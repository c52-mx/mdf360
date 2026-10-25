import re
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import requiere
from apps.core import audit

from . import access, services
from . import ofrendas as ofr
from .models import EstudioSemanal, Grupo, GrupoMiembro, Reunion

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


def miembro_dict(m: GrupoMiembro) -> dict:
    return {
        "id": m.pk,
        "persona_id": m.persona_id,
        "nombre": m.persona.nombre_completo,
        "rol": m.rol,
        "rol_display": m.get_rol_display(),
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
    sector = serializers.CharField(max_length=100, required=False, allow_blank=True)
    colonia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    dia_semana = serializers.IntegerField(min_value=0, max_value=6, required=False, allow_null=True)
    hora = serializers.TimeField(required=False, allow_null=True)
    activo = serializers.BooleanField(required=False)


# ---------- grupos ----------
class GruposView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grupos = access.grupos_visibles(request.user).filter(activo=True)
        return Response([grupo_resumen(g, request.user) for g in grupos])

    def post(self, request):
        if not access.puede_administrar(request.user):
            return _denegado()
        data = GrupoEscritura(data=request.data)
        data.is_valid(raise_exception=True)
        grupo = Grupo.objects.create(**data.validated_data)
        audit.log("grupo.creado", actor=request.user, target=grupo, request=request)
        return Response(grupo_resumen(grupo, request.user), status=status.HTTP_201_CREATED)


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
            for r in grupo.reuniones.all()[:20]:
                reuniones.append(
                    {
                        "id": r.pk,
                        "fecha": r.fecha.isoformat(),
                        "presentes": r.asistencias.filter(presente=True).count(),
                        "registrados": r.asistencias.count(),
                    }
                )
        else:  # el Secretario solo llega a la reunión de hoy
            hoy = grupo.reuniones.filter(fecha=date.today()).first()
            if hoy:
                reuniones.append({"id": hoy.pk, "fecha": hoy.fecha.isoformat()})
        return Response(
            {
                **grupo_resumen(grupo, request.user),
                "miembros": [miembro_dict(m) for m in miembros],
                "reuniones": reuniones,
                "puede_capturar": access.puede_capturar(request.user, grupo),
                "puede_gestionar": access.puede_gestionar_integrantes(request.user, grupo),
                "puede_administrar": access.puede_administrar(request.user),
            }
        )

    def patch(self, request, pk):
        grupo = self._grupo(request, pk)
        if not access.puede_administrar(request.user):
            return _denegado()
        data = GrupoEscritura(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        for campo, valor in data.validated_data.items():
            setattr(grupo, campo, valor)
        grupo.save()
        audit.log(
            "grupo.actualizado", actor=request.user, target=grupo, request=request,
            campos=sorted(data.validated_data),
        )  # fmt: skip
        return Response(grupo_resumen(grupo, request.user))


# ---------- integrantes ----------
class IntegranteSerializer(serializers.Serializer):
    whatsapp = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    rol = serializers.ChoiceField(choices=GrupoMiembro.Rol.choices, default="asistente")
    acepta_datos = serializers.BooleanField(default=False)


ROLES_RESERVADOS = {"supervisor", "lider"}


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
        if v["rol"] in ROLES_RESERVADOS and not access.puede_administrar(request.user):
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


class IntegranteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, miembro_id):
        grupo = get_object_or_404(Grupo, pk=pk)
        if not access.puede_ver_grupo(request.user, grupo):
            raise Http404
        miembro = get_object_or_404(GrupoMiembro, pk=miembro_id, grupo=grupo)
        if not access.puede_gestionar_integrantes(request.user, grupo):
            return _denegado()
        if miembro.rol in ROLES_RESERVADOS and not access.puede_administrar(request.user):
            return _denegado()
        miembro.activo = False
        miembro.save(update_fields=["activo"])
        audit.log(
            "grupo.integrante_quitado", actor=request.user, target=grupo, request=request,
            persona=miembro.persona_id, rol=miembro.rol,
        )  # fmt: skip
        return Response(status=status.HTTP_204_NO_CONTENT)


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
