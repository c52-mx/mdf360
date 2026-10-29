from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import audit

from . import access, services
from .models import Unidad, UnidadMiembro


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


def _denegado():
    return _error("forbidden", "No tienes permiso para esta acción.", status.HTTP_403_FORBIDDEN)


def unidad_resumen(unidad: Unidad, user) -> dict:
    miembros = unidad.miembros.filter(activo=True)
    return {
        "id": unidad.pk,
        "nombre": unidad.nombre,
        "descripcion": unidad.descripcion,
        "activa": unidad.activa,
        "encargados": [
            m.persona.nombre_completo
            for m in miembros.filter(rol="encargado").select_related("persona")
        ],
        "integrantes": miembros.values("persona_id").distinct().count(),
        "mis_roles": sorted(access.roles_en(user, unidad)),
    }


def miembro_dict(m: UnidadMiembro) -> dict:
    return {
        "id": m.pk,
        "persona_id": m.persona_id,
        "nombre": m.persona.nombre_completo,
        "rol": m.rol,
        "rol_display": m.get_rol_display(),
    }


class UnidadEscritura(serializers.Serializer):
    nombre = serializers.CharField(max_length=120)
    descripcion = serializers.CharField(max_length=300, required=False, allow_blank=True)
    activa = serializers.BooleanField(required=False)


class UnidadesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unidades = access.unidades_visibles(request.user)
        if not request.query_params.get("todas"):
            unidades = unidades.filter(activa=True)
        return Response([unidad_resumen(u, request.user) for u in unidades])

    def post(self, request):
        if not access.puede_administrar(request.user):
            return _denegado()
        data = UnidadEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        if Unidad.objects.filter(nombre__iexact=data.validated_data["nombre"].strip()).exists():
            return _error("duplicate", "Ya existe una unidad con ese nombre.")
        unidad = Unidad.objects.create(**data.validated_data)
        audit.log("unidad.creada", actor=request.user, target=unidad, request=request)
        return Response(unidad_resumen(unidad, request.user), status=status.HTTP_201_CREATED)


