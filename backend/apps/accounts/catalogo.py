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
    Permiso("unidades.ver_todas", "Ministerios", "Ministerios", "Ver todos los ministerios"),
    Permiso(
        "unidades.gestionar",
        "Ministerios",
        "Ministerios",
        "Crear ministerios y asignar encargados y respaldos",
    ),
    Permiso(
        "avisos.iglesia",
        "Avisos",
        "Avisos masivos",
        "Enviar avisos a toda la iglesia",
        sensible=True,
    ),
    Permiso(
        "avisos.personas", "Avisos", "Avisos masivos", "Enviar avisos a personas", sensible=True
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


# ---------- Permisos dentro de un equipo (grupo de conexión o ministerio) ----------
# Cada persona tiene un rol por grupo o ministerio (encargado, respaldo, servidor…). Lo que ese
# rol permite se configura en la pantalla de roles; estas son las acciones que existen.
AMBITO_GRUPO = "grupo"
AMBITO_MINISTERIO = "ministerio"
AMBITOS = {AMBITO_GRUPO: "Grupo de Conexión", AMBITO_MINISTERIO: "Ministerio"}

CATALOGO_EQUIPO: dict[str, tuple[Permiso, ...]] = {
    AMBITO_GRUPO: (
        Permiso("ver", "Grupo", "Su grupo", "Consultar el grupo y su gente"),
        Permiso("integrantes", "Grupo", "Su grupo", "Agregar, cambiar y quitar integrantes"),
        Permiso("historial", "Grupo", "Asistencia", "Ver el historial de asistencia"),
        Permiso("capturar", "Grupo", "Asistencia", "Capturar la asistencia (el mismo día)"),
        Permiso("corregir", "Grupo", "Asistencia", "Corregir la asistencia de cualquier día"),
        Permiso("estudio", "Grupo", "Estudio semanal", "Ver el estudio de la semana"),
        Permiso("avisos", "Grupo", "Tablero", "Publicar avisos en el tablero del grupo"),
    ),
    AMBITO_MINISTERIO: (
        Permiso("ver", "Ministerio", "Su ministerio", "Consultar el ministerio y su gente"),
        Permiso(
            "integrantes", "Ministerio", "Su ministerio", "Agregar, cambiar y quitar servidores"
        ),
        Permiso("avisos", "Ministerio", "Tablero", "Publicar avisos en el tablero del ministerio"),
        Permiso(
            "peticiones_registrar",
            "Ministerio",
            "Peticiones de oración",
            "Registrar peticiones del ministerio",
        ),
        Permiso(
            "peticiones_ver",
            "Ministerio",
            "Peticiones de oración",
            "Ver todas las peticiones del ministerio",
            sensible=True,
        ),
    ),
}


def codigos_equipo(ambito: str) -> set[str]:
    return {p.codigo for p in CATALOGO_EQUIPO.get(ambito, ())}


def agrupado_equipo(ambito: str) -> list[dict]:
    return [
        {"codigo": p.codigo, "accion": p.accion, "pantalla": p.pantalla, "sensible": p.sensible}
        for p in CATALOGO_EQUIPO.get(ambito, ())
    ]


# Roles que vienen con el sistema y lo que permiten al inicio.
_G = codigos_equipo(AMBITO_GRUPO)
BASE_EQUIPO: dict[str, tuple[tuple[str, str, str, tuple[str, ...]], ...]] = {
    AMBITO_GRUPO: (
        ("lider", "Líder", "Encargado del grupo.", tuple(sorted(_G))),
        (
            "respaldo",
            "Respaldo",
            "Persona de respaldo del líder.",
            tuple(sorted(_G)),
        ),
        (
            "supervisor",
            "Supervisor",
            "Consulta sus grupos.",
            ("ver", "historial", "estudio", "avisos"),
        ),
        (
            "secretario",
            "Secretario",
            "Captura la asistencia.",
            ("ver", "capturar", "estudio", "avisos"),
        ),
        ("anfitrion", "Anfitrión", "Abre su casa para la reunión.", ()),
        ("tesorero", "Tesorero", "Cuida las ofrendas del grupo.", ()),
        ("servidor", "Servidor", "Sirve en el grupo.", ()),
        ("asistente", "Asistente", "Participa en el grupo.", ()),
    ),
    AMBITO_MINISTERIO: (
        (
            "encargado",
            "Encargado",
            "Responsable del ministerio.",
            ("ver", "integrantes", "avisos", "peticiones_registrar", "peticiones_ver"),
        ),
        (
            "respaldo",
            "Respaldo",
            "Persona de respaldo del encargado.",
            ("ver", "integrantes", "avisos", "peticiones_registrar", "peticiones_ver"),
        ),
        ("servidor", "Servidor", "Sirve en el ministerio.", ("ver",)),
    ),
}
