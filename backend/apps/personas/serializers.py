from rest_framework import serializers

from . import services
from .models import Persona, PersonaMovimiento, Procedencia, ProcesoDiscipular

FOTO_MAX_BYTES = 5 * 1024 * 1024


class PersonaListSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    tiene_foto = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = [
            "id",
            "nombre_completo",
            "nivel",
            "procedencia",
            "whatsapp",
            "grupo_conexion",
            "activo",
            "tiene_foto",
        ]

    def get_tiene_foto(self, obj) -> bool:
        return bool(obj.foto)


class PersonaCreateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    apellido_paterno = serializers.CharField(max_length=100, required=False, allow_blank=True)
    apellido_materno = serializers.CharField(max_length=100, required=False, allow_blank=True)
    whatsapp = serializers.CharField(max_length=40)
    procedencia = serializers.ChoiceField(
        choices=Procedencia.choices, default=Procedencia.VISITANTE
    )
    acepta_datos = serializers.BooleanField()
    acepta_foto = serializers.BooleanField(default=False)


class ProcesoPersonaSerializer(serializers.Serializer):
    proceso = serializers.PrimaryKeyRelatedField(queryset=ProcesoDiscipular.objects.all())
    completado = serializers.BooleanField()
    fecha = serializers.DateField(required=False, allow_null=True)
    maestro = serializers.CharField(max_length=120, required=False, allow_blank=True)


class PersonaDetailSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    edad = serializers.IntegerField(read_only=True)
    tiene_foto = serializers.SerializerMethodField()
    faltantes_edu = serializers.SerializerMethodField()
    procesos = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = [
            "id",
            "nivel",
            "procedencia",
            "activo",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "nombre_completo",
            "fecha_nacimiento",
            "edad",
            "tiene_foto",
            "whatsapp",
            "telefono_fijo",
            "email",
            "calle_numero",
            "colonia",
            "codigo_postal",
            "alcaldia",
            "sector",
            "grupo_conexion",
            "lider",
            "miembro_desde",
            "sirve_en_ministerio",
            "ministerios",
            "devocional_personal",
            "oracion_familias",
            "oracion_familias_detalle",
            "otros_cursos",
            "observaciones",
            "datos_extra",
            "faltantes_edu",
            "procesos",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "nivel", "activo", "creado_en", "actualizado_en"]

    def get_tiene_foto(self, obj) -> bool:
        return bool(obj.foto)

    def get_faltantes_edu(self, obj) -> list[str]:
        return services.faltantes_para_edu(obj)

    def get_procesos(self, obj) -> list[dict]:
        return [
            {**fila, "fecha": fila["fecha"].isoformat() if fila["fecha"] else None}
            for fila in services.procesos_de(obj)
        ]

    def validate_whatsapp(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from apps.accounts.phone import normalize_whatsapp

        if not value:
            return ""
        try:
            normalizado = normalize_whatsapp(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        duplicado = Persona.objects.filter(whatsapp=normalizado).exclude(pk=self.instance.pk)
        if duplicado.exists():
            raise serializers.ValidationError("Ya existe otra persona con ese número.")
        return normalizado


class MovimientoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = PersonaMovimiento
        fields = ["id", "tipo", "tipo_display", "fecha", "motivo", "creado_en"]


class NivelSerializer(serializers.Serializer):
    nivel = serializers.ChoiceField(choices=["participante", "edu"])


class BajaSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    motivo = serializers.CharField(max_length=300)


class FotoSerializer(serializers.Serializer):
    foto = serializers.ImageField()

    def validate_foto(self, value):
        if value.size > FOTO_MAX_BYTES:
            raise serializers.ValidationError("La foto pesa más de 5 MB.")
        return value


class ProcesoCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcesoDiscipular
        fields = ["id", "nombre", "orden", "pide_maestro"]
