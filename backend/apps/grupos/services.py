from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core import audit
from apps.personas import services as personas
from apps.personas.models import Persona

from .models import Asistencia, EstudioSemanal, GrupoMiembro, Reunion, lunes_de

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
    if not nuevo and not miembro.activo:
        miembro.activo = True
        miembro.save(update_fields=["activo"])
    audit.log(
        "grupo.integrante_agregado", actor=actor, target=grupo, request=request,
        persona=persona.pk, rol=rol, persona_nueva=creada,
    )  # fmt: skip
    return miembro


@transaction.atomic
def guardar_asistencia(reunion: Reunion, items, *, actor, request=None) -> int:
    """`items`: lista de dicts {persona_id, presente}. Solo personas activas del grupo."""
    validas = set(
        GrupoMiembro.objects.filter(grupo=reunion.grupo, activo=True).values_list(
            "persona_id", flat=True
        )
    )
    for item in items:
        if item["persona_id"] not in validas:
            raise ValidationError("Una de las personas no pertenece al grupo.")
        Asistencia.objects.update_or_create(
            reunion=reunion,
            persona_id=item["persona_id"],
            defaults={"presente": item["presente"], "registrada_por": actor},
        )
    presentes = reunion.asistencias.filter(presente=True).count()
    audit.log(
        "asistencia.guardada", actor=actor, target=reunion, request=request,
        total=len(items), presentes=presentes,
    )  # fmt: skip
    return presentes


def abrir_reunion(grupo, fecha: date | None, *, actor, request=None) -> Reunion:
    reunion, creada = Reunion.objects.get_or_create(
        grupo=grupo, fecha=fecha or date.today(), defaults={"creada_por": actor}
    )
    if creada:
        audit.log("reunion.creada", actor=actor, target=reunion, request=request)
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
