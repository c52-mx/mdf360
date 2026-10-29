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
    "roles.administrar": "Crear y editar roles y sus permisos",
    "unidades.ver_todas": "Ver todas las unidades",
    "unidades.gestionar": "Crear y administrar unidades y sus encargados",
    "avisos.iglesia": "Enviar avisos a toda la iglesia",
    "avisos.personas": "Enviar avisos a personas",
    "bitacora.ver": "Consultar la bitácora",
    "grupos.ver_todos": "Ver todos los Grupos de Conexión",
    "grupos.gestionar": "Crear y administrar Grupos de Conexión",
    "grupos.material": "Subir el estudio semanal",
    "ofrendas.ver_todas": "Ver las ofrendas de todos los grupos",
    "config.gestionar": "Cambiar los parámetros configurables",
    "peticiones.ver_todas": "Ver las peticiones de oración de todos los orígenes",
    "peticiones.configurar": "Editar el formulario de peticiones de oración",
    "peticiones.equipo_oracion": "Leer las peticiones compartidas con el equipo de oración",
}

# clave: (nombre, nivel jerárquico (0 = más alto), exige contraseña fuerte, permisos)
ROLES = {
    "admin_tecnico": (
        "Administrador Técnico",
        0,
        True,
        [
            "usuarios.invitar",
            "roles.gestionar",
            "roles.administrar",
            "bitacora.ver",
            "config.gestionar",
            "peticiones.configurar",
        ],
    ),
    "pastor": ("Pastor General", 1, True, list(PERMISOS)),
    # Igual al Pastor en lo administrativo; por debajo del Super Usuario, como todos.
    "secretaria": ("Secretaria", 1, True, list(PERMISOS)),
    "anciano": (
        "Anciano",
        2,
        False,
        [
            "personas.ver",
            "personas.crear",
            "personas.editar",
            "grupos.ver_todos",
            "grupos.material",
            "peticiones.ver_todas",
            "unidades.ver_todas",
        ],
    ),
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
    "equipo_oracion": ("Equipo de oración", 8, False, ["peticiones.equipo_oracion"]),
}
