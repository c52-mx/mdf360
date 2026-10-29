"""Aviso de privacidad vigente.

El texto vive en la base de datos (modelo AvisoPrivacidad) para poder sustituirlo sin tocar el
código: quien administra la configuración publica una versión nueva desde la aplicación.
Cada consentimiento guarda la versión que la persona aceptó. Este módulo solo trae el texto
provisional con el que arranca el sistema y las funciones para consultar el vigente.
"""

VERSION_PROVISIONAL = "0.2-provisional"

TEXTO_PROVISIONAL = """\
AVISO DE PRIVACIDAD (TEXTO PROVISIONAL, PENDIENTE DE REVISIÓN LEGAL)

Mundo de Fe México es responsable del tratamiento de tus datos personales.

Qué datos recabamos: nombre, fecha de nacimiento, domicilio, teléfonos, correo, fotografía, \
información de tu proceso de discipulado, servicio y participación en grupos, cursos y \
ministerios, los vehículos que registres, las peticiones de oración que compartas y los datos \
adicionales que la iglesia solicite en sus formularios.

Para qué los usamos: dar seguimiento a tu proceso de discipulado, organizar grupos de conexión, \
cursos y ministerios, comunicarte avisos y eventos, y cuidar la seguridad de la comunidad. Los \
datos de tu vehículo se usan únicamente para ubicarte con rapidez ante cualquier asunto \
relacionado con él.

Tu fotografía solo se usa para identificarte dentro del sistema, y únicamente si das tu \
consentimiento. Los datos de menores de edad se tratan con el consentimiento de su madre, padre \
o tutor.

Tus derechos: puedes acceder, rectificar o cancelar tus datos, y oponerte a su uso \
(derechos ARCO), solicitándolo a tu líder o a la administración de la iglesia.

Este texto es provisional y debe ser revisado por la iglesia antes de su uso oficial.
"""


def vigente():
    """La versión más reciente publicada; si aún no hay ninguna, el texto provisional."""
    from .models import AvisoPrivacidad

    aviso = AvisoPrivacidad.objects.order_by("-publicado_en", "-pk").first()
    if aviso is None:
        return VERSION_PROVISIONAL, TEXTO_PROVISIONAL
    return aviso.version, aviso.texto
