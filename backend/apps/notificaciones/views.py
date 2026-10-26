from django.conf import settings
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import audit

from . import push
from .models import Suscripcion


class _Llaves(serializers.Serializer):
    p256dh = serializers.CharField(max_length=200)
    auth = serializers.CharField(max_length=100)


class SuscribirSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)
    keys = _Llaves()


class DesuscribirSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)


class ConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activo = push.disponible()
        return Response(
            {"disponible": activo, "clave_publica": settings.VAPID_PUBLIC_KEY if activo else ""}
        )


class SuscribirView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not push.disponible():
            return Response(
                {"code": "unavailable", "detail": "Las notificaciones no están activas."},
                status=status.HTTP_409_CONFLICT,
            )
        data = SuscribirSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        suscripcion, creada = Suscripcion.objects.update_or_create(
            endpoint=d["endpoint"],
            defaults={
                "usuario": request.user,
                "p256dh": d["keys"]["p256dh"],
                "auth": d["keys"]["auth"],
                "agente": request.headers.get("User-Agent", "")[:200],
            },
        )
        if creada:
            audit.log(
                "notificaciones.suscrita", actor=request.user, target=suscripcion, request=request
            )
        return Response(status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK)


class DesuscribirView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = DesuscribirSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        borradas, _ = Suscripcion.objects.filter(
            usuario=request.user, endpoint=data.validated_data["endpoint"]
        ).delete()
        if borradas:
            audit.log("notificaciones.cancelada", actor=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProbarView(APIView):
    """Manda una notificación de prueba a los dispositivos de quien la pide."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        enviados = push.notificar(
            titulo="MDF360",
            cuerpo="Así se verán tus avisos. Si lo ves y lo oyes, todo está listo.",
            url="/cuenta",
            etiqueta="prueba",
            usuarios=[request.user],
        )
        if not enviados:
            return Response(
                {"code": "no_devices", "detail": "Este usuario no tiene dispositivos activados."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({"dispositivos": enviados})
