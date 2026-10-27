from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import ACCIONES_AVISO, ACCIONES_ERROR, nivel_de


class HealthView(APIView):
    """Comprobación de vida para el balanceador y el monitoreo."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return Response({"status": "ok"})


_ACCIONES_POR_NIVEL = {"error": ACCIONES_ERROR, "aviso": ACCIONES_AVISO}


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
        if p.get("nivel") in ("error", "aviso"):
            qs = qs.filter(action__in=_ACCIONES_POR_NIVEL[p["nivel"]])
        elif p.get("nivel") == "info":
            qs = qs.exclude(action__in=ACCIONES_ERROR | ACCIONES_AVISO)
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
                "nivel": nivel_de(e.action),
                "actor": e.actor_repr,
                "objeto": f"{e.target_type} {e.target_id}".strip(),
                "detalle": e.detail,
                "ip": e.ip,
            }
            for e in page
        ]
        return paginator.get_paginated_response(filas)


class AuditResumenView(APIView):
    """Errores y avisos por día, y los módulos que hay en la bitácora (para filtrar)."""

    def get_permissions(self):
        from apps.accounts.permissions import requiere

        return [requiere("bitacora.ver")()]

    def get(self, request):
        from datetime import timedelta

        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from django.utils import timezone

        from .models import AuditEvent

        try:
            dias = min(max(int(request.query_params.get("dias", 14)), 1), 90)
        except ValueError:
            dias = 14
        hoy = timezone.localdate()
        desde = hoy - timedelta(days=dias - 1)
        filas = (
            AuditEvent.objects.filter(
                created_at__date__gte=desde,
                action__in=ACCIONES_ERROR | ACCIONES_AVISO,
            )
            .annotate(dia=TruncDate("created_at", tzinfo=timezone.get_current_timezone()))
            .values("dia", "action")
            .annotate(n=Count("id"))
        )
        por_dia = {desde + timedelta(days=i): {"errores": 0, "avisos": 0} for i in range(dias)}
        for f in filas:
            clave = "errores" if f["action"] in ACCIONES_ERROR else "avisos"
            if f["dia"] in por_dia:
                por_dia[f["dia"]][clave] += f["n"]
        acciones = AuditEvent.objects.values_list("action", flat=True).distinct()
        modulos = sorted({a.split(".")[0] for a in acciones})
        return Response(
            {
                "dias": [{"fecha": d.isoformat(), **v} for d, v in por_dia.items()],
                "modulos": modulos,
            }
        )


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
                    "opciones": d.get("opciones"),
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
