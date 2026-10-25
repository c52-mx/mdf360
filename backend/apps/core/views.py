from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Comprobación de vida para el balanceador y el monitoreo."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return Response({"status": "ok"})


class AuditPagination(PageNumberPagination):
    page_size = 50
    max_page_size = 200
    page_size_query_param = "page_size"


class AuditListView(APIView):
    """Consulta de la bitácora (permiso bitacora.ver). Consultarla también queda registrada."""

    def get_permissions(self):
        from apps.accounts.permissions import requiere

        return [requiere("bitacora.ver")()]

    def get(self, request):
        from django.db.models import Q

        from . import audit
        from .models import AuditEvent

        qs = AuditEvent.objects.all()
        p = request.query_params
        if p.get("action"):
            qs = qs.filter(action__startswith=p["action"])
        if p.get("q"):
            qs = qs.filter(Q(actor_repr__icontains=p["q"]) | Q(target_id=p["q"]))
        if p.get("desde"):
            qs = qs.filter(created_at__date__gte=p["desde"])
        if p.get("hasta"):
            qs = qs.filter(created_at__date__lte=p["hasta"])
        paginator = AuditPagination()
        page = paginator.paginate_queryset(qs, request)
        audit.log("bitacora.viewed", actor=request.user, request=request)
        filas = [
            {
                "id": e.id,
                "fecha": e.created_at,
                "accion": e.action,
                "actor": e.actor_repr,
                "objeto": f"{e.target_type} {e.target_id}".strip(),
                "detalle": e.detail,
                "ip": e.ip,
            }
            for e in page
        ]
        return paginator.get_paginated_response(filas)


class ConfigView(APIView):
    """Lista de parámetros configurables con su valor vigente (permiso config.gestionar)."""

    def get_permissions(self):
        from apps.accounts.permissions import requiere

        return [requiere("config.gestionar")()]

    def get(self, request):
        from . import config

        return Response(
            [
                {
                    "clave": clave,
                    "descripcion": d["descripcion"],
                    "tipo": d["tipo"],
                    "valor": config.obtener(clave),
                    "por_defecto": d["default"],
                }
                for clave, d in config.DEFINICIONES.items()
            ]
        )


class ConfigItemView(APIView):
    def get_permissions(self):
        from apps.accounts.permissions import requiere

        return [requiere("config.gestionar")()]

    def patch(self, request, clave):
        from django.core.exceptions import ValidationError

        from . import audit, config
        from .models import Configuracion

        if clave not in config.DEFINICIONES:
            from django.http import Http404

            raise Http404
        try:
            valor = config.validar(clave, request.data.get("valor"))
        except ValidationError as exc:
            return Response({"code": "invalid", "detail": " ".join(exc.messages)}, status=400)
        anterior = config.obtener(clave)
        Configuracion.objects.update_or_create(
            clave=clave, defaults={"valor": valor, "actualizado_por": request.user}
        )
        audit.log(
            "config.cambiada", actor=request.user, request=request,
            clave=clave, anterior=anterior, nuevo=valor,
        )  # fmt: skip
        return Response({"clave": clave, "valor": valor})
