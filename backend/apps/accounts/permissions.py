from rest_framework.permissions import BasePermission


def tiene_permiso(user, codigo: str) -> bool:
    return bool(user and user.is_authenticated and codigo in user.permisos())


def requiere(codigo: str):
    """Fabrica una clase de permiso de DRF que exige el permiso `codigo`."""

    class _Requiere(BasePermission):
        message = "No tienes permiso para esta acción."

        def has_permission(self, request, view):
            return tiene_permiso(request.user, codigo)

    _Requiere.__name__ = f"Requiere_{codigo.replace('.', '_')}"
    return _Requiere
