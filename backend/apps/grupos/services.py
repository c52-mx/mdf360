from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core import audit
from apps.notificaciones import push
from apps.personas import services as personas
from apps.personas.models import Persona

from . import access
from .models import (
    Asistencia,
    EstudioSemanal,
    GrupoMiembro,
    Reunion,
    SolicitudIngreso,
    lunes_de,
)

LIMITE_PDF = 15 * 1024 * 1024
LIMITE_AUDIO = 40 * 1024 * 1024
EXT_AUDIO = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav"}


def agregar_integrante(
    grupo, *, rol, whatsapp, nombre="", acepta_datos=False, actor=None, request=None
):
    """Suma a una persona al grupo. Si el WhatsApp ya existe, se vincula la misma persona;
    si no, se crea un Contacto (exige el consentimiento de privacidad)."""
    persona = personas.buscar_duplicado(whatsapp)
    creada = False
    if persona is None:
        if not nombre.strip():
            raise ValidationError("Escribe el nombre de la persona.")
        persona = personas.crear_persona(
            datos={
                "nombre": nombre.strip(),
                "whatsapp": whatsapp,
                "procedencia": "invitado_grupo" if rol == "asistente" else "miembro",
            },
            acepta_datos=acepta_datos,
            actor=actor,
            request=request,
        )
        creada = True
    miembro, nuevo = GrupoMiembro.objects.get_or_create(
        grupo=grupo, persona=persona, rol=rol, defaults={"activo": True}
    )
    entra = nuevo or not miembro.activo
    if not nuevo and not miembro.activo:
        miembro.activo = True
        miembro.retirado_por_baja = False
        miembro.save(update_fields=["activo", "retirado_por_baja"])
    audit.log(
        "grupo.integrante_agregado", actor=actor, target=grupo, request=request,
        persona=persona.pk, rol=rol, persona_nueva=creada,
    )  # fmt: skip
    if entra:
        _avisar_ingreso(grupo, persona, actor)
    return miembro


def _avisar_ingreso(grupo, persona, actor) -> None:
    """Avisa por notificación a quien lidera el grupo y a la persona (si tiene cuenta)."""
    lideres = [
        m.persona.usuario
        for m in GrupoMiembro.objects.filter(
            grupo=grupo, activo=True, rol__in=["lider", "supervisor"]
        ).select_related("persona__usuario")
        if m.persona.usuario_id
    ]
    push.notificar(
        titulo=f"Nueva persona en {grupo.nombre}",
        cuerpo=f"{persona.nombre_completo} se agregó al grupo.",
        url=f"/grupos/{grupo.pk}",
        etiqueta=f"ingreso-{grupo.pk}",
        usuarios=lideres,
        excluir=actor,
    )
    if persona.usuario_id:
        push.notificar(
            titulo="Te agregaron a un grupo",
            cuerpo=f"Ahora eres parte de {grupo.nombre}.",
            url=f"/grupos/{grupo.pk}",
            etiqueta=f"ingreso-{grupo.pk}-yo",
            usuarios=[persona.usuario],
            excluir=actor,
        )


# ---------- ingreso por enlace o QR (sala de espera) ----------
def generar_enlace(grupo, *, actor=None, request=None) -> str:
    """Crea (o regenera) el enlace de ingreso; el anterior deja de servir."""
    import secrets

    grupo.enlace_token = secrets.token_urlsafe(18)
    grupo.save(update_fields=["enlace_token"])
    audit.log("grupo.enlace_generado", actor=actor, target=grupo, request=request)
    return grupo.enlace_token


def desactivar_enlace(grupo, *, actor=None, request=None) -> None:
    grupo.enlace_token = None
    grupo.save(update_fields=["enlace_token"])
    audit.log("grupo.enlace_desactivado", actor=actor, target=grupo, request=request)


