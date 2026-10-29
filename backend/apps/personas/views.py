import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import requiere
from apps.core import audit
from apps.formularios import services as formularios

from . import aviso, jerarquia, services
from .models import Persona, ProcesoDiscipular
from .serializers import (
    BajaSerializer,
    FotoSerializer,
    MovimientoSerializer,
    NivelSerializer,
    PersonaCreateSerializer,
    PersonaDetailSerializer,
    PersonaListSerializer,
    ProcesoCatalogoSerializer,
    ProcesoPersonaSerializer,
    TrasladoSerializer,
)


def _error(code: str, detail, http_status=status.HTTP_400_BAD_REQUEST, **extra):
    return Response({"code": code, "detail": detail, **extra}, status=http_status)


def _sin_jerarquia():
    return _error(
        "forbidden",
        "Solo un superior puede dar de baja, trasladar o reactivar a esta persona.",
        status.HTTP_403_FORBIDDEN,
    )


def _validation_detail(exc: DjangoValidationError) -> str:
    return " ".join(exc.messages)


class PersonaPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class AvisoPrivacidadView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        version, texto = aviso.vigente()
        return Response({"version": version, "texto": texto})


class AvisoPrivacidadPublicarView(APIView):
    """Publica una versión nueva del aviso: quien administra la configuración del sistema."""

    permission_classes = [requiere("config.gestionar")]

    def post(self, request):
        try:
            services.publicar_aviso(
                version=str(request.data.get("version", "")),
                texto=str(request.data.get("texto", "")),
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        version, texto = aviso.vigente()
        return Response({"version": version, "texto": texto}, status=status.HTTP_201_CREATED)


class CatalogoProcesosView(APIView):
    permission_classes = [requiere("personas.editar")]

    def get(self, request):
        procesos = ProcesoDiscipular.objects.filter(activo=True)
        return Response(ProcesoCatalogoSerializer(procesos, many=True).data)


class PersonaViewSet(viewsets.ModelViewSet):
    """Expediente digital (EDU).

    Permisos por rol (M1-07): ver, crear, editar y baja/reactivación. El alcance por grupo
    (M1-08) llega con el módulo de Grupos.
    """

    ACCIONES = {
        "list": "personas.ver",
        "retrieve": "personas.ver",
        "movimientos": "personas.ver",
        "create": "personas.crear",
        "partial_update": "personas.editar",
        "nivel": "personas.editar",
        "procesos": "personas.editar",
        "baja": "personas.baja",
        "traslado": "personas.baja",
        "reactivar": "personas.baja",
    }

    def get_permissions(self):
        if self.action == "foto":
            codigo = "personas.editar" if self.request.method == "POST" else "personas.ver"
        else:
            codigo = self.ACCIONES.get(self.action, "personas.editar")
        return [IsAuthenticated(), requiere(codigo)()]

    pagination_class = PersonaPagination
    http_method_names = ["get", "post", "patch", "head", "options"]
    lookup_value_regex = r"\d+"
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        qs = Persona.objects.select_related("usuario").prefetch_related(
            "usuario__asignaciones__rol", "membresias__grupo"
        )
        if self.action != "list":
            return qs
        p = self.request.query_params
        activo = p.get("activo", "true")
        if activo != "all":
            qs = qs.filter(activo=activo != "false")
        if p.get("nivel"):
            qs = qs.filter(nivel=p["nivel"])
        if p.get("procedencia"):
            qs = qs.filter(procedencia=p["procedencia"])
        if p.get("grupo", "").isdigit():
            qs = qs.filter(membresias__grupo_id=int(p["grupo"]), membresias__activo=True)
        if p.get("rol"):
            qs = qs.filter(usuario__asignaciones__rol__clave=p["rol"])
        qs = qs.distinct()
        q = (p.get("q") or "").strip()
        if q:
            cond = Q()
            for palabra in q.split():
                cond &= (
                    Q(nombre__unaccent__icontains=palabra)
                    | Q(apellido_paterno__unaccent__icontains=palabra)
                    | Q(apellido_materno__unaccent__icontains=palabra)
                    | Q(email__unaccent__icontains=palabra)
                    | Q(grupo_conexion__unaccent__icontains=palabra)
                )
            digitos = re.sub(r"\D", "", q)
            if len(digitos) >= 3:
                cond |= Q(whatsapp__contains=digitos)
            qs = qs.filter(cond)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PersonaListSerializer
        if self.action == "create":
            return PersonaCreateSerializer
        return PersonaDetailSerializer

    def create(self, request, *args, **kwargs):
        data = PersonaCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = dict(data.validated_data)
        acepta_datos = v.pop("acepta_datos")
        acepta_foto = v.pop("acepta_foto")
        try:
            v["datos_extra"] = formularios.aplicar("persona", {}, v.pop("datos_extra", {}))
        except DjangoValidationError as exc:
            return _error("invalid", _validation_detail(exc))
        try:
            persona = services.crear_persona(
                datos=v,
                acepta_datos=acepta_datos,
                acepta_foto=acepta_foto,
                actor=request.user,
                request=request,
            )
        except services.ConsentimientoRequerido:
            return _error("consent_required", "La persona debe aceptar el aviso de privacidad.")
        except services.PersonaDuplicada as dup:
            return _error(
                "duplicate",
                "Ya existe una persona con ese número.",
                status.HTTP_409_CONFLICT,
                persona_id=dup.persona.pk,
                nombre=dup.persona.nombre_completo,
            )
        except DjangoValidationError as exc:
            return _error("invalid_number", _validation_detail(exc))
        return Response(PersonaDetailSerializer(persona).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        persona = self.get_object()
        audit.log("persona.viewed", actor=request.user, target=persona, request=request)
        return Response(PersonaDetailSerializer(persona).data)

    def partial_update(self, request, *args, **kwargs):
        persona = self.get_object()
        serializer = PersonaDetailSerializer(persona, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cambiados = sorted(serializer.validated_data.keys())
        if "datos_extra" in serializer.validated_data:
            try:
                serializer.validated_data["datos_extra"] = formularios.aplicar(
                    "persona", persona.datos_extra, serializer.validated_data["datos_extra"]
                )
            except DjangoValidationError as exc:
                return _error("invalid", _validation_detail(exc))
        serializer.save()
        audit.log(
            "persona.updated", actor=request.user, target=persona, request=request, campos=cambiados
        )
        return Response(PersonaDetailSerializer(persona).data)

    @action(detail=True, methods=["post"])
    def nivel(self, request, pk=None):
        persona = self.get_object()
        data = NivelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            services.cambiar_nivel(
                persona, data.validated_data["nivel"], actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid_level", _validation_detail(exc))
        return Response(PersonaDetailSerializer(persona).data)

    @action(detail=True, methods=["post"])
    def baja(self, request, pk=None):
        persona = self.get_object()
        if not jerarquia.puede_dar_baja(request.user, persona):
            return _sin_jerarquia()
        data = BajaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            services.registrar_baja(
                persona, actor=request.user, request=request, **data.validated_data
            )
        except DjangoValidationError as exc:
            return _error("invalid_baja", _validation_detail(exc))
        return Response(PersonaDetailSerializer(persona).data)

    @action(detail=True, methods=["post"])
    def traslado(self, request, pk=None):
        persona = self.get_object()
        if not jerarquia.puede_dar_baja(request.user, persona):
            return _sin_jerarquia()
        data = TrasladoSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            services.trasladar(persona, actor=request.user, request=request, **data.validated_data)
        except DjangoValidationError as exc:
            return _error("invalid_traslado", _validation_detail(exc))
        return Response(PersonaDetailSerializer(persona).data)

    @action(detail=True, methods=["post"])
    def reactivar(self, request, pk=None):
        persona = self.get_object()
        if not jerarquia.puede_dar_baja(request.user, persona):
            return _sin_jerarquia()
        try:
            services.reactivar(
                persona,
                motivo=str(request.data.get("motivo", ""))[:300],
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            return _error("invalid_reactivation", _validation_detail(exc))
        return Response(PersonaDetailSerializer(persona).data)

    @action(detail=True, methods=["get"])
    def movimientos(self, request, pk=None):
        persona = self.get_object()
        return Response(MovimientoSerializer(persona.movimientos.all(), many=True).data)

    @action(detail=True, methods=["post"], url_path="procesos")
    def procesos(self, request, pk=None):
        """Guarda el avance en los procesos discipulares (lista completa o parcial)."""
        persona = self.get_object()
        data = ProcesoPersonaSerializer(data=request.data, many=True)
        data.is_valid(raise_exception=True)
        services.actualizar_procesos(
            persona, data.validated_data, actor=request.user, request=request
        )
        return Response(PersonaDetailSerializer(persona).data)

    @action(detail=True, methods=["get", "post"], url_path="foto")
    def foto(self, request, pk=None):
        persona = self.get_object()
        if request.method == "POST":
            data = FotoSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            try:
                services.guardar_foto(
                    persona, data.validated_data["foto"], actor=request.user, request=request
                )
            except DjangoValidationError as exc:
                return _error("invalid_photo", _validation_detail(exc))
            return Response(PersonaDetailSerializer(persona).data)
        if not persona.foto:
            raise Http404
        try:
            respuesta = FileResponse(persona.foto.open("rb"), content_type="image/jpeg")
        except FileNotFoundError as exc:
            raise Http404 from exc
        respuesta["Cache-Control"] = "private, max-age=300"
        return respuesta
