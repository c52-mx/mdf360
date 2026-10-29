import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image, ImageOps

from apps.accounts.phone import normalize_whatsapp
from apps.core import audit

from . import aviso
from .models import (
    NIVEL_ORDEN,
    AvisoPrivacidad,
    Consentimiento,
    Nivel,
    Persona,
    PersonaMovimiento,
    PersonaProceso,
    Procedencia,
    ProcesoDiscipular,
)

REQUISITOS_EDU = {
    "nombre": "nombre",
    "apellido_paterno": "apellido paterno",
    "fecha_nacimiento": "fecha de nacimiento",
}
FOTO_LADO_MAXIMO = 800


class ConsentimientoRequerido(Exception):
    pass


class PersonaDuplicada(Exception):
    def __init__(self, persona: Persona):
        self.persona = persona


def faltantes_para_edu(persona: Persona) -> list[str]:
    return [etiqueta for campo, etiqueta in REQUISITOS_EDU.items() if not getattr(persona, campo)]


def _movimiento(
    persona, tipo, motivo="", fecha=None, actor=None, iglesia_destino=""
) -> PersonaMovimiento:
    return PersonaMovimiento.objects.create(
        persona=persona,
        tipo=tipo,
        motivo=motivo,
        iglesia_destino=iglesia_destino,
        fecha=fecha or timezone.localdate(),
        registrado_por=actor if getattr(actor, "pk", None) else None,
    )


def registrar_consentimiento(persona, *, acepta_datos, acepta_foto=False, actor=None):
    if not acepta_datos:
        raise ConsentimientoRequerido
    return Consentimiento.objects.create(
        persona=persona,
        version=aviso.vigente()[0],
        acepta_datos=True,
        acepta_foto=acepta_foto,
        registrado_por=actor if getattr(actor, "pk", None) else None,
    )


def buscar_duplicado(whatsapp: str) -> Persona | None:
    if not whatsapp:
        return None
    return Persona.objects.filter(whatsapp=normalize_whatsapp(whatsapp)).first()


@transaction.atomic
def crear_persona(*, datos, acepta_datos, acepta_foto=False, actor=None, request=None) -> Persona:
    """Alta rápida de un Contacto (M1-12). Exige consentimiento y evita duplicados por WhatsApp."""
    if not acepta_datos:
        raise ConsentimientoRequerido
    existente = buscar_duplicado(datos.get("whatsapp", ""))
    if existente:
        raise PersonaDuplicada(existente)
    try:
        with transaction.atomic():
            persona = Persona.objects.create(nivel=Nivel.CONTACTO, **datos)
    except IntegrityError as exc:  # carrera entre dos altas con el mismo número
        existente = buscar_duplicado(datos.get("whatsapp", ""))
        if existente:
            raise PersonaDuplicada(existente) from exc
        raise
    registrar_consentimiento(
        persona, acepta_datos=acepta_datos, acepta_foto=acepta_foto, actor=actor
    )
    _movimiento(persona, PersonaMovimiento.Tipo.ALTA, actor=actor)
    audit.log("persona.created", actor=actor, target=persona, request=request, nivel=persona.nivel)
    return persona


def cambiar_nivel(persona: Persona, nivel: str, *, actor=None, request=None) -> Persona:
    if nivel not in NIVEL_ORDEN:
        raise ValidationError("Nivel de registro no válido.")
    if NIVEL_ORDEN[nivel] <= NIVEL_ORDEN[persona.nivel]:
        raise ValidationError("El nivel de registro solo puede avanzar.")
    if nivel == Nivel.EDU:
        faltan = faltantes_para_edu(persona)
        if faltan:
            raise ValidationError(f"Para el expediente completo falta: {', '.join(faltan)}.")
    anterior = persona.nivel
    persona.nivel = nivel
    persona.save(update_fields=["nivel", "actualizado_en"])
    _movimiento(persona, PersonaMovimiento.Tipo.CAMBIO_NIVEL, f"{anterior} → {nivel}", actor=actor)
    audit.log(
        "persona.nivel_changed", actor=actor, target=persona, request=request,
        anterior=anterior, nuevo=nivel,
    )  # fmt: skip
    return persona


def _retirar_de_grupos(persona: Persona) -> list[int]:
    """Quien sale de la iglesia deja de aparecer en las listas de sus grupos.

    Se desactiva la membresía (no se borra): el historial de asistencia se conserva. Devuelve los
    grupos de los que salió.
    """
    from apps.grupos.models import GrupoMiembro

    membresias = GrupoMiembro.objects.filter(persona=persona, activo=True)
    grupos = sorted(set(membresias.values_list("grupo_id", flat=True)))
    membresias.update(activo=False, retirado_por_baja=True)
    return grupos


def _desactivar_acceso(persona: Persona) -> bool:
    """Su cuenta (si la tiene) deja de poder entrar hasta que se reactive a la persona."""
    cuenta = persona.usuario
    if cuenta is None or not cuenta.is_active:
        return False
    cuenta.is_active = False
    cuenta.save(update_fields=["is_active"])
    return True


