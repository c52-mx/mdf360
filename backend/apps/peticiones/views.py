from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import requiere
from apps.core import audit, config

from . import crypto, registry, services
from .models import Peticion


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


def _denegado():
    return _error("forbidden", "No tienes permiso para esta acción.", status.HTTP_403_FORBIDDEN)


class OrigenesView(APIView):
    """Tipos de origen registrados (para filtros y etiquetas)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([{"tipo": o.tipo, "nombre": o.nombre} for o in registry.todos()])


class FormularioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        f = services.formulario_vigente()
        return Response(
            {
                "version": f.version,
                "campos": f.campos,
                "visibilidad_por_defecto": config.obtener("peticiones.visibilidad_por_defecto"),
                "dias_retencion": int(config.obtener("peticiones.dias_retencion")),
            }
        )

    def put(self, request):
        if not requiere("peticiones.configurar")().has_permission(request, self):
            return _denegado()
        try:
            f = services.guardar_formulario(
                request.data.get("campos"), actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response({"version": f.version, "campos": f.campos})


class CrearSerializer(serializers.Serializer):
    origen_tipo = serializers.CharField(max_length=40)
    origen_id = serializers.IntegerField(min_value=1)
    referencia_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    datos = serializers.DictField()
    visibilidad = serializers.ChoiceField(choices=Peticion.Visibilidad.choices, required=False)
    ocultar_nombre = serializers.BooleanField(required=False, default=False)


class Paginacion(PageNumberPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = "page_size"


def _con_contenido(p: Peticion, viewer) -> dict:
    try:
        return services.peticion_dict(p, con_contenido=True, viewer=viewer)
    except crypto.NoSePuedeDescifrar:
        return {**services.peticion_dict(p, con_contenido=False, viewer=viewer), "ilegible": True}


class PeticionesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services.purgar_vencidas()
        qs = services.peticiones_visibles(request.user)
        p = request.query_params
        if p.get("origen_tipo"):
            qs = qs.filter(origen_tipo=p["origen_tipo"])
        if p.get("origen_id", "").isdigit():
            qs = qs.filter(origen_id=int(p["origen_id"]))
        if p.get("estado") in ("activa", "atendida"):
            qs = qs.filter(estado=p["estado"])
        paginador = Paginacion()
        pagina = paginador.paginate_queryset(qs, request)
        audit.log(
            "peticion.consultadas", actor=request.user, request=request,
            cantidad=len(pagina), origen=p.get("origen_tipo", ""), origen_id=p.get("origen_id", ""),
        )  # fmt: skip
        return paginador.get_paginated_response([_con_contenido(x, request.user) for x in pagina])

    def post(self, request):
        services.purgar_vencidas()
        data = CrearSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            peticion = services.registrar_peticion(
                actor=request.user, request=request, **data.validated_data
            )
        except services.OrigenDesconocido:
            return _error("unknown_origin", "El origen de la petición no es válido.")
        except services.SinPermiso:
            return _denegado()
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        # Quien puede registrar no siempre puede leer (ej. el Secretario): solo ve la confirmación
        visible = services.puede_ver(request.user, peticion)
        return Response(
            services.peticion_dict(peticion, con_contenido=visible, viewer=request.user),
            status=status.HTTP_201_CREATED,
        )


class PeticionView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        peticion = get_object_or_404(Peticion, pk=pk)
        if not services.puede_ver(request.user, peticion):
            raise Http404
        if not services.puede_gestionar(request.user, peticion):
            return _denegado()
        try:
            services.cambiar_estado(
                peticion, request.data.get("estado"), actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(_con_contenido(peticion, request.user))
