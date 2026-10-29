import re
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts import equipos
from apps.accounts.permissions import requiere
from apps.core import audit
from apps.formularios import services as formularios

from . import access, services
from . import ofrendas as ofr
from .models import (
    Asistencia,
    EstudioSemanal,
    Grupo,
    GrupoMiembro,
    Ofrenda,
    Reunion,
    SolicitudIngreso,
)

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST, **extra):
    return Response({"code": code, "detail": detail, **extra}, status=http_status)


def _denegado():
    return _error("forbidden", "No tienes permiso para esta acción.", status.HTTP_403_FORBIDDEN)


def _detalle(exc: DjangoValidationError) -> str:
    return " ".join(exc.messages)


# ---------- serialización manual (listas cortas, sin sobrecarga) ----------
def grupo_resumen(grupo: Grupo, user) -> dict:
    miembros = grupo.miembros.filter(activo=True)
    lideres = [
        m.persona.nombre_completo for m in miembros.filter(rol="lider").select_related("persona")
    ]
    return {
        "id": grupo.pk,
        "nombre": grupo.nombre,
        "tipo": grupo.tipo,
        "sector": grupo.sector,
        "casa": grupo.casa,
        "ubicacion": grupo.ubicacion,
        "suspendido": grupo.suspendido,
        "suspension_motivo": grupo.suspension_motivo,
        "suspendido_en": grupo.suspendido_en.isoformat() if grupo.suspendido_en else None,
        "colonia": grupo.colonia,
        "dia_semana": grupo.dia_semana,
        "dia": DIAS[grupo.dia_semana] if grupo.dia_semana is not None else "",
        "hora": grupo.hora.strftime("%H:%M") if grupo.hora else "",
        "activo": grupo.activo,
        "lideres": lideres,
        "integrantes": miembros.values("persona_id").distinct().count(),
        "mis_roles": sorted(access.roles_en(user, grupo)),
        "ofrendas_con_diferencia": ofr.diferencias_visibles(user, grupo),
    }


def miembro_dict(m: GrupoMiembro, nombres: dict | None = None) -> dict:
    nombres = nombres if nombres is not None else equipos.nombres("grupo")
    return {
        "id": m.pk,
        "persona_id": m.persona_id,
        "nombre": m.persona.nombre_completo,
        "rol": m.rol,
        "rol_display": nombres.get(m.rol, m.rol),
        "invitado": m.persona.procedencia == "invitado_grupo",
    }


def estudio_dict(e: EstudioSemanal | None) -> dict | None:
    if e is None:
        return None
    base = f"/api/grupos/estudios/{e.pk}/archivo"
    return {
        "id": e.pk,
        "semana": e.semana.isoformat(),
        "titulo": e.titulo,
        "pdf_adultos": f"{base}/pdf_adultos/" if e.pdf_adultos else None,
        "pdf_ninos": f"{base}/pdf_ninos/" if e.pdf_ninos else None,
        "audio": f"{base}/audio/" if e.audio else None,
    }


