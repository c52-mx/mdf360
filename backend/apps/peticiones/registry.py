"""Orígenes de peticiones: cada módulo que usa el componente se registra aquí.

Una petición siempre pertenece a un origen (por ejemplo, un Grupo de Conexión). El módulo dueño
del origen decide quién puede registrar y quién puede ver; el componente de peticiones nunca lo
decide por su cuenta. Así se reutiliza en otros lugares (cursos, eventos…) sin cambiar su lógica.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Origen:
    tipo: str  # clave estable, por ejemplo «grupo»
    nombre: str  # «Grupo de Conexión»
    # (id, referencia_id) -> etiqueta fija que se guarda con la petición, o None si no existe
    etiqueta: Callable[[int, int | None], str | None]
    puede_registrar: Callable[[object, int], bool]
    puede_ver: Callable[[object, int], bool]
    # Ids visibles para el usuario: None = todos, lista = solo esos
    ids_visibles: Callable[[object], list[int] | None]


_ORIGENES: dict[str, Origen] = {}


def registrar(origen: Origen) -> None:
    _ORIGENES[origen.tipo] = origen


def obtener(tipo: str) -> Origen | None:
    return _ORIGENES.get(tipo)


def todos() -> list[Origen]:
    return list(_ORIGENES.values())