def registrar_baja(persona: Persona, *, fecha, motivo, actor=None, request=None) -> Persona:
    if not persona.activo:
        raise ValidationError("La persona ya está dada de baja.")
    persona.activo = False
    persona.save(update_fields=["activo", "actualizado_en"])
    _movimiento(persona, PersonaMovimiento.Tipo.BAJA, motivo, fecha, actor)
    grupos = _retirar_de_grupos(persona)
    acceso = _desactivar_acceso(persona)
    audit.log(
        "persona.baja", actor=actor, target=persona, request=request,
        grupos_quitados=grupos, acceso_desactivado=acceso,
    )  # fmt: skip
    return persona


def trasladar(
    persona: Persona, *, fecha, iglesia_destino, motivo="", actor=None, request=None
) -> Persona:
    """Pasa a la persona a otra iglesia: queda inactiva, con el destino en su historial."""
    if not persona.activo:
        raise ValidationError("La persona ya está dada de baja.")
    destino = iglesia_destino.strip()
    if not destino:
        raise ValidationError("Escribe a qué iglesia se traslada.")
    persona.activo = False
    persona.save(update_fields=["activo", "actualizado_en"])
    _movimiento(
        persona, PersonaMovimiento.Tipo.TRASLADO, motivo, fecha, actor, iglesia_destino=destino
    )
    grupos = _retirar_de_grupos(persona)
    acceso = _desactivar_acceso(persona)
    audit.log(
        "persona.traslado", actor=actor, target=persona, request=request,
        destino=destino, grupos_quitados=grupos, acceso_desactivado=acceso,
    )  # fmt: skip
    return persona


def reactivar(persona: Persona, *, motivo="", actor=None, request=None) -> Persona:
    if persona.activo:
        raise ValidationError("La persona ya está activa.")
    persona.activo = True
    persona.save(update_fields=["activo", "actualizado_en"])
    _movimiento(persona, PersonaMovimiento.Tipo.REACTIVACION, motivo, actor=actor)
    grupos = _regresar_a_grupos(persona)
    acceso = _reactivar_acceso(persona)
    audit.log(
        "persona.reactivada", actor=actor, target=persona, request=request,
        grupos_regresados=grupos, acceso_reactivado=acceso,
    )  # fmt: skip
    return persona


def _regresar_a_grupos(persona: Persona) -> list[int]:
    """Regresa solo a los grupos de los que salió por la baja (no a los que dejó antes)."""
    from apps.grupos.models import GrupoMiembro

    membresias = GrupoMiembro.objects.filter(persona=persona, retirado_por_baja=True)
    grupos = sorted(set(membresias.values_list("grupo_id", flat=True)))
    membresias.update(activo=True, retirado_por_baja=False)
    return grupos


def _reactivar_acceso(persona: Persona) -> bool:
    cuenta = persona.usuario
    if cuenta is None or cuenta.is_active:
        return False
    cuenta.is_active = True
    cuenta.save(update_fields=["is_active"])
    return True


def actualizar_procesos(persona: Persona, items, *, actor=None, request=None) -> None:
    """Guarda el avance en los procesos discipulares. `items`: dicts con proceso (obj), etc."""
    with transaction.atomic():
        for item in items:
            PersonaProceso.objects.update_or_create(
                persona=persona,
                proceso=item["proceso"],
                defaults={
                    "completado": item["completado"],
                    "fecha": item.get("fecha"),
                    "maestro": item.get("maestro", ""),
                },
            )
    audit.log("persona.procesos_updated", actor=actor, target=persona, request=request)


def procesos_de(persona: Persona) -> list[dict]:
    """Catálogo activo combinado con el avance de la persona."""
    avance = {pp.proceso_id: pp for pp in persona.procesos.all()}
    filas = []
    for proceso in ProcesoDiscipular.objects.filter(activo=True):
        pp = avance.get(proceso.pk)
        filas.append(
            {
                "proceso": proceso.pk,
                "nombre": proceso.nombre,
                "pide_maestro": proceso.pide_maestro,
                "completado": pp.completado if pp else False,
                "fecha": pp.fecha if pp else None,
                "maestro": pp.maestro if pp else "",
            }
        )
    return filas


def guardar_foto(persona: Persona, archivo, *, actor=None, request=None) -> Persona:
    """Normaliza la foto (orientación, tamaño máximo, JPEG sin metadatos) y la guarda en disco."""
    try:
        imagen = Image.open(archivo)
        imagen = ImageOps.exif_transpose(imagen).convert("RGB")
    except Exception as exc:
        raise ValidationError("El archivo no es una imagen válida.") from exc
    imagen.thumbnail((FOTO_LADO_MAXIMO, FOTO_LADO_MAXIMO))
    buffer = io.BytesIO()
    imagen.save(buffer, format="JPEG", quality=85)
    if persona.foto:
        persona.foto.delete(save=False)
    persona.foto.save("foto.jpg", ContentFile(buffer.getvalue()), save=False)
    persona.save(update_fields=["foto", "actualizado_en"])
    audit.log("persona.foto_updated", actor=actor, target=persona, request=request)
    return persona


