"""Segmentos: grupos de personas que no son un grupo ni un ministerio (p. ej. «Servidores»)."""

from apps.accounts.permissions import tiene_permiso

ID_IGLESIA = 1
SERVIDORES = 1
SEGMENTOS = {SERVIDORES: "Servidores"}


def es_servidor(user) -> bool:
    """Sirve en algún ministerio o tiene el rol de servidor en algún grupo."""
    persona = getattr(user, "persona", None)
    if persona is None:
        return False
    from apps.grupos.models import GrupoMiembro
    from apps.unidades.models import UnidadMiembro

    return (
        UnidadMiembro.objects.filter(persona=persona, activo=True, unidad__activa=True).exists()
        or GrupoMiembro.objects.filter(persona=persona, activo=True, rol="servidor").exists()
    )


def pertenece(user, segmento_id: int) -> bool:
    if segmento_id == SERVIDORES:
        return es_servidor(user) or tiene_permiso(user, "muro.publicar")
    return False
