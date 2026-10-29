from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import tiene_permiso

from . import services

#: Quién consulta los reportes de cada entidad (lo mismo que ya puede ver esos registros).
PERMISO_REPORTE = {"persona": "personas.ver", "grupo": "grupos.ver_todos"}


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


def _no_existe():
    return _error("not_found", "No existe ese formulario.", status.HTTP_404_NOT_FOUND)


class CatalogoFormulariosView(APIView):
    """Los formularios que se pueden diseñar y los tipos de campo disponibles."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "entidades": [{"clave": k, "nombre": v} for k, v in services.ENTIDADES.items()],
                "tipos": [{"clave": k, "nombre": v} for k, v in services.TIPOS.items()],
                "objetivos": [{"clave": k, "nombre": v} for k, v in services.OBJETIVOS.items()],
            }
        )


class FormularioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, entidad):
        if not services.entidad_valida(entidad):
            return _no_existe()
        return Response(services.vigente(entidad))

    def put(self, request, entidad):
        if not services.entidad_valida(entidad):
            return _no_existe()
        if not tiene_permiso(request.user, "formularios.gestionar"):
            return _error("forbidden", "No tienes permiso para esta acción.", 403)
        try:
            resultado = services.guardar(
                entidad, request.data.get("campos"), actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(resultado)


class ReporteView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, entidad):
        if not services.entidad_valida(entidad):
            return _no_existe()
        permitido = tiene_permiso(request.user, "formularios.gestionar") or tiene_permiso(
            request.user, PERMISO_REPORTE[entidad]
        )
        if not permitido:
            return _error("forbidden", "No tienes permiso para esta acción.", 403)
        return Response(services.reporte(entidad))