def ensure_persona_for_user(user) -> Persona:
    """Toda cuenta de usuario tiene su Persona: se enlaza por WhatsApp o se crea un Contacto."""
    persona = Persona.objects.filter(usuario=user).first()
    if persona:
        return persona
    existente = Persona.objects.filter(whatsapp=user.whatsapp, usuario__isnull=True).first()
    if existente:
        existente.usuario = user
        existente.save(update_fields=["usuario", "actualizado_en"])
        return existente
    persona = Persona.objects.create(
        nombre=user.nombre,
        whatsapp=user.whatsapp,
        email=user.email,
        procedencia=Procedencia.MIEMBRO,
        usuario=user,
    )
    _movimiento(persona, PersonaMovimiento.Tipo.ALTA, "Alta por invitación")
    return persona


#: Lo que cada persona edita de sí misma desde «Mi cuenta». Nada de esto toca el acceso
#: (WhatsApp, correo, PIN) ni sus relaciones con la iglesia (grupo, sector, ministerios, roles).
CAMPOS_DE_PERFIL = (
    "nombre",
    "apellido_paterno",
    "apellido_materno",
    "fecha_nacimiento",
    "telefono_fijo",
    "calle_numero",
    "colonia",
    "codigo_postal",
    "alcaldia",
    "devocional_personal",
    "oracion_familias",
    "oracion_familias_detalle",
)


@transaction.atomic
def actualizar_perfil(persona: Persona, datos: dict, *, actor, request=None) -> Persona:
    """Guarda los datos básicos que la propia persona puede corregir."""
    cambios = {c: v for c, v in datos.items() if c in CAMPOS_DE_PERFIL}
    if "nombre" in cambios and not str(cambios["nombre"]).strip():
        raise ValidationError("Escribe tu nombre.")
    modificados = [c for c, v in cambios.items() if getattr(persona, c) != v]
    if not modificados:
        return persona
    for campo in modificados:
        setattr(persona, campo, cambios[campo])
    persona.save(update_fields=[*modificados, "actualizado_en"])
    usuario = persona.usuario
    if usuario is not None and usuario.nombre != persona.nombre_completo:
        usuario.nombre = persona.nombre_completo
        usuario.save(update_fields=["nombre"])
    # La bitácora guarda qué campos cambiaron, no sus valores
    audit.log(
        "persona.perfil_editado", actor=actor, target=persona, request=request, campos=modificados
    )
    return persona


def tiene_consentimiento_de_foto(persona: Persona) -> bool:
    ultimo = persona.consentimientos.order_by("-fecha", "-pk").first()
    return bool(ultimo and ultimo.acepta_foto)


def guardar_foto_propia(persona: Persona, archivo, *, acepta_foto: bool, actor, request=None):
    """La foto exige el consentimiento correspondiente: si falta, se registra en este momento."""
    if not tiene_consentimiento_de_foto(persona):
        if not acepta_foto:
            raise ConsentimientoRequerido
        registrar_consentimiento(persona, acepta_datos=True, acepta_foto=True, actor=actor)
    return guardar_foto(persona, archivo, actor=actor, request=request)


def aviso_pendiente(persona: Persona) -> bool:
    """Hay un aviso vigente distinto al último que la persona aceptó."""
    ultimo = persona.consentimientos.order_by("-fecha", "-pk").first()
    return ultimo is None or ultimo.version != aviso.vigente()[0]


def aceptar_aviso_vigente(persona: Persona, *, actor, request=None) -> Consentimiento:
    """Registra que la persona acepta el aviso vigente; conserva su decisión sobre la foto."""
    ultimo = persona.consentimientos.order_by("-fecha", "-pk").first()
    consentimiento = registrar_consentimiento(
        persona,
        acepta_datos=True,
        acepta_foto=bool(ultimo and ultimo.acepta_foto),
        actor=actor,
    )
    audit.log(
        "persona.aviso_aceptado", actor=actor, target=persona, request=request,
        version=consentimiento.version,
    )  # fmt: skip
    return consentimiento


@transaction.atomic
def publicar_aviso(*, version: str, texto: str, actor, request=None):
    version, texto = version.strip(), texto.strip()
    if not version or len(version) > 40:
        raise ValidationError("Escribe la versión del aviso (máximo 40 caracteres).")
    if len(texto) < 50:
        raise ValidationError("El texto del aviso es demasiado corto.")
    if AvisoPrivacidad.objects.filter(version=version).exists():
        raise ValidationError("Ya existe un aviso con esa versión; usa otra.")
    nuevo = AvisoPrivacidad.objects.create(version=version, texto=texto, publicado_por=actor)
    audit.log("aviso.publicado", actor=actor, request=request, version=version)
    return nuevo
