"""Catálogo de permisos: qué acciones existen, en qué módulo y pantalla.

El código define el catálogo porque solo él puede hacer cumplir cada permiso. La pantalla de
roles no inventa acciones: combina estas. Cada permiso nuevo del sistema se registra aquí con su
módulo, su pantalla y una descripción, y aparece solo en la matriz de roles.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Permiso:
    codigo: str
    modulo: str
    pantalla: str
    accion: str
    #: Da acceso a información delicada o a decisiones de peso: la pantalla de roles lo marca.
    sensible: bool = False


CATALOGO: tuple[Permiso, ...] = (
    Permiso("personas.ver", "Personas", "Expedientes", "Ver expedientes", sensible=True),
    Permiso("personas.crear", "Personas", "Expedientes", "Registrar contactos"),
    Permiso(
        "personas.editar", "Personas", "Expedientes", "Editar expedientes y procesos", sensible=True
    ),
    Permiso(
        "personas.baja",
        "Personas",
        "Expedientes",
        "Dar de baja, trasladar o reactivar",
        sensible=True,
    ),
    Permiso("grupos.ver_todos", "Grupos", "Grupos de Conexión", "Ver todos los grupos"),
    Permiso(
        "grupos.gestionar",
        "Grupos",
        "Grupos de Conexión",
        "Crear, editar, suspender y asignar integrantes",
    ),
    Permiso("grupos.material", "Grupos", "Estudio semanal", "Subir el estudio de la semana"),
    Permiso(
        "ofrendas.ver_todas",
        "Grupos",
        "Ofrendas",
        "Ver las ofrendas de todos los grupos",
        sensible=True,
    ),
    Permiso(
        "peticiones.ver_todas",
        "Peticiones",
        "Peticiones de oración",
        "Ver las peticiones de todos los orígenes",
        sensible=True,
    ),
    Permiso(
        "peticiones.equipo_oracion",
        "Peticiones",
        "Peticiones de oración",
        "Leer las peticiones compartidas con el equipo de oración",
        sensible=True,
    ),
    Permiso(
        "peticiones.configurar", "Peticiones", "Formulario", "Editar el formulario de peticiones"
    ),
    Permiso(
        "usuarios.invitar",
        "Administración",
        "Invitaciones y accesos",
        "Invitar personas y reiniciar accesos",
    ),
    Permiso(
        "roles.gestionar",
        "Administración",
        "Roles y permisos",
        "Asignar roles a las personas",
        sensible=True,
    ),
    Permiso(
        "roles.administrar",
        "Administración",
        "Roles y permisos",
        "Crear y editar roles y sus permisos",
        sensible=True,
    ),
    Permiso("bitacora.ver", "Administración", "Bitácora", "Consultar la bitácora"),
    Permiso(
        "config.gestionar", "Administración", "Configuración", "Cambiar los parámetros del sistema"
    ),
)

POR_CODIGO = {p.codigo: p for p in CATALOGO}


def codigos() -> set[str]:
    return set(POR_CODIGO)


def agrupado() -> list[dict]:
    """El catálogo como módulo › pantalla › acciones, en el orden en que se declaró."""
    modulos: dict[str, dict[str, list[dict]]] = {}
    for p in CATALOGO:
        modulos.setdefault(p.modulo, {}).setdefault(p.pantalla, []).append(
            {"codigo": p.codigo, "accion": p.accion, "sensible": p.sensible}
        )
    return [
        {
            "modulo": modulo,
            "pantallas": [
                {"pantalla": pantalla, "acciones": a} for pantalla, a in pantallas.items()
            ],
        }
        for modulo, pantallas in modulos.items()
    ]