def solicitar_ingreso(grupo, *, nombre, whatsapp, acepta_datos, request=None) -> SolicitudIngreso:
    """Registra la solicitud de quien abrió el enlace. Es idempotente: si ya hay una pendiente
    con ese WhatsApp, se devuelve la misma. No pide cuenta: la persona espera la aprobación."""
    import secrets

    from apps.accounts.phone import normalize_whatsapp

    if not acepta_datos:
        raise ValidationError("Debes aceptar el aviso de privacidad para pedir tu ingreso.")
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("Escribe tu nombre.")
    numero = normalize_whatsapp(whatsapp)
    persona = personas.buscar_duplicado(numero)
    if persona and GrupoMiembro.objects.filter(grupo=grupo, persona=persona, activo=True).exists():
        raise ValidationError("Ya eres parte de este grupo.")
    existente = SolicitudIngreso.objects.filter(
        grupo=grupo, whatsapp=numero, estado=SolicitudIngreso.Estado.PENDIENTE
    ).first()
    if existente:
        return existente
    solicitud = SolicitudIngreso.objects.create(
        grupo=grupo,
        nombre=nombre,
        whatsapp=numero,
        acepta_datos=True,
        codigo=secrets.token_urlsafe(24),
    )
    audit.log("grupo.solicitud_creada", target=grupo, request=request, solicitud=solicitud.pk)
    lideres = [
        m.persona.usuario
        for m in GrupoMiembro.objects.filter(
            grupo=grupo, activo=True, rol__in=["lider", "supervisor"]
        ).select_related("persona__usuario")
        if m.persona.usuario_id
    ]
    push.notificar(
        titulo=f"Quieren unirse a {grupo.nombre}",
        cuerpo=f"{solicitud.nombre} espera tu aprobación.",
        url=f"/grupos/{grupo.pk}",
        etiqueta=f"solicitud-{grupo.pk}",
        usuarios=lideres,
    )
    return solicitud


def resolver_solicitud(solicitud, *, aprobar, actor, request=None) -> SolicitudIngreso:
    if solicitud.estado != SolicitudIngreso.Estado.PENDIENTE:
        raise ValidationError("Esta solicitud ya se resolvió.")
    with transaction.atomic():
        if aprobar:
            agregar_integrante(
                solicitud.grupo,
                rol="asistente",
                whatsapp=solicitud.whatsapp,
                nombre=solicitud.nombre,
                acepta_datos=solicitud.acepta_datos,
                actor=actor,
                request=request,
            )
        solicitud.estado = (
            SolicitudIngreso.Estado.APROBADA if aprobar else SolicitudIngreso.Estado.RECHAZADA
        )
        solicitud.resuelta_en = timezone.now()
        solicitud.resuelta_por = actor
        solicitud.save(update_fields=["estado", "resuelta_en", "resuelta_por"])
    audit.log(
        "grupo.solicitud_aprobada" if aprobar else "grupo.solicitud_rechazada",
        actor=actor, target=solicitud.grupo, request=request, solicitud=solicitud.pk,
    )  # fmt: skip
    return solicitud


@transaction.atomic
def guardar_asistencia(
    reunion: Reunion, items, *, actor, request=None, capturado_en=None
) -> tuple[int, int]:
    """`items`: lista de dicts {persona_id, presente}. Solo personas activas del grupo.

    Si viene `capturado_en` (captura sin conexión), no se pisa un registro más reciente que esa
    captura: se omite y se cuenta. Devuelve (presentes, omitidos).
    """
    validas = set(
        GrupoMiembro.objects.filter(grupo=reunion.grupo, activo=True).values_list(
            "persona_id", flat=True
        )
    )
    omitidos = 0
    for item in items:
        if item["persona_id"] not in validas:
            raise ValidationError("Una de las personas no pertenece al grupo.")
        if capturado_en is not None:
            existente = Asistencia.objects.filter(
                reunion=reunion, persona_id=item["persona_id"]
            ).first()
            if existente and existente.actualizada_en > capturado_en:
                omitidos += 1
                continue
        Asistencia.objects.update_or_create(
            reunion=reunion,
            persona_id=item["persona_id"],
            defaults={"presente": item["presente"], "registrada_por": actor},
        )
    presentes = reunion.asistencias.filter(presente=True).count()
    audit.log(
        "asistencia.guardada", actor=actor, target=reunion, request=request,
        total=len(items), presentes=presentes, omitidos=omitidos,
        diferida=capturado_en is not None,
        capturado_en=capturado_en.isoformat() if capturado_en else None,
    )  # fmt: skip
    return presentes, omitidos


