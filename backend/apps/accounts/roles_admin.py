"""Administrador de roles y permisos.

Reglas que protegen la jerarquía (y que ninguna pantalla puede saltarse):
- Nadie está por encima del Super Usuario (nivel 0): su rol no se edita ni se desactiva.
- Solo se edita o se crea un rol de nivel más bajo que el propio (número mayor).
- Nadie concede un permiso que no tiene.
- Un rol base no se desactiva y un rol en uso tampoco.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core import audit

from . import catalogo
from .models import Rol, User

SUPER_USUARIO = "admin_tecnico"


class RolNoEditable(Exception):
    """El actor no puede modificar ese rol."""


def nivel_de(user) -> int:
    return min(
        Rol.objects.filter(asignaciones__usuario=user, activo=True).values_list("nivel", flat=True),
        default=99,
    )


def puede_editar(actor, rol: Rol) -> bool:
    return rol.clave != SUPER_USUARIO and rol.nivel > nivel_de(actor)


def _validar(nombre, nivel, permisos, actor, *, rol=None):
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValidationError("Escribe el nombre del rol.")
    if Rol.objects.filter(nombre__iexact=nombre).exclude(pk=getattr(rol, "pk", None)).exists():
        raise ValidationError("Ya existe un rol con ese nombre.")
    if nivel <= nivel_de(actor):
        raise ValidationError("El rol debe quedar por debajo de tu nivel en la jerarquía.")
    if nivel > 98:
        raise ValidationError("Nivel de jerarquía no válido.")
    desconocidos = sorted(set(permisos) - catalogo.codigos())
    if desconocidos:
        raise ValidationError(f"Permisos que no existen: {', '.join(desconocidos)}.")
    propios = actor.permisos()
    actuales = set(rol.permisos) if rol else set()
    ajenos = sorted((set(permisos) - actuales) - propios)
    if ajenos:
        raise ValidationError(f"No puedes conceder permisos que tú no tienes: {', '.join(ajenos)}.")
    return nombre


def _clave_libre(nombre: str) -> str:
    from django.utils.text import slugify

    base = slugify(nombre)[:34] or "rol"
    clave, n = base, 2
    while Rol.objects.filter(clave=clave).exists():
        clave = f"{base}-{n}"
        n += 1
    return clave


def crear_rol(
    actor, *, nombre, nivel, permisos, descripcion="", exige_credencial_fuerte=False, request=None
) -> Rol:
    permisos = sorted(set(permisos))
    nombre = _validar(nombre, nivel, permisos, actor)
    rol = Rol.objects.create(
        clave=_clave_libre(nombre),
        nombre=nombre,
        nivel=nivel,
        permisos=permisos,
        descripcion=descripcion.strip(),
        exige_credencial_fuerte=exige_credencial_fuerte,
    )
    audit.log(
        "rbac.rol_creado",
        actor=actor,
        request=request,
        rol=rol.clave,
        nivel=nivel,
        permisos=permisos,
    )
    return rol


def _reaplicar_credencial_fuerte(rol: Rol) -> None:
    """Si el rol pasó a exigir contraseña fuerte, quienes lo tienen quedan marcados."""
    for user in User.objects.filter(asignaciones__rol=rol).distinct():
        fuerte = any(
            r.exige_credencial_fuerte for r in Rol.objects.filter(asignaciones__usuario=user)
        )
        if fuerte != user.requires_strong_credential:
            user.requires_strong_credential = fuerte
            user.save(update_fields=["requires_strong_credential"])


@transaction.atomic
def editar_rol(actor, rol: Rol, *, request=None, **cambios) -> Rol:
    if not puede_editar(actor, rol):
        raise RolNoEditable
    nombre = cambios.get("nombre", rol.nombre)
    nivel = cambios.get("nivel", rol.nivel)
    permisos = sorted(set(cambios.get("permisos", rol.permisos)))
    nombre = _validar(nombre, nivel, permisos, actor, rol=rol)
    antes = set(rol.permisos)
    rol.nombre, rol.nivel, rol.permisos = nombre, nivel, permisos
    if "descripcion" in cambios:
        rol.descripcion = cambios["descripcion"].strip()
    fuerte_antes = rol.exige_credencial_fuerte
    if "exige_credencial_fuerte" in cambios:
        rol.exige_credencial_fuerte = cambios["exige_credencial_fuerte"]
    rol.save()
    if rol.exige_credencial_fuerte != fuerte_antes:
        _reaplicar_credencial_fuerte(rol)
    audit.log(
        "rbac.rol_editado", actor=actor, request=request, rol=rol.clave, nivel=nivel,
        agregados=sorted(set(permisos) - antes), quitados=sorted(antes - set(permisos)),
    )  # fmt: skip
    return rol


def duplicar_rol(actor, rol: Rol, *, request=None) -> Rol:
    """Copia un rol con lo que el actor puede conceder: parte de un rol parecido y se ajusta."""
    nivel = max(rol.nivel, nivel_de(actor) + 1)
    permisos = sorted(set(rol.permisos) & actor.permisos())
    nombre, n = f"Copia de {rol.nombre}", 2
    while Rol.objects.filter(nombre__iexact=nombre).exists():
        nombre = f"Copia {n} de {rol.nombre}"
        n += 1
    return crear_rol(
        actor,
        nombre=nombre,
        nivel=nivel,
        permisos=permisos,
        descripcion=rol.descripcion,
        exige_credencial_fuerte=rol.exige_credencial_fuerte,
        request=request,
    )


def cambiar_estado(actor, rol: Rol, *, activo: bool, request=None) -> Rol:
    if not puede_editar(actor, rol):
        raise RolNoEditable
    if not activo:
        if rol.es_base:
            raise ValidationError("Un rol base no se desactiva; puedes ajustar sus permisos.")
        en_uso = rol.asignaciones.count()
        if en_uso:
            raise ValidationError(
                f"Hay {en_uso} persona(s) con este rol. Quítaselo primero para desactivarlo."
            )
    rol.activo = activo
    rol.save(update_fields=["activo"])
    audit.log(
        "rbac.rol_activado" if activo else "rbac.rol_desactivado",
        actor=actor, request=request, rol=rol.clave,
    )  # fmt: skip
    return rol


def permisos_de(user) -> list[dict]:
    """Lo que puede hacer la persona, por módulo y pantalla, y de qué rol le viene."""
    roles = list(Rol.objects.filter(asignaciones__usuario=user, activo=True))
    efectivos = {}
    for r in roles:
        for codigo in r.permisos:
            efectivos.setdefault(codigo, []).append(r.nombre)
    filas = []
    for modulo in catalogo.agrupado():
        for pantalla in modulo["pantallas"]:
            acciones = [
                {**a, "roles": efectivos[a["codigo"]]}
                for a in pantalla["acciones"]
                if a["codigo"] in efectivos
            ]
            if acciones:
                filas.append(
                    {
                        "modulo": modulo["modulo"],
                        "pantalla": pantalla["pantalla"],
                        "acciones": acciones,
                    }
                )
    return filas
