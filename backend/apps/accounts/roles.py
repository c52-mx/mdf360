"""Roles y permisos base (M1-07). Siguen la matriz de confidencialidad aprobada (v3.2, sec. 3.3).

Estos valores siembran el catálogo; después se pueden ajustar desde la base de datos sin tocar
código. Los permisos de Supervisor y Líder se limitan a "registrar contactos" hasta que exista el
módulo de Grupos (alcance por grupo, M1-08): sin alcance no pueden ver expedientes ajenos.
"""

PERMISOS = {
    "personas.ver": "Ver expedientes",
    "personas.crear": "Registrar contactos",
    "personas.editar": "Editar expedientes y procesos",
    "personas.baja": "Dar de baja o reactivar",
    "usuarios.invitar": "Invitar personas y reiniciar accesos",
    "roles.gestionar": "Asignar roles",
    "bitacora.ver": "Consultar la bitácora",
}

# clave: (nombre, nivel jerárquico (0 = más alto), exige contraseña fuerte, permisos)
ROLES = {
    "admin_tecnico": (
        "Administrador Técnico",
        0,
        True,
        ["usuarios.invitar", "roles.gestionar", "bitacora.ver"],
    ),
    "pastor": ("Pastor General", 1, True, list(PERMISOS)),
    "anciano": ("Anciano", 2, False, ["personas.ver", "personas.crear", "personas.editar"]),
    "supervisor": (
        "Supervisor / Director de Área",
        3,
        False,
        ["personas.crear", "usuarios.invitar"],
    ),
    "lider": ("Líder / Maestro", 4, False, ["personas.crear", "usuarios.invitar"]),
    "secretario": ("Secretario de grupo", 5, False, ["personas.crear"]),
    "tesorero": ("Tesorero", 5, True, []),
    "servidor": ("Servidor", 6, False, []),
    "miembro": ("Miembro / Asistente", 7, False, []),
}
