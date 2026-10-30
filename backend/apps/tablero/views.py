from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import audit

from . import services
from .models import Mensaje


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


class PublicarSerializer(serializers.Serializer):
    origen_tipo = serializers.CharField(max_length=40)
    origen_id = serializers.IntegerField(min_value=1)
    texto = serializers.CharField(max_length=2000)
    fijado = serializers.BooleanField(required=False, default=False)


class TableroView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services.purgar_antiguos()
        tipo = request.query_params.get("origen_tipo", "")
        origen_id = request.query_params.get("origen_id", "")
        if not origen_id.isdigit():
            return _error("invalid", "Indica el origen del tablero.")
        qs = services.mensajes_de(request.user, tipo, int(origen_id))
        if qs is None:
            raise Http404
        return Response([services.mensaje_dict(m, request.user) for m in qs[:100]])

    def post(self, request):
        data = PublicarSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            mensaje = services.publicar(actor=request.user, request=request, **data.validated_data)
        except services.OrigenDesconocido:
            return _error("unknown_origin", "El origen no es válido.")
        except services.SinPermiso:
            return _error(
                "forbidden", "No tienes permiso para publicar aquí.", status.HTTP_403_FORBIDDEN
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(
            services.mensaje_dict(mensaje, request.user), status=status.HTTP_201_CREATED
        )


class MensajeView(APIView):
    permission_classes = [IsAuthenticated]

    def _mensaje(self, request, pk):
        mensaje = get_object_or_404(
            Mensaje, pk=pk, eliminado=False, estado=Mensaje.Estado.PUBLICADO
        )
        if services.mensajes_de(request.user, mensaje.origen_tipo, mensaje.origen_id) is None:
            raise Http404
        return mensaje

    def patch(self, request, pk):
        mensaje = self._mensaje(request, pk)
        if not services.puede_moderar(request.user, mensaje):
            return _error("forbidden", "No puedes cambiar este mensaje.", status.HTTP_403_FORBIDDEN)
        if "fijado" not in request.data or not isinstance(request.data["fijado"], bool):
            return _error("invalid", "Indica si el mensaje se fija o no.")
        mensaje.fijado = request.data["fijado"]
        mensaje.save(update_fields=["fijado"])
        audit.log(
            "tablero.fijado",
            actor=request.user,
            target=mensaje,
            request=request,
            fijado=mensaje.fijado,
        )
        return Response(services.mensaje_dict(mensaje, request.user))

    def delete(self, request, pk):
        mensaje = self._mensaje(request, pk)
        if not services.puede_moderar(request.user, mensaje):
            return _error("forbidden", "No puedes borrar este mensaje.", status.HTTP_403_FORBIDDEN)
        mensaje.eliminado = True
        mensaje.save(update_fields=["eliminado"])
        audit.log("tablero.eliminado", actor=request.user, target=mensaje, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MensajeRestaurarView(APIView):
    """Deshace un borrado: el mensaje vuelve al tablero (lo puede pedir quien puede moderarlo)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        mensaje = get_object_or_404(Mensaje, pk=pk, eliminado=True, estado=Mensaje.Estado.PUBLICADO)
        if services.mensajes_de(request.user, mensaje.origen_tipo, mensaje.origen_id) is None:
            raise Http404
        if not services.puede_moderar(request.user, mensaje):
            return _error(
                "forbidden", "No puedes restaurar este mensaje.", status.HTTP_403_FORBIDDEN
            )
        mensaje.eliminado = False
        mensaje.save(update_fields=["eliminado"])
        audit.log("tablero.restaurado", actor=request.user, target=mensaje, request=request)
        return Response(services.mensaje_dict(mensaje, request.user))


class VistoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tipo = str(request.data.get("origen_tipo", ""))
        origen_id = request.data.get("origen_id")
        if not isinstance(origen_id, int) or not services.marcar_visto(
            request.user, tipo, origen_id
        ):
            raise Http404
        return Response(status=status.HTTP_204_NO_CONTENT)


class MisTablerosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.mis_tableros(request.user))


class DestinoSerializer(serializers.Serializer):
    tipo = serializers.CharField(max_length=40)
    id = serializers.IntegerField(min_value=1)


class MasivoSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=1000)
    destinos = DestinoSerializer(many=True)
    fijado = serializers.BooleanField(required=False, default=False)


class DestinosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.destinos_para_publicar(request.user))


class MasivoView(APIView):
    """Un mismo aviso para varios tableros (iglesia, grupos, ministerios, personas)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = MasivoSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            resultado = services.publicar_masivo(
                actor=request.user, request=request, **data.validated_data
            )
        except DjangoValidationError as exc:
            return Response({"code": "invalid", "detail": " ".join(exc.messages)}, status=400)
        return Response(resultado, status=status.HTTP_201_CREATED)


class NoLeidosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.no_leidos(request.user))


class PorAutorizarView(APIView):
    """Avisos a toda la iglesia que esperan autorización (o que se rechazaron, para su autor)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import timedelta

        from django.utils import timezone

        puede = services.puede_autorizar_iglesia(request.user)
        pendientes = services.por_autorizar(request.user)
        # El autor también ve cuáles se rechazaron en los últimos días
        rechazados = Mensaje.objects.filter(
            estado=Mensaje.Estado.RECHAZADO,
            autor=request.user,
            resuelto_en__gte=timezone.now() - timedelta(days=7),
        )
        filas = list(pendientes) + list(rechazados)
        return Response(
            {
                "puede_autorizar": puede,
                "avisos": [
                    {
                        **services.mensaje_dict(m, request.user),
                        "puede_resolver": puede and m.autor_id != request.user.pk,
                    }
                    for m in filas
                ],
            }
        )


class ResolverAvisoView(APIView):
    permission_classes = [IsAuthenticated]
    autorizar = True

    def post(self, request, pk):
        mensaje = get_object_or_404(Mensaje, pk=pk, estado=Mensaje.Estado.PENDIENTE)
        if mensaje not in services.por_autorizar(request.user):
            raise Http404
        try:
            services.resolver(
                mensaje, autorizar=self.autorizar, actor=request.user, request=request
            )
        except services.SinPermiso:
            return _error("forbidden", "No puedes resolver este aviso.", status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(services.mensaje_dict(mensaje, request.user))


class AutorizarAvisoView(ResolverAvisoView):
    autorizar = True


class RechazarAvisoView(ResolverAvisoView):
    autorizar = False
