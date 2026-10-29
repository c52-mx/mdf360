"""Roles dentro de un grupo de conexión o un ministerio, y lo que cada uno permite.

Quien administra roles (Super Usuario, Pastor y Secretaria) crea roles de equipo y decide sus
permisos. Los tres roles de siempre (encargado, respaldo y servidor) vienen con el sistema y se
ajustan, pero no se desactivan.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from apps.core import audit

from . import catalogo
from .models import RolEquipo


def nombres(ambito: str) -> dict[str, str]:
    """clave -> nombre para mostrar. Una sola consulta por lista."""
    return dict(RolEquipo.objects.filter(ambito=ambito).values_list("clave", "nombre"))


def nombre_de(ambito: str, clave: str) -> str:
    return nombres(ambito).get(clave, clave)


def claves_activas(ambito: str) -> set[str]:
    return set(RolEquipo.objects.filter(ambito=ambito, activo=True).values_list("clave", flat=True))


def permisos_de_roles(ambito: str, claves) -> set[str]:
    """Unión de lo que permiten los roles dados (solo los activos)."""
    claves = set(claves)
    if not claves:
        return set()
    resultado: set[str] = set()
    for permisos in RolEquipo.objects.filter(
        ambito=ambito, clave__in=claves, activo=True
    ).values_list("permisos", flat=True):
        resultado.update(permisos)
    return resultado


def con_permiso(ambito: str, permiso: str) -> set[str]:
    """Claves de los roles activos que incluyen ese permiso."""
    return {
        r.clave
        for r in RolEquipo.objects.filter(ambito=ambito, activo=True)
        if permiso in r.permisos
    }


PERMISOS_DE_GESTION = {"integrantes", "historial"}


def permisos_de_gestion(permisos) -> bool:
    return bool(set(permisos) & PERMISOS_DE_GESTION)


def es_de_gestion(ambito: str, clave: str) -> bool:
    """Un rol que administra a la gente del equipo (o ve su historial) solo lo asigna la
    administración del grupo o del ministerio: líder, supervisor, encargado, respaldo…"""
    return any(
        permisos_de_gestion(r.permisos)
        for r in RolEquipo.objects.filter(ambito=ambito, clave=clave, activo=True)
    )


def en_uso(rol: RolEquipo) -> int:
    from apps.grupos.models import GrupoMiembro
    from apps.unidades.models import UnidadMiembro

    modelo = GrupoMiembro if rol.ambito == catalogo.AMBITO_GRUPO else UnidadMiembro
    return modelo.objects.filter(rol=rol.clave, activo=True).count()


def _validar(ambito, nombre, permisos, *, rol=None) -> str:
    if ambito not in catalogo.AMBITOS:
        raise ValidationError("Ámbito no válido.")
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValidationError("Escribe el nombre del rol.")
    repetido = RolEquipo.objects.filter(ambito=ambito, nombre__iexact=nombre)
    if repetido.exclude(pk=getattr(rol, "pk", None)).exists():
        raise ValidationError("Ya existe un rol con ese nombre.")
    desconocidos = sorted(set(permisos) - catalogo.codigos_equipo(ambito))
    if desconocidos:
        raise ValidationError(f"Permisos que no existen: {', '.join(desconocidos)}.")
    return nombre


def _clave_libre(ambito: str, nombre: str) -> str:
    base = slugify(nombre)[:34] or "rol"
    clave, n = base, 2
    while RolEquipo.objects.filter(ambito=ambito, clave=clave).exists():
        clave = f"{base}-{n}"
        n += 1
    return clave


@transaction.atomic
def crear(actor, *, ambito, nombre, permisos, descripcion="", request=None) -> RolEquipo:
    permisos = sorted(set(permisos))
    nombre = _validar(ambito, nombre, permisos)
    rol = RolEquipo.objects.create(
        ambito=ambito,
        clave=_clave_libre(ambito, nombre),
        nombre=nombre,
        permisos=permisos,
        descripcion=descripcion.strip(),
    )
    audit.log(
        "rbac.rol_equipo_creado", actor=actor, request=request,
        ambito=ambito, rol=rol.clave, permisos=permisos,
    )  # fmt: skip
    return rol


@transaction.atomic
def editar(actor, rol: RolEquipo, *, request=None, **cambios) -> RolEquipo:
    permisos = sorted(set(cambios.get("permisos", rol.permisos)))
    nombre = _validar(rol.ambito, cambios.get("nombre", rol.nombre), permisos, rol=rol)
    antes = set(rol.permisos)
    rol.nombre, rol.permisos = nombre, permisos
    if "descripcion" in cambios:
        rol.descripcion = cambios["descripcion"].strip()
    rol.save()
    audit.log(
        "rbac.rol_equipo_editado", actor=actor, request=request, ambito=rol.ambito, rol=rol.clave,
        agregados=sorted(set(permisos) - antes), quitados=sorted(antes - set(permisos)),
    )  # fmt: skip
    return rol


def cambiar_estado(actor, rol: RolEquipo, *, activo: bool, request=None) -> RolEquipo:
    if not activo:
        if rol.es_base:
            raise ValidationError("Un rol base no se desactiva; puedes ajustar sus permisos.")
        usados = en_uso(rol)
        if usados:
            raise ValidationError(
                f"Hay {usados} persona(s) con este rol. Cámbialas de rol primero para desactivarlo."
            )
    rol.activo = activo
    rol.save(update_fields=["activo"])
    audit.log(
        "rbac.rol_equipo_activado" if activo else "rbac.rol_equipo_desactivado",
        actor=actor, request=request, ambito=rol.ambito, rol=rol.clave,
    )  # fmt: skip
    return rol


def sembrar() -> None:
    """Crea los roles base si faltan (la base de datos manda después del primer arranque)."""
    for ambito, roles in catalogo.BASE_EQUIPO.items():
        for clave, nombre, descripcion, permisos in roles:
            RolEquipo.objects.get_or_create(
                ambito=ambito,
                clave=clave,
                defaults={
                    "nombre": nombre,
                    "descripcion": descripcion,
                    "permisos": list(permisos),
                    "es_base": True,
                },
            )


def campo_rol(ambito: str, **kwargs):
    """Campo de DRF que acepta solo la clave de un rol de equipo activo de ese ámbito."""
    from rest_framework import serializers

    class CampoRolEquipo(serializers.CharField):
        def to_internal_value(self, data):
            valor = super().to_internal_value(data)
            if valor not in claves_activas(ambito):
                raise serializers.ValidationError("Ese rol no existe o está desactivado.")
            return valor

    return CampoRolEquipo(max_length=40, **kwargs)