class GrupoEscritura(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    tipo = serializers.ChoiceField(choices=Grupo.Tipo.choices, default="conexion")
    sector = serializers.RegexField(
        r"^[A-Za-z]?$",
        required=False,
        allow_blank=True,
        error_messages={"invalid": "El sector es una sola letra, por ejemplo K."},
    )
    casa = serializers.IntegerField(min_value=1, max_value=9999, required=False, allow_null=True)

    def validate_sector(self, valor: str) -> str:
        return valor.upper()

    datos_extra = serializers.DictField(required=False)
    colonia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    dia_semana = serializers.IntegerField(min_value=0, max_value=6, required=False, allow_null=True)
    hora = serializers.TimeField(required=False, allow_null=True)
    activo = serializers.BooleanField(required=False)


def _reuniones_del_grupo(user, grupo: Grupo) -> list[dict]:
    """Últimas reuniones con lo que ocurrió ese día: asistencia, observaciones, ofrendas (solo
    si puede ver finanzas) y peticiones (solo las que puede leer)."""
    from apps.peticiones import services as peticiones

    from .ofrendas import puede_ver_finanzas_grupo

    reuniones = list(grupo.reuniones.all()[:20])
    ids = [r.pk for r in reuniones]
    asistencia = {
        f["reunion_id"]: f
        for f in Asistencia.objects.filter(reunion_id__in=ids)
        .values("reunion_id")
        .annotate(registrados=Count("id"), presentes=Count("id", filter=Q(presente=True)))
    }
    peticiones_por_dia = {
        f["referencia_id"]: f["n"]
        for f in peticiones.peticiones_visibles(user)
        .filter(origen_tipo="grupo", origen_id=grupo.pk, referencia_id__in=ids)
        .values("referencia_id")
        .annotate(n=Count("id"))
    }
    ve_finanzas = puede_ver_finanzas_grupo(user, grupo)
    ofrendas_por_dia = {}
    if ve_finanzas:
        ofrendas_por_dia = {
            f["reunion_id"]: f
            for f in Ofrenda.objects.filter(reunion_id__in=ids)
            .values("reunion_id")
            .annotate(n=Count("id"), total=Sum("monto"))
        }
    filas = []
    for r in reuniones:
        a = asistencia.get(r.pk, {})
        fila = {
            "id": r.pk,
            "fecha": r.fecha.isoformat(),
            "presentes": a.get("presentes", 0),
            "registrados": a.get("registrados", 0),
            "notas": r.notas,
            "peticiones": peticiones_por_dia.get(r.pk, 0),
            "ofrendas": None,
        }
        if ve_finanzas:
            o = ofrendas_por_dia.get(r.pk)
            fila["ofrendas"] = (
                {"cantidad": o["n"], "total": str(o["total"])}
                if o
                else {
                    "cantidad": 0,
                    "total": "0",
                }
            )
        filas.append(fila)
    return filas


# ---------- grupos ----------
class GruposView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        p = request.query_params
        grupos = access.grupos_visibles(request.user).filter(activo=True)
        if p.get("estado") == "activos":
            grupos = grupos.filter(suspendido=False)
        elif p.get("estado") == "suspendidos":
            grupos = grupos.filter(suspendido=True)
        if p.get("dia", "").isdigit():
            grupos = grupos.filter(dia_semana=int(p["dia"]))
        if p.get("sector"):
            grupos = grupos.filter(sector__iexact=p["sector"].strip())
        lider = (p.get("lider") or "").strip()
        if lider:
            grupos = grupos.filter(
                miembros__activo=True,
                miembros__rol="lider",
                miembros__persona__nombre__unaccent__icontains=lider,
            ).distinct()
        q = (p.get("q") or "").strip()
        if q:
            grupos = grupos.filter(
                Q(nombre__unaccent__icontains=q) | Q(colonia__unaccent__icontains=q)
            )
        return Response([grupo_resumen(g, request.user) for g in grupos])

    def post(self, request):
        if not access.puede_administrar(request.user):
            return _denegado()
        data = GrupoEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        datos = dict(data.validated_data)
        try:
            datos["datos_extra"] = formularios.aplicar("grupo", {}, datos.pop("datos_extra", {}))
        except DjangoValidationError as exc:
            return _error("invalid", _detalle(exc))
        grupo = Grupo.objects.create(**datos)
        audit.log("grupo.creado", actor=request.user, target=grupo, request=request)
        return Response(grupo_resumen(grupo, request.user), status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    """Reporte de supervisión de los grupos que la persona puede consultar (M3-07)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from . import dashboard

        return Response(dashboard.construir(request.user))


class GrupoView(APIView):
    permission_classes = [IsAuthenticated]

    def _grupo(self, request, pk):
        grupo = get_object_or_404(Grupo, pk=pk)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        return grupo

    def get(self, request, pk):
        grupo = self._grupo(request, pk)
        miembros = grupo.miembros.filter(activo=True).select_related("persona")
        reuniones = []
        if access.puede_ver_historial(request.user, grupo):
            reuniones = _reuniones_del_grupo(request.user, grupo)
        else:  # el Secretario solo llega a la reunión de hoy
            hoy = grupo.reuniones.filter(fecha=timezone.localdate()).first()
            if hoy:
                reuniones.append({"id": hoy.pk, "fecha": hoy.fecha.isoformat()})
        return Response(
            {
                **grupo_resumen(grupo, request.user),
                "datos_extra": grupo.datos_extra,
                "datos_extra_etiquetas": formularios.etiquetas("grupo", grupo.datos_extra),
                "miembros": [miembro_dict(m, equipos.nombres("grupo")) for m in miembros],
                "reuniones": reuniones,
                "puede_capturar": access.puede_capturar(request.user, grupo),
                "puede_gestionar": access.puede_gestionar_integrantes(request.user, grupo),
                "puede_administrar": access.puede_administrar(request.user),
                "enlace": (
                    f"/unirse/{grupo.enlace_token}"
                    if grupo.enlace_token
                    and access.puede_gestionar_integrantes(request.user, grupo)
                    else None
                ),
            }
        )

    def patch(self, request, pk):
        grupo = self._grupo(request, pk)
        if not access.puede_administrar(request.user):
            return _denegado()
        data = GrupoEscritura(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        cambios = dict(data.validated_data)
        if "datos_extra" in cambios:
            try:
                cambios["datos_extra"] = formularios.aplicar(
                    "grupo", grupo.datos_extra, cambios["datos_extra"]
                )
            except DjangoValidationError as exc:
                return _error("invalid", _detalle(exc))
        for campo, valor in cambios.items():
            setattr(grupo, campo, valor)
        grupo.save()
        audit.log(
            "grupo.actualizado", actor=request.user, target=grupo, request=request,
            campos=sorted(data.validated_data),
        )  # fmt: skip
        return Response(grupo_resumen(grupo, request.user))


# ---------- ingreso por enlace o QR ----------
class IngresoThrottle(AnonRateThrottle):
    scope = "unirse"


def _grupo_por_enlace(token: str):
    return Grupo.objects.filter(enlace_token=token, activo=True, suspendido=False).first()


class EnlaceGrupoView(APIView):
    """Quien lidera el grupo genera, regenera o desactiva el enlace (y su QR)."""

    permission_classes = [IsAuthenticated]

    def _grupo(self, request, pk):
        grupo = get_object_or_404(Grupo, pk=pk, activo=True)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        return grupo

    def post(self, request, pk):
        grupo = self._grupo(request, pk)
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        if grupo.suspendido:
            return _error("suspended", "El grupo está suspendido.")
        token = services.generar_enlace(grupo, actor=request.user, request=request)
        return Response({"enlace": f"/unirse/{token}"}, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        grupo = self._grupo(request, pk)
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        services.desactivar_enlace(grupo, actor=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnlacePublicoView(APIView):
    """Lo que ve quien abre el enlace: solo el nombre y el horario del grupo."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [IngresoThrottle]

    def get(self, request, token):
        grupo = _grupo_por_enlace(token)
        if grupo is None:
            return _error("invalid_link", "Este enlace ya no es válido.", status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "grupo": grupo.nombre,
                "dia": DIAS[grupo.dia_semana] if grupo.dia_semana is not None else "",
                "hora": grupo.hora.strftime("%H:%M") if grupo.hora else "",
            }
        )


class SolicitudEscritura(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    whatsapp = serializers.CharField(max_length=40)
    acepta_datos = serializers.BooleanField()


class SolicitarIngresoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [IngresoThrottle]

    def post(self, request, token):
        grupo = _grupo_por_enlace(token)
        if grupo is None:
            return _error("invalid_link", "Este enlace ya no es válido.", status.HTTP_404_NOT_FOUND)
        data = SolicitudEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            solicitud = services.solicitar_ingreso(grupo, request=request, **data.validated_data)
        except DjangoValidationError as exc:
            return _error("invalid", _detalle(exc))
        return Response(
            {"codigo": solicitud.codigo, "estado": solicitud.estado, "grupo": grupo.nombre},
            status=status.HTTP_201_CREATED,
        )


class SalaDeEsperaView(APIView):
    """La persona consulta, con su código secreto, si ya la aprobaron."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [IngresoThrottle]

    def get(self, request, codigo):
        solicitud = get_object_or_404(
            SolicitudIngreso.objects.select_related("grupo"), codigo=codigo
        )
        return Response({"estado": solicitud.estado, "grupo": solicitud.grupo.nombre})


def solicitud_dict(s: SolicitudIngreso) -> dict:
    from urllib.parse import quote

    texto = (
        f"Hola {s.nombre.split()[0]}, ya eres parte de {s.grupo.nombre}. "
        "¡Te esperamos en la próxima reunión!"
    )
    return {
        "id": s.pk,
        "nombre": s.nombre,
        "whatsapp": s.whatsapp,
        "creada_en": s.creada_en,
        "estado": s.estado,
        "whatsapp_url": f"https://wa.me/{s.whatsapp.lstrip('+')}?text={quote(texto)}",
    }


class SolicitudesGrupoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        grupo = get_object_or_404(Grupo, pk=pk, activo=True)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        pendientes = grupo.solicitudes.filter(estado="pendiente").select_related("grupo")
        return Response([solicitud_dict(s) for s in pendientes])


class ResolverSolicitudView(APIView):
    permission_classes = [IsAuthenticated]
    aprobar = True

    def post(self, request, sid):
        solicitud = get_object_or_404(SolicitudIngreso.objects.select_related("grupo"), pk=sid)
        grupo = solicitud.grupo
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        try:
            solicitud = services.resolver_solicitud(
                solicitud, aprobar=self.aprobar, actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid", _detalle(exc))
        return Response(solicitud_dict(solicitud))


class AprobarSolicitudView(ResolverSolicitudView):
    aprobar = True


class RechazarSolicitudView(ResolverSolicitudView):
    aprobar = False


class SuspensionSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=1000)


class GrupoSuspenderView(APIView):
    """Suspende un grupo (deja de contar en el dashboard y no abre reuniones) con su motivo."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        grupo = get_object_or_404(Grupo, pk=pk, activo=True)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        if not access.puede_administrar(request.user):
            return _denegado()
        data = SuspensionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        motivo = data.validated_data["motivo"].strip()
        if not motivo:
            return _error("invalid", "Escribe el motivo de la suspensión.")
        grupo.suspendido = True
        grupo.suspension_motivo = motivo
        grupo.suspendido_en = timezone.localdate()
        grupo.save(update_fields=["suspendido", "suspension_motivo", "suspendido_en"])
        audit.log(
            "grupo.suspendido", actor=request.user, target=grupo, request=request, motivo=motivo
        )
        return Response(grupo_resumen(grupo, request.user))


class GrupoReactivarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        grupo = get_object_or_404(Grupo, pk=pk, activo=True)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        if not access.puede_administrar(request.user):
            return _denegado()
        grupo.suspendido = False
        grupo.save(update_fields=["suspendido"])  # el motivo y la fecha quedan como historial
        audit.log("grupo.reactivado", actor=request.user, target=grupo, request=request)
        return Response(grupo_resumen(grupo, request.user))


# ---------- integrantes ----------
class IntegranteSerializer(serializers.Serializer):
    whatsapp = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    rol = equipos.campo_rol("grupo", default="asistente")
    acepta_datos = serializers.BooleanField(default=False)


class IntegrantesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        grupo = get_object_or_404(Grupo, pk=pk)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        data = IntegranteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        if equipos.es_de_gestion("grupo", v["rol"]) and not access.puede_administrar(request.user):
            return _error(
                "role_not_allowed",
                "Solo la administración asigna Supervisor o Líder.",
                status.HTTP_403_FORBIDDEN,
            )
        try:
            miembro = services.agregar_integrante(
                grupo,
                rol=v["rol"],
                whatsapp=v["whatsapp"],
                nombre=v["nombre"],
                acepta_datos=v["acepta_datos"],
                actor=request.user,
                request=request,
            )
        except DjangoValidationError as exc:
            return _error("invalid", _detalle(exc))
        except Exception as exc:  # consentimiento requerido, etc.
            from apps.personas.services import ConsentimientoRequerido

            if isinstance(exc, ConsentimientoRequerido):
                return _error("consent_required", "La persona debe aceptar el aviso de privacidad.")
            raise
        return Response(miembro_dict(miembro), status=status.HTTP_201_CREATED)


class CambioRolSerializer(serializers.Serializer):
    rol = equipos.campo_rol("grupo")


class IntegranteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, miembro_id):
        """Cambia el rol de un integrante dentro del grupo."""
        grupo = get_object_or_404(Grupo, pk=pk)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        miembro = get_object_or_404(GrupoMiembro, pk=miembro_id, grupo=grupo, activo=True)
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        data = CambioRolSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        nuevo = data.validated_data["rol"]
        if (
            equipos.es_de_gestion("grupo", miembro.rol) or equipos.es_de_gestion("grupo", nuevo)
        ) and not access.puede_administrar(request.user):
            return _error(
                "role_not_allowed",
                "Solo la administración asigna o cambia Supervisor o Líder.",
                status.HTTP_403_FORBIDDEN,
            )
        if (
            GrupoMiembro.objects.filter(grupo=grupo, persona=miembro.persona, rol=nuevo)
            .exclude(pk=miembro.pk)
            .exists()
        ):
            return _error("invalid", "Esa persona ya tiene ese rol en el grupo.")
        anterior = miembro.rol
        miembro.rol = nuevo
        miembro.save(update_fields=["rol"])
        audit.log(
            "grupo.integrante_rol", actor=request.user, target=grupo, request=request,
            persona=miembro.persona_id, de=anterior, a=nuevo,
        )  # fmt: skip
        return Response(miembro_dict(miembro))

    def delete(self, request, pk, miembro_id):
        grupo = get_object_or_404(Grupo, pk=pk)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        miembro = get_object_or_404(GrupoMiembro, pk=miembro_id, grupo=grupo)
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        if equipos.es_de_gestion("grupo", miembro.rol) and not access.puede_administrar(
            request.user
        ):
            return _denegado()
        miembro.activo = False
        miembro.save(update_fields=["activo"])
        audit.log(
            "grupo.integrante_quitado", actor=request.user, target=grupo, request=request,
            persona=miembro.persona_id, rol=miembro.rol,
        )  # fmt: skip
        return Response(status=status.HTTP_204_NO_CONTENT)


class IntegranteRestaurarView(APIView):
    """Deshace «quitar»: el integrante vuelve al grupo con el mismo rol."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk, miembro_id):
        grupo = get_object_or_404(Grupo, pk=pk)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        miembro = get_object_or_404(GrupoMiembro, pk=miembro_id, grupo=grupo, activo=False)
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        if equipos.es_de_gestion("grupo", miembro.rol) and not access.puede_administrar(
            request.user
        ):
            return _denegado()
        miembro.activo = True
        miembro.save(update_fields=["activo"])
        audit.log(
            "grupo.integrante_restaurado", actor=request.user, target=grupo, request=request,
            persona=miembro.persona_id, rol=miembro.rol,
        )  # fmt: skip
        return Response(miembro_dict(miembro))


# ---------- reuniones y asistencia ----------
class AbrirReunionSerializer(serializers.Serializer):
    fecha = serializers.DateField(required=False)
    capturado_en = serializers.DateTimeField(required=False)


def _momento(datos):
    """Valida el momento de captura sin conexión; devuelve (momento, respuesta_de_error)."""
    try:
        return access.momento_captura(datos.get("capturado_en")), None
    except access.CapturaInvalida as exc:
        return None, _error("too_old", str(exc))


class ReunionesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        grupo = get_object_or_404(Grupo, pk=pk)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        if not access.puede_capturar(request.user, grupo):
            return _denegado()
        if grupo.suspendido:
            return _error("suspended", "El grupo está suspendido: no se abren reuniones.")
        data = AbrirReunionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        fecha = data.validated_data.get("fecha")
        momento, error = _momento(data.validated_data)
        if error:
            return error
        dia = access.dia_efectivo(momento)
        # El Secretario solo abre la reunión del día en que captura (sin conexión, el día real)
        if fecha and fecha != dia and not access.puede_ver_historial(request.user, grupo):
            return _denegado()
        reunion = services.abrir_reunion(grupo, fecha or dia, actor=request.user, request=request)
        return Response({"id": reunion.pk, "fecha": reunion.fecha.isoformat()}, status=201)


class AsistenciaItem(serializers.Serializer):
    persona_id = serializers.IntegerField()
    presente = serializers.BooleanField()


class AsistenciaSerializer(serializers.Serializer):
    asistencias = AsistenciaItem(many=True)
    notas = serializers.CharField(required=False, allow_blank=True)
    capturado_en = serializers.DateTimeField(required=False)


class ReunionView(APIView):
    permission_classes = [IsAuthenticated]

    def _reunion(self, request, rid, dia=None):
        reunion = get_object_or_404(Reunion.objects.select_related("grupo"), pk=rid)
        if not access.puede_ver_reunion(request.user, reunion, dia):
            raise Http404
        return reunion

    def get(self, request, rid):
        reunion = self._reunion(request, rid)
        if request.user and access.puede_ver_historial(request.user, reunion.grupo):
            audit.log("asistencia.consultada", actor=request.user, target=reunion, request=request)
        return Response(
            {
                "id": reunion.pk,
                "fecha": reunion.fecha.isoformat(),
                "notas": reunion.notas,
                "grupo": {"id": reunion.grupo_id, "nombre": reunion.grupo.nombre},
                "personas": services.personas_con_asistencia(reunion),
                "estudio": estudio_dict(services.estudio_de(reunion.fecha)),
                "puede_modificar": access.puede_modificar_asistencia(request.user, reunion),
            }
        )

    def put(self, request, rid):
        data = AsistenciaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        momento, error = _momento(data.validated_data)
        if error:
            return error
        dia = access.dia_efectivo(momento)
        reunion = self._reunion(request, rid, dia)
        if not access.puede_modificar_asistencia(request.user, reunion, dia):
            return _denegado()
        try:
            presentes, omitidos = services.guardar_asistencia(
                reunion,
                data.validated_data["asistencias"],
                actor=request.user,
                request=request,
                capturado_en=momento,
            )
        except DjangoValidationError as exc:
            return _error("invalid", _detalle(exc))
        if "notas" in data.validated_data and (momento is None or not reunion.notas):
            reunion.notas = data.validated_data["notas"]
            reunion.save(update_fields=["notas"])
        return Response({"presentes": presentes, "omitidos": omitidos})


# ---------- estudio semanal ----------
class EstudiosView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        if not access.puede_ver_estudios(request.user):
            return _denegado()
        return Response([estudio_dict(e) for e in EstudioSemanal.objects.all()[:12]])

    def post(self, request):
        from rest_framework.permissions import BasePermission  # noqa: F401

        if not requiere("grupos.material")().has_permission(request, self):
            return _denegado()
        titulo = (request.data.get("titulo") or "").strip()
        semana = request.data.get("semana")
        if not titulo:
            return _error("invalid", "Escribe el título del estudio.")
        try:
            semana = date.fromisoformat(semana)
        except (TypeError, ValueError):
            return _error("invalid", "La semana no es una fecha válida.")
        archivos = {
            campo: request.FILES[campo]
            for campo in ("pdf_adultos", "pdf_ninos", "audio")
            if campo in request.FILES
        }
        try:
            estudio = services.guardar_estudio(
                semana=semana, titulo=titulo, archivos=archivos, actor=request.user, request=request
            )
        except DjangoValidationError as exc:
            return _error("invalid", _detalle(exc))
        return Response(estudio_dict(estudio), status=status.HTTP_201_CREATED)


_RANGO = re.compile(r"bytes=(\d*)-(\d*)")
_TIPOS = {
    "pdf_adultos": "application/pdf",
    "pdf_ninos": "application/pdf",
    "audio": None,
}
_MIME_AUDIO = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
}


def _rangos(archivo_field, request, content_type):
    """Respuesta con soporte de Range (necesario para reproducir y avanzar el audio en iPhone)."""
    tamano = archivo_field.size
    encabezado = request.headers.get("Range", "")
    coincide = _RANGO.fullmatch(encabezado.strip()) if encabezado else None
    if not coincide:
        resp = FileResponse(archivo_field.open("rb"), content_type=content_type)
        resp["Accept-Ranges"] = "bytes"
        resp["Cache-Control"] = "private, max-age=300"
        return resp
    inicio, fin = coincide.groups()
    if inicio == "":  # últimos N bytes
        n = int(fin or 0)
        inicio, fin = max(tamano - n, 0), tamano - 1
    else:
        inicio = int(inicio)
        fin = int(fin) if fin else tamano - 1
    fin = min(fin, tamano - 1)
    if inicio > fin or inicio >= tamano:
        resp = HttpResponse(status=416)
        resp["Content-Range"] = f"bytes */{tamano}"
        return resp
    largo = fin - inicio + 1

    def trozos():
        with archivo_field.open("rb") as f:
            f.seek(inicio)
            restante = largo
            while restante > 0:
                dato = f.read(min(64 * 1024, restante))
                if not dato:
                    break
                restante -= len(dato)
                yield dato

    resp = StreamingHttpResponse(trozos(), status=206, content_type=content_type)
    resp["Content-Range"] = f"bytes {inicio}-{fin}/{tamano}"
    resp["Content-Length"] = str(largo)
    resp["Accept-Ranges"] = "bytes"
    resp["Cache-Control"] = "private, max-age=300"
    return resp


class EstudioArchivoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, tipo):
        if tipo not in _TIPOS or not access.puede_ver_estudios(request.user):
            raise Http404
        estudio = get_object_or_404(EstudioSemanal, pk=pk)
        campo = getattr(estudio, tipo)
        if not campo:
            raise Http404
        mime = _TIPOS[tipo]
        if mime is None:
            ext = "." + campo.name.rsplit(".", 1)[-1].lower()
            mime = _MIME_AUDIO.get(ext, "application/octet-stream")
        try:
            return _rangos(campo, request, mime)
        except FileNotFoundError as exc:
            raise Http404 from exc
