import io
from datetime import date

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from PIL import Image, ImageOps

from apps.accounts.phone import normalize_whatsapp
from apps.core import audit

from .aviso import AVISO_VERSION
from .models import (
    NIVEL_ORDEN,
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


def _movimiento(persona, tipo, motivo="", fecha=None, actor=None) -> PersonaMovimiento:
    return PersonaMovimiento.objects.create(
        persona=persona,
        tipo=tipo,
        motivo=motivo,
        fecha=fecha or date.today(),
        registrado_por=actor if getattr(actor, "pk", None) else None,
    )


def registrar_consentimiento(persona, *, acepta_datos, acepta_foto=False, actor=None):
    if not acepta_datos:
        raise ConsentimientoRequerido
    return Consentimiento.objects.create(
        persona=persona,
        version=AVISO_VERSION,
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


def registrar_baja(persona: Persona, *, fecha, motivo, actor=None, request=None) -> Persona:
    if not persona.activo:
        raise ValidationError("La persona ya está dada de baja.")
    persona.activo = False
    persona.save(update_fields=["activo", "actualizado_en"])
    _movimiento(persona, PersonaMovimiento.Tipo.BAJA, motivo, fecha, actor)
    audit.log("persona.baja", actor=actor, target=persona, request=request)
    return persona


def reactivar(persona: Persona, *, motivo="", actor=None, request=None) -> Persona:
    if persona.activo:
        raise ValidationError("La persona ya está activa.")
    persona.activo = True
    persona.save(update_fields=["activo", "actualizado_en"])
    _movimiento(persona, PersonaMovimiento.Tipo.REACTIVACION, motivo, actor=actor)
    audit.log("persona.reactivada", actor=actor, target=persona, request=request)
    return persona


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
