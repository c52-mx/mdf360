from django.core.exceptions import ValidationError
from django.db.models import Count, Q

from apps.accounts.permissions import tiene_permiso
from apps.core import audit
from apps.notificaciones import push
from apps.tablero import registry

from . import segmentos
from .models import Audiencia, Comentario, Publicacion, Reaccion

LIMITE = 2000
MAX_AUDIENCIAS = 20
PAGINA = 20


class SinPermiso(Exception):
    pass


def _activo(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active)


def etiqueta_de(tipo: str, ref_id: int) -> str | None:
    """Nombre visible de una audiencia, o None si no existe."""
    if tipo == Audiencia.Tipo.IGLESIA:
        return "Toda la iglesia" if ref_id == segmentos.ID_IGLESIA else None
    if tipo == Audiencia.Tipo.SEGMENTO:
        return segmentos.SEGMENTOS.get(ref_id)
    origen = registry.obtener(tipo)
    return origen.etiqueta(ref_id) if origen else None


def puede_ver_audiencia(user, tipo: str, ref_id: int) -> bool:
    if not _activo(user):
        return False
    if tipo == Audiencia.Tipo.IGLESIA:
        return ref_id == segmentos.ID_IGLESIA
    if tipo == Audiencia.Tipo.SEGMENTO:
        return segmentos.pertenece(user, ref_id)
    origen = registry.obtener(tipo)
    return bool(origen and origen.puede_leer(user, ref_id))


def puede_publicar_en(user, tipo: str, ref_id: int) -> bool:
    """Toda la iglesia y los segmentos piden `muro.publicar`; grupo y ministerio, su permiso de
    equipo «avisos» (configurable por rol)."""
    if not _activo(user):
        return False
    if tipo in (Audiencia.Tipo.IGLESIA, Audiencia.Tipo.SEGMENTO):
        return tiene_permiso(user, "muro.publicar")
    origen = registry.obtener(tipo)
    return bool(origen and origen.puede_publicar(user, ref_id))


def destinos_para_publicar(user) -> list[dict]:
    """Las audiencias a las que la persona puede dirigir una publicación."""
    filas = []
    if tiene_permiso(user, "muro.publicar"):
        filas.append({"tipo": "iglesia", "id": segmentos.ID_IGLESIA, "etiqueta": "Toda la iglesia"})
        filas += [
            {"tipo": "segmento", "id": i, "etiqueta": n} for i, n in segmentos.SEGMENTOS.items()
        ]
    for tipo in (Audiencia.Tipo.GRUPO, Audiencia.Tipo.UNIDAD):
        origen = registry.obtener(tipo)
        if origen is None or origen.listar is None:
            continue
        for ref_id, etiqueta in origen.listar(user):
            if origen.puede_publicar(user, ref_id):
                filas.append({"tipo": tipo.value, "id": ref_id, "etiqueta": etiqueta})
    return filas


def puede_ver(user, publicacion: Publicacion) -> bool:
    if not _activo(user) or publicacion.eliminada:
        return False
    if publicacion.autor_id == user.pk:
        return True
    return any(puede_ver_audiencia(user, a.tipo, a.ref_id) for a in publicacion.audiencias.all())


def publicar(*, texto, destinos, actor, request=None) -> Publicacion:
    """Crea una publicación para varias audiencias. Si no puede publicar en alguna, no se crea."""
    texto = (texto or "").strip()
    if not texto:
        raise ValidationError("Escribe la publicación.")
    if len(texto) > LIMITE:
        raise ValidationError(f"La publicación puede tener hasta {LIMITE} caracteres.")
    unicos, vistos = [], set()
    for d in destinos or []:
        clave = (d["tipo"], int(d["id"]))
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(clave)
    if not unicos:
        raise ValidationError("Elige a quién va dirigida.")
    if len(unicos) > MAX_AUDIENCIAS:
        raise ValidationError(f"Puedes elegir hasta {MAX_AUDIENCIAS} audiencias.")
    etiquetas = []
    for tipo, ref_id in unicos:
        if tipo not in Audiencia.Tipo.values:
            raise ValidationError("Una de las audiencias no es válida.")
        etiqueta = etiqueta_de(tipo, ref_id)
        if etiqueta is None:
            raise ValidationError("Una de las audiencias no existe.")
        if not puede_publicar_en(actor, tipo, ref_id):
            raise SinPermiso
        etiquetas.append(etiqueta)
    publicacion = Publicacion.objects.create(autor=actor, autor_nombre=actor.nombre, texto=texto)
    Audiencia.objects.bulk_create(
        [
            Audiencia(publicacion=publicacion, tipo=t, ref_id=i, etiqueta=e)
            for (t, i), e in zip(unicos, etiquetas, strict=True)
        ]
    )
    audit.log(
        "muro.publicado", actor=actor, target=publicacion, request=request,
        audiencias=[f"{t}:{i}" for t, i in unicos],
    )  # fmt: skip
    push.notificar(
        titulo=" · ".join(etiquetas[:2]) + (" y más" if len(etiquetas) > 2 else ""),
        cuerpo=f"{publicacion.autor_nombre}: {texto}",
        url="/",
        etiqueta=f"muro-{publicacion.pk}",
        puede_recibir=lambda u: puede_ver(u, publicacion),
        excluir=actor,
    )
    return publicacion


