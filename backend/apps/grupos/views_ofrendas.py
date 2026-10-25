from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import audit

from . import ofrendas as of
from .models import Grupo, GrupoMiembro, Ofrenda, Reunion


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


def _denegado():
    return _error("forbidden", "No tienes permiso para esta acción.", status.HTTP_403_FORBIDDEN)


class CapturaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=Ofrenda.Tipo.choices, default="regular")
    concepto = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    monto = serializers.DecimalField(max_digits=10, decimal_places=2)


class OfrendasReunionView(APIView):
    permission_classes = [IsAuthenticated]

    def _reunion(self, rid):
        return get_object_or_404(Reunion.objects.select_related("grupo"), pk=rid)

    def get(self, request, rid):
        reunion = self._reunion(rid)
        if not of.puede_ver_ofrendas(request.user, reunion):
            raise Http404
        lista = Ofrenda.objects.filter(reunion=reunion).select_related("reunion__grupo")
        audit.log("ofrenda.consultada", actor=request.user, target=reunion, request=request)
        return Response(
            {
                "ofrendas": [of.ofrenda_dict(o) for o in lista],
                "puede_capturar": of.puede_capturar_ofrenda(request.user, reunion),
                "puede_avalar": of.puede_avalar(request.user, reunion.grupo),
            }
        )

    def post(self, request, rid):
        reunion = self._reunion(rid)
        if not of.puede_ver_ofrendas(request.user, reunion):
            raise Http404
        if not of.puede_capturar_ofrenda(request.user, reunion):
            return _denegado()
        data = CapturaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            ofrenda = of.capturar(
                reunion, actor=request.user, request=request, **data.validated_data
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(of.ofrenda_dict(ofrenda), status=status.HTTP_201_CREATED)


class CorreccionSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    motivo = serializers.CharField(max_length=300)


class OfrendaView(APIView):
    permission_classes = [IsAuthenticated]

    def _ofrenda(self, request, oid):
        ofrenda = get_object_or_404(Ofrenda.objects.select_related("reunion__grupo"), pk=oid)
        if not of.puede_ver_ofrendas(request.user, ofrenda.reunion):
            raise Http404
        return ofrenda

    def get(self, request, oid):
        return Response(of.ofrenda_dict(self._ofrenda(request, oid)))

    def patch(self, request, oid):
        ofrenda = self._ofrenda(request, oid)
        if not of.puede_corregir(request.user, ofrenda):
            return _denegado()
        data = CorreccionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            of.corregir(ofrenda, actor=request.user, request=request, **data.validated_data)
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(of.ofrenda_dict(ofrenda))


class AvalSerializer(serializers.Serializer):
    monto_contado = serializers.DecimalField(max_digits=10, decimal_places=2)
    credential = serializers.CharField(max_length=128, trim_whitespace=False)


class AvalView(APIView):
    """El Tesorero avala con la cifra que contó y volviendo a escribir su PIN."""

    permission_classes = [IsAuthenticated]

    def post(self, request, oid):
        ofrenda = get_object_or_404(Ofrenda.objects.select_related("reunion__grupo"), pk=oid)
        if not of.puede_avalar(request.user, ofrenda.reunion.grupo):
            raise Http404
        data = AvalSerializer(data=request.data)
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
            audit.log("ofrenda.aval_pin_incorrecto", actor=user, target=ofrenda, request=request)
            return _error("invalid_pin", "El PIN no es correcto.")
        user.clear_failures()
        try:
            of.avalar(
                ofrenda,
                monto_contado=data.validated_data["monto_contado"],
                actor=user,
                request=request,
            )
        except of.ElPropioCapturista:
            return _error(
                "own_capture",
                "No puedes avalar una ofrenda que tú capturaste.",
                status.HTTP_403_FORBIDDEN,
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(of.ofrenda_dict(ofrenda))


class OfrendasPendientesView(APIView):
    """Ofrendas por avalar (o con diferencia) de los grupos donde la persona es Tesorera.

    Si un grupo no tiene Tesorero, también aparecen para su Líder y para el Pastor (suplencia).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        persona = getattr(request.user, "persona", None)
        ids = set()
        if persona is not None:
            ids |= set(
                GrupoMiembro.objects.filter(
                    persona=persona, activo=True, rol=GrupoMiembro.Rol.TESORERO
                ).values_list("grupo_id", flat=True)
            )
        for grupo in Grupo.objects.filter(activo=True):
            if of.aval_suplente(request.user, grupo):
                ids.add(grupo.pk)
        lista = Ofrenda.objects.filter(
            reunion__grupo_id__in=list(ids),
            estado__in=[Ofrenda.Estado.PENDIENTE, Ofrenda.Estado.DIFERENCIA],
        ).select_related("reunion__grupo")
        return Response([of.ofrenda_dict(o, detalle=False) for o in lista])
