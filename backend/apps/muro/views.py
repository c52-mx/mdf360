from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


class DestinoSerializer(serializers.Serializer):
    tipo = serializers.CharField(max_length=12)
    id = serializers.IntegerField(min_value=1)


class PublicarSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=2000)
    destinos = DestinoSerializer(many=True)


class MuroView(APIView):
    """El muro de la persona: lo dirigido a ella, página por página (`?antes=<id>`)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        antes = request.query_params.get("antes", "")
        tipo = request.query_params.get("audiencia_tipo", "")
        ref = request.query_params.get("audiencia_id", "")
        if (antes and not antes.isdigit()) or (tipo and not ref.isdigit()):
            return _error("invalid", "Los parámetros del muro no son válidos.")
        filas = services.muro(
            request.user,
            antes=int(antes) if antes else None,
            audiencia=(tipo, int(ref)) if tipo else None,
        )
        hay_mas = len(filas) > services.PAGINA
        filas = filas[: services.PAGINA]
        return Response(
            {
                "resultados": [services.publicacion_dict(p, request.user) for p in filas],
                "siguiente": filas[-1].pk if hay_mas and filas else None,
            }
        )

    def post(self, request):
        data = PublicarSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            publicacion = services.publicar(
                actor=request.user, request=request, **data.validated_data
            )
        except services.SinPermiso:
            return _error(
                "forbidden", "No puedes publicar en alguna de esas audiencias.",
                status.HTTP_403_FORBIDDEN,
            )  # fmt: skip
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(
            services.publicacion_dict(publicacion, request.user), status=status.HTTP_201_CREATED
        )


class DestinosView(APIView):
    """Las audiencias a las que la persona puede publicar (vacío = no puede publicar)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.destinos_para_publicar(request.user))
