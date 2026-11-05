from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import audit

from . import ofrendas as base
from . import ofrendas_iglesia as ig
from .models import Ofrenda, OfrendaIglesia, TipoOfrenda


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


def _denegado():
    return _error("forbidden", "No tienes permiso para esta acción.", status.HTTP_403_FORBIDDEN)


class TipoSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=80, required=False)
    para_grupo = serializers.BooleanField(required=False)
    para_iglesia = serializers.BooleanField(required=False)
    activo = serializers.BooleanField(required=False)


class TiposView(APIView):
    """Catálogo único de tipos. ?para=grupo|iglesia lo limita a lo que se usa en ese lugar."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not base.tiene_acceso(request.user):
            return _denegado()
        tipos = TipoOfrenda.objects.all()
        para = request.query_params.get("para", "")
        if para == "grupo":
            tipos = tipos.filter(para_grupo=True)
        elif para == "iglesia":
            tipos = tipos.filter(para_iglesia=True)
        if not ig.puede_administrar_catalogo(request.user):
            tipos = tipos.filter(activo=True)
        return Response(
            {
                "puede_administrar": ig.puede_administrar_catalogo(request.user),
                "tipos": [ig.tipo_dict(t) for t in tipos],
            }
        )

    def post(self, request):
        if not ig.puede_administrar_catalogo(request.user):
            return _denegado()
        data = TipoSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            tipo = ig.guardar_tipo(datos=data.validated_data, actor=request.user, request=request)
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(ig.tipo_dict(tipo), status=status.HTTP_201_CREATED)


class TipoView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, tid):
        if not ig.puede_administrar_catalogo(request.user):
            return _denegado()
        tipo = get_object_or_404(TipoOfrenda, pk=tid)
        data = TipoSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            ig.guardar_tipo(
                datos=data.validated_data, actor=request.user, tipo=tipo, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(ig.tipo_dict(tipo))


class CapturaIglesiaSerializer(serializers.Serializer):
    fecha = serializers.DateField(required=False)
    tipo = serializers.PrimaryKeyRelatedField(queryset=TipoOfrenda.objects.all())
    nota = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    monto = serializers.DecimalField(max_digits=10, decimal_places=2)


class OfrendasIglesiaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not base.tiene_acceso(request.user):
            return _denegado()
        return Response(
            {
                "ofrendas": [
                    ig.ofrenda_iglesia_dict(o, detalle=False) for o in ig.visibles(request.user)
                ],
                "puede_capturar": ig.puede_capturar(request.user),
                "puede_avalar": ig.puede_avalar(request.user),
            }
        )

    def post(self, request):
        if not ig.puede_capturar(request.user):
            return _denegado()
        data = CapturaIglesiaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        datos = data.validated_data
        try:
            ofrenda = ig.capturar(
                fecha=datos.get("fecha") or timezone.localdate(),
                tipo=datos["tipo"],
                monto=datos["monto"],
                nota=datos["nota"],
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(ig.ofrenda_iglesia_dict(ofrenda), status=status.HTTP_201_CREATED)


class CorreccionIglesiaSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    motivo = serializers.CharField(max_length=300)


class OfrendaIglesiaView(APIView):
    permission_classes = [IsAuthenticated]

    def _ofrenda(self, request, oid):
        ofrenda = get_object_or_404(
            OfrendaIglesia.objects.select_related("tipo", "capturada_por"), pk=oid
        )
        if not ig.puede_ver(request.user, ofrenda):
            raise Http404
        return ofrenda

    def get(self, request, oid):
        return Response(ig.ofrenda_iglesia_dict(self._ofrenda(request, oid)))

    def patch(self, request, oid):
        ofrenda = self._ofrenda(request, oid)
        if not ig.puede_capturar(request.user):
            return _denegado()
        data = CorreccionIglesiaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            ig.corregir(ofrenda, actor=request.user, request=request, **data.validated_data)
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(ig.ofrenda_iglesia_dict(ofrenda))


class AvalIglesiaSerializer(serializers.Serializer):
    monto_contado = serializers.DecimalField(max_digits=10, decimal_places=2)
    credential = serializers.CharField(max_length=128, trim_whitespace=False)


class AvalIglesiaView(APIView):
    """Avala con la cifra contada y volviendo a escribir el PIN. Nadie avala lo que capturó."""

    permission_classes = [IsAuthenticated]

    def post(self, request, oid):
        ofrenda = get_object_or_404(OfrendaIglesia.objects.select_related("tipo"), pk=oid)
        if not ig.puede_avalar(request.user):
            raise Http404
        data = AvalIglesiaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = request.user
        if user.is_locked():
            return _error(
                "locked",
                "Demasiados intentos. Espera unos minutos.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if not user.check_password(data.validated_data["credential"]):
            user.register_failure()
            audit.log(
                "ofrenda_iglesia.aval_pin_incorrecto", actor=user, target=ofrenda, request=request
            )
            return _error("invalid_pin", "El PIN no es correcto.")
        user.clear_failures()
        try:
            ig.avalar(
                ofrenda,
                monto_contado=data.validated_data["monto_contado"],
                actor=user,
                request=request,
            )
        except base.ElPropioCapturista:
            return _error(
                "own_capture",
                "No puedes avalar una ofrenda que tú capturaste.",
                status.HTTP_403_FORBIDDEN,
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(ig.ofrenda_iglesia_dict(ofrenda))


def _fecha(valor):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise serializers.ValidationError({"fecha": "Fecha no válida."}) from exc


def _entero(valor):
    return int(valor) if valor and valor.isdigit() else None


class ResumenOfrendasView(APIView):
    """Tabla, totales y series de lo que la persona puede ver, con filtros dinámicos."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not base.tiene_acceso(request.user):
            return _denegado()
        p = request.query_params
        origen = p.get("origen", "")
        estado = p.get("estado", "")
        if origen not in ("", "grupo", "iglesia"):
            return _error("invalid", "Origen no válido.")
        if estado not in ("", *Ofrenda.Estado.values):
            return _error("invalid", "Estado no válido.")
        audit.log("ofrenda.resumen_consultado", actor=request.user, request=request)
        return Response(
            ig.resumen(
                request.user,
                desde=_fecha(p.get("desde")),
                hasta=_fecha(p.get("hasta")),
                origen=origen,
                tipo=_entero(p.get("tipo")),
                grupo=_entero(p.get("grupo")),
                estado=estado,
            )
        )