class UnidadView(APIView):
    permission_classes = [IsAuthenticated]

    def _unidad(self, request, pk):
        unidad = get_object_or_404(Unidad, pk=pk)
        if not access.puede_ver(request.user, unidad):
            raise Http404
        return unidad

    def get(self, request, pk):
        unidad = self._unidad(request, pk)
        miembros = unidad.miembros.filter(activo=True).select_related("persona")
        return Response(
            {
                **unidad_resumen(unidad, request.user),
                "miembros": [miembro_dict(m) for m in miembros],
                "puede_gestionar": access.puede_gestionar_integrantes(request.user, unidad),
                "puede_administrar": access.puede_administrar(request.user),
            }
        )

    def patch(self, request, pk):
        unidad = self._unidad(request, pk)
        if not access.puede_administrar(request.user):
            return _denegado()
        data = UnidadEscritura(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        nombre = data.validated_data.get("nombre", "").strip()
        if nombre and Unidad.objects.filter(nombre__iexact=nombre).exclude(pk=unidad.pk).exists():
            return _error("duplicate", "Ya existe una unidad con ese nombre.")
        for campo, valor in data.validated_data.items():
            setattr(unidad, campo, valor)
        unidad.save()
        audit.log(
            "unidad.actualizada", actor=request.user, target=unidad, request=request,
            campos=sorted(data.validated_data),
        )  # fmt: skip
        return Response(unidad_resumen(unidad, request.user))


class IntegranteEscritura(serializers.Serializer):
    whatsapp = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    rol = serializers.ChoiceField(choices=UnidadMiembro.Rol.choices, default="servidor")
    acepta_datos = serializers.BooleanField(default=False)


class CambioRol(serializers.Serializer):
    rol = serializers.ChoiceField(choices=UnidadMiembro.Rol.choices)


def _reservado_sin_permiso(user, *roles) -> bool:
    """Encargado y respaldo los asigna solo la administración de unidades."""
    return any(r in services.RESERVADOS for r in roles) and not access.puede_administrar(user)


class IntegrantesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        unidad = get_object_or_404(Unidad, pk=pk, activa=True)
        if not access.puede_ver(request.user, unidad):
            raise Http404
        if not access.puede_gestionar_integrantes(request.user, unidad):
            return _denegado()
        data = IntegranteEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        if _reservado_sin_permiso(request.user, v["rol"]):
            return _error(
                "role_not_allowed",
                "Solo la administración asigna encargado o respaldo.",
                status.HTTP_403_FORBIDDEN,
            )
        try:
            miembro = services.agregar_integrante(unidad, actor=request.user, request=request, **v)
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        except Exception as exc:
            from apps.personas.services import ConsentimientoRequerido

            if isinstance(exc, ConsentimientoRequerido):
                return _error("consent_required", "La persona debe aceptar el aviso de privacidad.")
            raise
        return Response(miembro_dict(miembro), status=status.HTTP_201_CREATED)


class IntegranteView(APIView):
    permission_classes = [IsAuthenticated]

    def _miembro(self, request, pk, miembro_id, activo=True):
        unidad = get_object_or_404(Unidad, pk=pk)
        if not access.puede_ver(request.user, unidad):
            raise Http404
        miembro = get_object_or_404(UnidadMiembro, pk=miembro_id, unidad=unidad, activo=activo)
        return unidad, miembro

    def patch(self, request, pk, miembro_id):
        unidad, miembro = self._miembro(request, pk, miembro_id)
        if not access.puede_gestionar_integrantes(request.user, unidad):
            return _denegado()
        data = CambioRol(data=request.data)
        data.is_valid(raise_exception=True)
        nuevo = data.validated_data["rol"]
        if _reservado_sin_permiso(request.user, miembro.rol, nuevo):
            return _denegado()
        if (
            UnidadMiembro.objects.filter(unidad=unidad, persona=miembro.persona, rol=nuevo)
            .exclude(pk=miembro.pk)
            .exists()
        ):
            return _error("invalid", "Esa persona ya tiene ese rol en la unidad.")
        anterior, miembro.rol = miembro.rol, nuevo
        miembro.save(update_fields=["rol"])
        audit.log(
            "unidad.integrante_rol", actor=request.user, target=unidad, request=request,
            persona=miembro.persona_id, de=anterior, a=nuevo,
        )  # fmt: skip
        return Response(miembro_dict(miembro))

    def delete(self, request, pk, miembro_id):
        unidad, miembro = self._miembro(request, pk, miembro_id)
        if not access.puede_gestionar_integrantes(request.user, unidad):
            return _denegado()
        if _reservado_sin_permiso(request.user, miembro.rol):
            return _denegado()
        miembro.activo = False
        miembro.save(update_fields=["activo"])
        audit.log(
            "unidad.integrante_quitado", actor=request.user, target=unidad, request=request,
            persona=miembro.persona_id, rol=miembro.rol,
        )  # fmt: skip
        return Response(status=status.HTTP_204_NO_CONTENT)


class IntegranteRestaurarView(IntegranteView):
    """Deshace «quitar»: el integrante vuelve con el mismo rol."""

    http_method_names = ["post", "options"]

    def post(self, request, pk, miembro_id):
        unidad, miembro = self._miembro(request, pk, miembro_id, activo=False)
        if not access.puede_gestionar_integrantes(request.user, unidad):
            return _denegado()
        if _reservado_sin_permiso(request.user, miembro.rol):
            return _denegado()
        miembro.activo = True
        miembro.save(update_fields=["activo"])
        audit.log(
            "unidad.integrante_restaurado", actor=request.user, target=unidad, request=request,
            persona=miembro.persona_id, rol=miembro.rol,
        )  # fmt: skip
        return Response(miembro_dict(miembro))
