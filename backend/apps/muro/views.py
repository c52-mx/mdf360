from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Comentario, Publicacion


def _error(code, detail, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "detail": detail}, status=http_status)


class DestinoSerializer(serializers.Serializer):
    tipo = serializers.CharField(max_length=12)
    id = serializers.IntegerField(min_value=1)


class PublicarSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=2000)
    destinos = DestinoSerializer(many=True)


class MuroView(APIView):
    """El muro de la persona: lo dirigido a ella, página por página (`?antes=<id>`)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        antes = request.query_params.get("antes", "")
        tipo = request.query_params.get("audiencia_tipo", "")
        ref = request.query_params.get("audiencia_id", "")
        if (antes and not antes.isdigit()) or (tipo and not ref.isdigit()):
            return _error("invalid", "Los parámetros del muro no son válidos.")
        filas = services.muro(
            request.user,
            antes=int(antes) if antes else None,
            audiencia=(tipo, int(ref)) if tipo else None,
        )
        primera = not antes
        hay_mas = len(filas) > services.PAGINA
        filas = filas[: services.PAGINA]
        return Response(
            {
                "fijadas": services.publicaciones_dict(
                    services.fijadas(request.user, (tipo, int(ref)) if tipo else None),
                    request.user,
                )
                if primera
                else [],
                "resultados": services.publicaciones_dict(filas, request.user),
                "siguiente": filas[-1].pk if hay_mas and filas else None,
            }
        )

    def post(self, request):
        data = PublicarSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            publicacion = services.publicar(
                actor=request.user, request=request, **data.validated_data
            )
        except services.SinPermiso:
            return _error(
                "forbidden", "No puedes publicar en alguna de esas audiencias.",
                status.HTTP_403_FORBIDDEN,
            )  # fmt: skip
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(
            services.publicaciones_dict([publicacion], request.user)[0],
            status=status.HTTP_201_CREATED,
        )


class DestinosView(APIView):
    """Las audiencias a las que la persona puede publicar (vacío = no puede publicar)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.destinos_para_publicar(request.user))


def _publicacion_visible(request, pk) -> Publicacion:
    """La publicación, o 404 si no existe o la persona no la puede ver (no se revela cuál)."""
    publicacion = Publicacion.objects.filter(pk=pk, eliminada=False).first()
    if publicacion is None or not services.puede_ver(request.user, publicacion):
        raise Http404
    return publicacion


class ReaccionView(APIView):
    """Pone, cambia o quita la reacción propia: {"tipo": "amen"}; null la quita."""

    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        publicacion = _publicacion_visible(request, pk)
        tipo = request.data.get("tipo")
        if tipo is not None and not isinstance(tipo, str):
            return _error("invalid", "Indica la reacción.")
        try:
            services.reaccionar(publicacion, request.user, tipo)
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(services.publicaciones_dict([publicacion], request.user)[0])


class ComentariosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        publicacion = _publicacion_visible(request, pk)
        comentarios = publicacion.comentarios.filter(eliminado=False)
        return Response([services.comentario_dict(c, request.user) for c in comentarios])

    def post(self, request, pk):
        publicacion = _publicacion_visible(request, pk)
        texto = request.data.get("texto")
        if not isinstance(texto, str):
            return _error("invalid", "Escribe el comentario.")
        try:
            comentario = services.comentar(publicacion, request.user, texto, request)
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(
            services.comentario_dict(comentario, request.user), status=status.HTTP_201_CREATED
        )


class ComentarioView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        comentario = (
            Comentario.objects.filter(pk=pk, eliminado=False).select_related("publicacion").first()
        )
        if comentario is None or not services.puede_ver(request.user, comentario.publicacion):
            raise Http404
        if not services.puede_quitar_comentario(request.user, comentario):
            return _error(
                "forbidden", "No puedes quitar este comentario.", status.HTTP_403_FORBIDDEN
            )
        comentario.eliminado = True
        comentario.save(update_fields=["eliminado"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicacionView(APIView):
    """Editar (su autor), fijar (quien modera) o eliminar (su autor o quien modera)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        publicacion = _publicacion_visible(request, pk)
        try:
            if "texto" in request.data:
                if not isinstance(request.data["texto"], str):
                    return _error("invalid", "Escribe la publicación.")
                services.editar(publicacion, request.user, request.data["texto"], request)
            if "fijada" in request.data:
                if not isinstance(request.data["fijada"], bool):
                    return _error("invalid", "Indica si se fija o no.")
                services.fijar(publicacion, request.user, request.data["fijada"], request)
        except services.SinPermiso:
            return _error(
                "forbidden", "No puedes cambiar esta publicación.", status.HTTP_403_FORBIDDEN
            )
        except DjangoValidationError as exc:
            return _error("invalid", " ".join(exc.messages))
        return Response(services.publicaciones_dict([publicacion], request.user)[0])

    def delete(self, request, pk):
        publicacion = _publicacion_visible(request, pk)
        try:
            services.eliminar(publicacion, request.user, request)
        except services.SinPermiso:
            return _error(
                "forbidden", "No puedes eliminar esta publicación.", status.HTTP_403_FORBIDDEN
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        publicacion = _publicacion_visible(request, pk)
        services.reportar(publicacion, request.user, request.data.get("motivo", ""), request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AtenderReportesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        publicacion = _publicacion_visible(request, pk)
        try:
            services.atender_reportes(publicacion, request.user, request)
        except services.SinPermiso:
            return _error("forbidden", "No puedes atender reportes.", status.HTTP_403_FORBIDDEN)
        return Response(services.publicaciones_dict([publicacion], request.user)[0])