def abrir_reunion(grupo, fecha: date | None, *, actor, request=None) -> Reunion:
    dia = fecha or timezone.localdate()
    # Solo se advierte, no se bloquea: se registra que fue fuera del día fijo del grupo
    fuera = grupo.dia_semana is not None and dia.weekday() != grupo.dia_semana
    reunion, creada = Reunion.objects.get_or_create(
        grupo=grupo, fecha=dia, defaults={"creada_por": actor, "fuera_de_dia": fuera}
    )
    if creada:
        audit.log(
            "reunion.creada", actor=actor, target=reunion, request=request, fuera_de_dia=fuera
        )
    return reunion


def estudio_de(fecha: date) -> EstudioSemanal | None:
    return EstudioSemanal.objects.filter(semana=lunes_de(fecha)).first()


def _validar_archivo(archivo, tipo: str):
    nombre = archivo.name.lower()
    if tipo in ("pdf_adultos", "pdf_ninos"):
        if not nombre.endswith(".pdf"):
            raise ValidationError("El estudio debe ser un archivo PDF.")
        if archivo.size > LIMITE_PDF:
            raise ValidationError("Cada PDF puede pesar hasta 15 MB.")
        cabecera = archivo.read(5)
        archivo.seek(0)
        if cabecera != b"%PDF-":
            raise ValidationError("El archivo no es un PDF válido.")
    else:
        if not any(nombre.endswith(ext) for ext in EXT_AUDIO):
            raise ValidationError("El audio debe ser mp3, m4a, aac, ogg, opus o wav.")
        if archivo.size > LIMITE_AUDIO:
            raise ValidationError("El audio puede pesar hasta 40 MB.")


@transaction.atomic
def guardar_estudio(*, semana: date, titulo: str, archivos: dict, actor, request=None):
    """Crea o actualiza el estudio de la semana. `archivos`: {campo: UploadedFile}."""
    semana = lunes_de(semana)
    for tipo, archivo in archivos.items():
        _validar_archivo(archivo, tipo)
    estudio, _ = EstudioSemanal.objects.get_or_create(
        semana=semana, defaults={"titulo": titulo, "subido_por": actor}
    )
    estudio.titulo = titulo
    estudio.subido_por = actor
    for tipo, archivo in archivos.items():
        anterior = getattr(estudio, tipo)
        if anterior:
            anterior.delete(save=False)
        setattr(estudio, tipo, archivo)
    estudio.save()
    audit.log(
        "estudio.guardado", actor=actor, target=estudio, request=request,
        archivos=sorted(archivos),
    )  # fmt: skip
    if archivos:
        push.notificar(
            titulo="Estudio de la semana",
            cuerpo=estudio.titulo,
            url="/estudios",
            etiqueta="estudio",
            puede_recibir=access.puede_ver_estudios,
            excluir=actor,
        )
    return estudio


def personas_con_asistencia(reunion: Reunion) -> list[dict]:
    """Integrantes activos del grupo con su asistencia registrada (si la hay)."""
    registradas = {a.persona_id: a.presente for a in reunion.asistencias.all()}
    filas = []
    vistos = set()
    miembros = GrupoMiembro.objects.filter(grupo=reunion.grupo, activo=True).select_related(
        "persona"
    )
    for m in miembros:
        if m.persona_id in vistos:
            continue
        vistos.add(m.persona_id)
        p: Persona = m.persona
        filas.append(
            {
                "persona_id": p.pk,
                "nombre": p.nombre_completo,
                "roles": sorted(
                    GrupoMiembro.objects.filter(
                        grupo=reunion.grupo, persona=p, activo=True
                    ).values_list("rol", flat=True)
                ),
                "invitado": p.procedencia == "invitado_grupo",
                "presente": registradas.get(p.pk, False),
                "registrada": p.pk in registradas,
            }
        )
    return filas
