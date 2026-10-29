"""Roles de equipo: lo que puede hacer cada rol dentro de un grupo o de un ministerio."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import catalogo, equipos
from .models import RolEquipo
from .permissions import requiere, tiene_permiso


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


def rol_equipo_dict(rol: RolEquipo) -> dict:
    return {
        "ambito": rol.ambito,
        "clave": rol.clave,
        "nombre": rol.nombre,
        "descripcion": rol.descripcion,
        "permisos": rol.permisos,
        "activo": rol.activo,
        "es_base": rol.es_base,
        "en_uso": equipos.en_uso(rol),
        "de_gestion": equipos.permisos_de_gestion(rol.permisos),
    }


class RolEquipoEscritura(serializers.Serializer):
    ambito = serializers.ChoiceField(choices=list(catalogo.AMBITOS))
    nombre = serializers.CharField(max_length=80)
    descripcion = serializers.CharField(max_length=300, required=False, allow_blank=True)
    permisos = serializers.ListField(child=serializers.CharField(max_length=40), allow_empty=True)


class RolEquipoCambio(serializers.Serializer):
    nombre = serializers.CharField(max_length=80, required=False)
    descripcion = serializers.CharField(max_length=300, required=False, allow_blank=True)
    permisos = serializers.ListField(
        child=serializers.CharField(max_length=40), required=False, allow_empty=True
    )
    activo = serializers.BooleanField(required=False)


class RolesEquipoView(APIView):
    """Lista los roles de equipo (`?ambito=` los acota) y da de alta roles nuevos."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [requiere("roles.administrar")()]
        return [IsAuthenticated()]

    def get(self, request):
        roles = RolEquipo.objects.all()
        if request.query_params.get("ambito"):
            roles = roles.filter(ambito=request.query_params["ambito"])
        if not (
            request.query_params.get("todos") and tiene_permiso(request.user, "roles.administrar")
        ):
            roles = roles.filter(activo=True)
        return Response([rol_equipo_dict(r) for r in roles])

    def post(self, request):
        data = RolEquipoEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            rol = equipos.crear(request.user, request=request, **data.validated_data)
        except DjangoValidationError as exc:
            return _error("invalid_role", " ".join(exc.messages))
        return Response(rol_equipo_dict(rol), status=status.HTTP_201_CREATED)


class RolEquipoView(APIView):
    permission_classes = [requiere("roles.administrar")]

    def patch(self, request, ambito, clave):
        rol = RolEquipo.objects.filter(ambito=ambito, clave=clave).first()
        if rol is None:
            return _error("not_found", "No existe el rol.", status.HTTP_404_NOT_FOUND)
        data = RolEquipoCambio(data=request.data)
        data.is_valid(raise_exception=True)
        cambios = dict(data.validated_data)
        activo = cambios.pop("activo", None)
        try:
            if cambios:
                equipos.editar(request.user, rol, request=request, **cambios)
            if activo is not None and activo != rol.activo:
                equipos.cambiar_estado(request.user, rol, activo=activo, request=request)
        except DjangoValidationError as exc:
            return _error("invalid_role", " ".join(exc.messages))
        return Response(rol_equipo_dict(rol))


class CatalogoEquipoView(APIView):
    """Las acciones que puede tener un rol dentro de un grupo o un ministerio."""

    permission_classes = [requiere("roles.gestionar")]

    def get(self, request, ambito):
        if ambito not in catalogo.AMBITOS:
            return _error("not_found", "Ámbito no válido.", status.HTTP_404_NOT_FOUND)
        return Response(catalogo.agrupado_equipo(ambito))
