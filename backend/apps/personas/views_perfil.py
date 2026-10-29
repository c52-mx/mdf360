"""«Mi cuenta»: la persona corrige sus propios datos básicos."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, Http404
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import audit

from . import services
from .models import Persona, Vehiculo
from .serializers import FOTO_MAX_BYTES


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


def _persona(request) -> Persona:
    persona = services.ensure_persona_for_user(request.user)
    return persona


def perfil_dict(persona: Persona) -> dict:
    return {
        **{campo: getattr(persona, campo) for campo in services.CAMPOS_DE_PERFIL},
        "fecha_nacimiento": persona.fecha_nacimiento.isoformat()
        if persona.fecha_nacimiento
        else None,
        "nombre_completo": persona.nombre_completo,
        "tiene_foto": bool(persona.foto),
        "acepto_foto": services.tiene_consentimiento_de_foto(persona),
        "aviso_pendiente": services.aviso_pendiente(persona),
    }


class PerfilEscritura(serializers.Serializer):
    nombre = serializers.CharField(max_length=100, required=False)
    apellido_paterno = serializers.CharField(max_length=100, required=False, allow_blank=True)
    apellido_materno = serializers.CharField(max_length=100, required=False, allow_blank=True)
    fecha_nacimiento = serializers.DateField(required=False, allow_null=True)
    telefono_fijo = serializers.CharField(max_length=20, required=False, allow_blank=True)
    calle_numero = serializers.CharField(max_length=200, required=False, allow_blank=True)
    colonia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    codigo_postal = serializers.CharField(max_length=10, required=False, allow_blank=True)
    alcaldia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    devocional_personal = serializers.CharField(max_length=200, required=False, allow_blank=True)
    oracion_familias = serializers.BooleanField(required=False)
    oracion_familias_detalle = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )


class FotoPropia(serializers.Serializer):
    foto = serializers.ImageField()
    acepta_foto = serializers.BooleanField(required=False, default=False)

    def validate_foto(self, value):
        if value.size > FOTO_MAX_BYTES:
            raise serializers.ValidationError("La foto pesa más de 5 MB.")
        return value


class MiPerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(perfil_dict(_persona(request)))

    def patch(self, request):
        persona = _persona(request)
        data = PerfilEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            services.actualizar_perfil(
                persona, data.validated_data, actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(perfil_dict(persona))


class AceptarAvisoView(APIView):
    """La persona acepta la versión vigente del aviso de privacidad."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        persona = _persona(request)
        services.aceptar_aviso_vigente(persona, actor=request.user, request=request)
        return Response(perfil_dict(persona))


class MiFotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        persona = _persona(request)
        if not persona.foto:
            raise Http404
        try:
            respuesta = FileResponse(persona.foto.open("rb"), content_type="image/jpeg")
        except FileNotFoundError as exc:
            raise Http404 from exc
        respuesta["Cache-Control"] = "private, max-age=300"
        return respuesta

    def post(self, request):
        persona = _persona(request)
        data = FotoPropia(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            services.guardar_foto_propia(
                persona,
                data.validated_data["foto"],
                acepta_foto=data.validated_data["acepta_foto"],
                actor=request.user,
                request=request,
            )
        except services.ConsentimientoRequerido:
            return _error("consent_required", "Para subir tu foto debes aceptar su uso.")
        except DjangoValidationError as exc:
            return _error("invalid_photo", " ".join(exc.messages))
        return Response(perfil_dict(persona))


def vehiculo_dict(v: Vehiculo) -> dict:
    return {
        "id": v.pk,
        "tipo": v.tipo,
        "tipo_display": v.get_tipo_display(),
        "marca": v.marca,
        "modelo": v.modelo,
        "anio": v.anio,
        "color": v.color,
        "placas": v.placas,
    }


class VehiculoEscritura(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=Vehiculo.Tipo.choices)
    marca = serializers.CharField(max_length=60, required=False, allow_blank=True)
    modelo = serializers.CharField(max_length=60, required=False, allow_blank=True)
    anio = serializers.IntegerField(min_value=1950, max_value=2100, required=False, allow_null=True)
    color = serializers.CharField(max_length=40, required=False, allow_blank=True)
    placas = serializers.CharField(max_length=15, required=False, allow_blank=True)


class MisVehiculosView(APIView):
    """Los vehículos de la propia persona: los registra, los corrige y los quita ella misma."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([vehiculo_dict(v) for v in _persona(request).vehiculos.all()])

    def post(self, request):
        persona = _persona(request)
        data = VehiculoEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        vehiculo = Vehiculo.objects.create(persona=persona, **data.validated_data)
        audit.log("persona.vehiculo_agregado", actor=request.user, target=persona, request=request)
        return Response(vehiculo_dict(vehiculo), status=status.HTTP_201_CREATED)


class MiVehiculoView(APIView):
    permission_classes = [IsAuthenticated]

    def _vehiculo(self, request, pk):
        vehiculo = _persona(request).vehiculos.filter(pk=pk).first()
        if vehiculo is None:
            raise Http404
        return vehiculo

    def patch(self, request, pk):
        vehiculo = self._vehiculo(request, pk)
        data = VehiculoEscritura(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        for campo, valor in data.validated_data.items():
            setattr(vehiculo, campo, valor)
        vehiculo.save()
        audit.log(
            "persona.vehiculo_editado", actor=request.user, target=vehiculo.persona, request=request
        )
        return Response(vehiculo_dict(vehiculo))

    def delete(self, request, pk):
        vehiculo = self._vehiculo(request, pk)
        persona = vehiculo.persona
        vehiculo.delete()
        audit.log("persona.vehiculo_quitado", actor=request.user, target=persona, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
