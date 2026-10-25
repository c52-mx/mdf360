from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone

from apps.core import audit, config

from . import registry
from .models import Lectura, Mensaje

LIMITE = 1000


class OrigenDesconocido(Exception):
    pass


class SinPermiso(Exception):
    pass


def purgar_antiguos() -> int:
    """Borra los mensajes que superan los días de conservación configurados."""
    dias = int(config.obtener("tablero.dias_retencion"))
    antiguos = Mensaje.objects.filter(creado_en__lt=timezone.now() - timedelta(days=dias))
    total = antiguos.count()
    if total:
        antiguos.delete()
        audit.log("tablero.purgados", cantidad=total)
    return total


def publicar(*, origen_tipo, origen_id, texto, actor, fijado=False, request=None) -> Mensaje:
    origen = registry.obtener(origen_tipo)
    if origen is None:
        raise OrigenDesconocido
    if not origen.puede_publicar(actor, origen_id):
        raise SinPermiso
    etiqueta = origen.etiqueta(origen_id)
    if etiqueta is None:
        raise ValidationError("El origen del mensaje no existe.")
    texto = (texto or "").strip()
    if not texto:
        raise ValidationError("Escribe el mensaje.")
    if len(texto) > LIMITE:
        raise ValidationError(f"El mensaje puede tener hasta {LIMITE} caracteres.")
    mensaje = Mensaje.objects.create(
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        origen_etiqueta=etiqueta,
        autor=actor,
        autor_nombre=actor.nombre,
        texto=texto,
        fijado=bool(fijado),
    )
    audit.log(
        "tablero.publicado", actor=actor, target=mensaje, request=request,
        origen=origen_tipo, origen_id=origen_id, fijado=mensaje.fijado,
    )  # fmt: skip
    return mensaje


def mensajes_de(user, origen_tipo, origen_id):
    origen = registry.obtener(origen_tipo)
    if origen is None or not origen.puede_leer(user, origen_id):
        return None
    return Mensaje.objects.filter(origen_tipo=origen_tipo, origen_id=origen_id, eliminado=False)


def puede_moderar(user, mensaje: Mensaje) -> bool:
    """Fijar o quitar: quien publicó o quien puede publicar en ese origen."""
    origen = registry.obtener(mensaje.origen_tipo)
    if origen is None:
        return False
    return mensaje.autor_id == getattr(user, "pk", None) or origen.puede_publicar(
        user, mensaje.origen_id
    )


def marcar_visto(user, origen_tipo, origen_id) -> bool:
    origen = registry.obtener(origen_tipo)
    if origen is None or not origen.puede_leer(user, origen_id):
        return False
    Lectura.objects.update_or_create(
        usuario=user,
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        defaults={"visto_hasta": timezone.now()},
    )
    return True


def no_leidos(user) -> dict[str, dict[int, int]]:
    """Mensajes nuevos por origen: {tipo: {id: cantidad}}, solo de los orígenes que puede leer."""
    resultado: dict[str, dict[int, int]] = {}
    vistos = {
        (lec.origen_tipo, lec.origen_id): lec.visto_hasta
        for lec in Lectura.objects.filter(usuario=user)
    }
    for origen in registry.todos():
        ids = origen.ids_legibles(user)
        qs = Mensaje.objects.filter(origen_tipo=origen.tipo, eliminado=False).exclude(autor=user)
        if ids is not None:
            qs = qs.filter(origen_id__in=ids)
        por_origen = {
            fila["origen_id"]: fila["n"] for fila in qs.values("origen_id").annotate(n=Count("id"))
        }
        conteo = {}
        for origen_id in por_origen:
            visto = vistos.get((origen.tipo, origen_id))
            q = qs.filter(origen_id=origen_id)
            if visto:
                q = q.filter(creado_en__gt=visto)
            n = q.count()
            if n:
                conteo[origen_id] = n
        if conteo:
            resultado[origen.tipo] = conteo
    return resultado


def mis_tableros(user) -> list[dict]:
    """Tableros que la persona puede leer, con mensajes sin leer y si puede publicar."""
    pendientes = no_leidos(user)
    filas = []
    for origen in registry.todos():
        if origen.listar is None:
            continue
        for origen_id, etiqueta in origen.listar(user):
            filas.append(
                {
                    "tipo": origen.tipo,
                    "tipo_display": origen.nombre,
                    "id": origen_id,
                    "etiqueta": etiqueta,
                    "no_leidos": pendientes.get(origen.tipo, {}).get(origen_id, 0),
                    "puede_publicar": origen.puede_publicar(user, origen_id),
                }
            )
    return filas


def mensaje_dict(m: Mensaje, user) -> dict:
    return {
        "id": m.pk,
        "origen": {"tipo": m.origen_tipo, "id": m.origen_id, "etiqueta": m.origen_etiqueta},
        "autor": m.autor_nombre,
        "texto": m.texto,
        "fijado": m.fijado,
        "creado_en": m.creado_en.isoformat(),
        "es_mio": m.autor_id == user.pk,
        "puede_moderar": puede_moderar(user, m),
    }


_ = Q