def visibles(user):
    """Publicaciones que la persona puede leer: las de sus audiencias y las propias."""
    if not _activo(user):
        return Publicacion.objects.none()
    cond = Q(autor=user) | Q(audiencias__tipo="iglesia", audiencias__ref_id=segmentos.ID_IGLESIA)
    for sid in segmentos.SEGMENTOS:
        if segmentos.pertenece(user, sid):
            cond |= Q(audiencias__tipo="segmento", audiencias__ref_id=sid)
    for tipo in (Audiencia.Tipo.GRUPO, Audiencia.Tipo.UNIDAD):
        origen = registry.obtener(tipo)
        if origen is None:
            continue
        ids = origen.ids_legibles(user)
        if ids is None:
            cond |= Q(audiencias__tipo=tipo)
        elif ids:
            cond |= Q(audiencias__tipo=tipo, audiencias__ref_id__in=ids)
    return Publicacion.objects.filter(cond, eliminada=False).distinct()


def muro(user, *, antes: int | None = None, audiencia: tuple[str, int] | None = None):
    """Una página del muro (más recientes primero); trae una de más para saber si hay otra.
    `antes` = id de la última publicación vista."""
    qs = visibles(user)
    if audiencia is not None:
        qs = qs.filter(audiencias__tipo=audiencia[0], audiencias__ref_id=audiencia[1])
    if antes:
        qs = qs.filter(pk__lt=antes)
    return list(qs.prefetch_related("audiencias").order_by("-id")[: PAGINA + 1])


LIMITE_COMENTARIO = 500


def reaccionar(publicacion: Publicacion, user, tipo: str | None) -> None:
    """Pone, cambia o quita (tipo=None, o el mismo tipo otra vez) la reacción de la persona."""
    if not puede_ver(user, publicacion):
        raise SinPermiso
    if tipo is not None and tipo not in Reaccion.Tipo.values:
        raise ValidationError("Esa reacción no existe.")
    actual = Reaccion.objects.filter(publicacion=publicacion, usuario=user).first()
    if tipo is None or (actual and actual.tipo == tipo):
        if actual:
            actual.delete()
        return
    Reaccion.objects.update_or_create(
        publicacion=publicacion, usuario=user, defaults={"tipo": tipo}
    )


def comentar(publicacion: Publicacion, user, texto, request=None) -> Comentario:
    if not puede_ver(user, publicacion):
        raise SinPermiso
    texto = (texto or "").strip()
    if not texto:
        raise ValidationError("Escribe el comentario.")
    if len(texto) > LIMITE_COMENTARIO:
        raise ValidationError(f"El comentario puede tener hasta {LIMITE_COMENTARIO} caracteres.")
    comentario = Comentario.objects.create(
        publicacion=publicacion, autor=user, autor_nombre=user.nombre, texto=texto
    )
    if publicacion.autor_id and publicacion.autor_id != user.pk:
        push.notificar(
            titulo="Comentaron tu publicación",
            cuerpo=f"{user.nombre}: {texto}",
            url="/",
            etiqueta=f"muro-comentario-{publicacion.pk}",
            usuarios=[publicacion.autor],
        )
    return comentario


def puede_quitar_comentario(user, comentario: Comentario) -> bool:
    """Lo quita quien lo escribió o quien escribió la publicación."""
    return user.pk in (comentario.autor_id, comentario.publicacion.autor_id)


def comentario_dict(c: Comentario, user) -> dict:
    return {
        "id": c.pk,
        "autor": c.autor_nombre,
        "texto": c.texto,
        "creado_en": c.creado_en.isoformat(),
        "es_mio": c.autor_id == user.pk,
        "puede_quitar": puede_quitar_comentario(user, c),
    }


def _resumen(publicaciones, user) -> dict[int, dict]:
    ids = [p.pk for p in publicaciones]
    reacciones: dict[int, dict[str, int]] = {i: {} for i in ids}
    for f in (
        Reaccion.objects.filter(publicacion_id__in=ids)
        .values("publicacion_id", "tipo")
        .annotate(n=Count("id"))
    ):
        reacciones[f["publicacion_id"]][f["tipo"]] = f["n"]
    mias = dict(
        Reaccion.objects.filter(publicacion_id__in=ids, usuario=user).values_list(
            "publicacion_id", "tipo"
        )
    )
    comentarios = dict(
        Comentario.objects.filter(publicacion_id__in=ids, eliminado=False)
        .values("publicacion_id")
        .annotate(n=Count("id"))
        .values_list("publicacion_id", "n")
    )
    return {
        i: {
            "reacciones": reacciones[i],
            "mi_reaccion": mias.get(i),
            "comentarios_total": comentarios.get(i, 0),
        }
        for i in ids
    }


def publicaciones_dict(publicaciones, user) -> list[dict]:
    resumen = _resumen(publicaciones, user)
    return [publicacion_dict(p, user) | resumen[p.pk] for p in publicaciones]


def publicacion_dict(p: Publicacion, user) -> dict:
    return {
        "id": p.pk,
        "autor": p.autor_nombre,
        "texto": p.texto,
        "creada_en": p.creada_en.isoformat(),
        "audiencias": [
            {"tipo": a.tipo, "id": a.ref_id, "etiqueta": a.etiqueta} for a in p.audiencias.all()
        ],
        "es_mia": p.autor_id == user.pk,
    }
