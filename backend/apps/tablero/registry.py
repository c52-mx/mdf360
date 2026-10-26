"""Orígenes del tablero de mensajes (M1-19): cada módulo se registra y decide quién publica y lee.

Igual que en peticiones: el componente no decide permisos por su cuenta, así que el mismo tablero
sirve para un grupo, un curso, un área de servicio o la iglesia en general.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Origen:
    tipo: str  # clave estable, p. ej. «grupo»
    nombre: str  # «Grupo de Conexión»
    etiqueta: Callable[[int], str | None]  # nombre visible del origen, None si no existe
    puede_publicar: Callable[[object, int], bool]
    puede_leer: Callable[[object, int], bool]
    # Ids que el usuario puede leer: None = todos, lista = solo esos
    ids_legibles: Callable[[object], list[int] | None]
    # [(id, etiqueta)] de los tableros que el usuario puede leer (para la pantalla «Avisos»)
    listar: Callable[[object], list[tuple[int, str]]] | None = None
    # Pantalla donde se lee el tablero (al tocar la notificación); None = «Avisos»
    ruta: Callable[[int], str] | None = None


_ORIGENES: dict[str, Origen] = {}


def registrar(origen: Origen) -> None:
    _ORIGENES[origen.tipo] = origen


def obtener(tipo: str) -> Origen | None:
    return _ORIGENES.get(tipo)


def todos() -> list[Origen]:
    return list(_ORIGENES.values())
