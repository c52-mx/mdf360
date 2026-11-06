from django.core.exceptions import ValidationError

from apps.accounts import equipos
from apps.core import audit
from apps.notificaciones import push
from apps.personas import services as personas

from .models import UnidadMiembro


def agregar_integrante(
    unidad, *, rol, whatsapp, nombre="", acepta_datos=False, actor=None, request=None
):
    """Suma a una persona al ministerio. Si el WhatsApp ya existe se vincula la misma persona;
    si no, se crea un Contacto (exige el consentimiento de privacidad)."""
    persona = personas.buscar_duplicado(whatsapp)
    creada = False
    if persona is None:
        if not nombre.strip():
            raise ValidationError("Escribe el nombre de la persona.")
        persona = personas.crear_persona(
            datos={"nombre": nombre.strip(), "whatsapp": whatsapp, "procedencia": "miembro"},
            acepta_datos=acepta_datos,
            actor=actor,
            request=request,
        )
        creada = True
    miembro, nuevo = UnidadMiembro.objects.get_or_create(
        unidad=unidad, persona=persona, rol=rol, defaults={"activo": True}
    )
    entra = nuevo or not miembro.activo
    if not nuevo and not miembro.activo:
        miembro.activo = True
        miembro.save(update_fields=["activo"])
    audit.log(
        "unidad.integrante_agregado", actor=actor, target=unidad, request=request,
        persona=persona.pk, rol=rol, persona_nueva=creada,
    )  # fmt: skip
    if entra and persona.usuario_id:
        rol_nombre = equipos.nombre_de("ministerio", miembro.rol).lower()
        push.notificar(
            titulo="Te agregaron a un ministerio",
            cuerpo=f"Ahora sirves en {unidad.nombre} como {rol_nombre}.",
            url=f"/ministerios/{unidad.pk}",
            etiqueta=f"unidad-{unidad.pk}-yo",
            usuarios=[persona.usuario],
            excluir=actor,
        )
    return miembro


def generar_enlace(unidad, *, actor=None, request=None) -> str:
    """Crea (o regenera) el enlace fijo del ministerio; el anterior deja de servir."""
    import secrets

    unidad.enlace_token = secrets.token_urlsafe(18)
    unidad.save(update_fields=["enlace_token"])
    audit.log("unidad.enlace_generado", actor=actor, target=unidad, request=request)
    return unidad.enlace_token


def desactivar_enlace(unidad, *, actor=None, request=None) -> None:
    unidad.enlace_token = None
    unidad.save(update_fields=["enlace_token"])
    audit.log("unidad.enlace_desactivado", actor=actor, target=unidad, request=request)


def unirse_por_enlace(unidad, *, nombre, whatsapp, acepta_datos, request=None):
    """Quien abre el QR del ministerio entra de inmediato como servidor (rol básico), sin
    aprobación. Los roles con más alcance los asigna después quien administra el ministerio."""
    from apps.accounts.phone import normalize_whatsapp

    numero = normalize_whatsapp(whatsapp)
    if personas.buscar_duplicado(numero) is None and not acepta_datos:
        raise ValidationError("Debes aceptar el aviso de privacidad para sumarte.")
    miembro = agregar_integrante(
        unidad,
        rol=UnidadMiembro.Rol.SERVIDOR,
        whatsapp=numero,
        nombre=nombre,
        acepta_datos=acepta_datos,
        request=request,
    )
    audit.log("unidad.ingreso_por_qr", target=unidad, request=request, persona=miembro.persona_id)
    return miembro
