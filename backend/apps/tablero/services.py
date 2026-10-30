from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.permissions import tiene_permiso
from apps.core import audit, config
from apps.notificaciones import push

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
    estado = Mensaje.Estado.PUBLICADO
    if not origen.puede_publicar(actor, origen_id):
        if not _puede_solicitar(actor, origen_tipo, origen_id):
            raise SinPermiso
        estado = Mensaje.Estado.PENDIENTE
    etiqueta = origen.etiqueta(origen_id)
    if etiqueta is None:
        raise ValidationError("El origen del mensaje no existe.")
    texto = (texto or "").strip()
    if not texto:
        raise ValidationError("Escribe el mensaje.")
    if len(texto) > LIMITE:
        raise ValidationError(f"El mensaje puede tener hasta {LIMITE} caracteres.")
    mensaje = Mensaje.objects.create(
        estado=estado,
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        origen_etiqueta=etiqueta,
        autor=actor,
        autor_nombre=actor.nombre,
        texto=texto,
        fijado=bool(fijado),
    )
    if estado == Mensaje.Estado.PENDIENTE:
        audit.log(
            "tablero.solicitado", actor=actor, target=mensaje, request=request,
            origen=origen_tipo, origen_id=origen_id,
        )  # fmt: skip
        push.notificar(
            titulo="Aviso por autorizar",
            cuerpo=f"{mensaje.autor_nombre} pide enviar un aviso a toda la iglesia.",
            url="/avisos",
            etiqueta="tablero-por-autorizar",
            puede_recibir=lambda u: u.pk != actor.pk and puede_autorizar_iglesia(u),
            excluir=actor,
        )
        return mensaje
    _publicado(mensaje, origen, actor, request)
    return mensaje


def _publicado(mensaje: Mensaje, origen, actor, request=None) -> None:
    audit.log(
        "tablero.publicado", actor=actor, target=mensaje, request=request,
        origen=mensaje.origen_tipo, origen_id=mensaje.origen_id, fijado=mensaje.fijado,
    )  # fmt: skip
    push.notificar(
        titulo=mensaje.origen_etiqueta,
        cuerpo=f"{mensaje.autor_nombre}: {mensaje.texto}",
        url=origen.ruta(mensaje.origen_id) if origen.ruta else "/avisos",
        etiqueta=f"tablero-{mensaje.origen_tipo}-{mensaje.origen_id}",
        puede_recibir=lambda u: origen.puede_leer(u, mensaje.origen_id),
        excluir=actor,
    )


# ---------- avisos a toda la iglesia: se autorizan ----------
def puede_autorizar_iglesia(user) -> bool:
    """Pastor y Secretaria (quien publica a toda la iglesia), y el líder de grupo o superior."""
    if not (user and user.is_authenticated):
        return False
    if tiene_permiso(user, "avisos.iglesia") or tiene_permiso(user, "grupos.gestionar"):
        return True
    persona = getattr(user, "persona", None)
    if persona is None:
        return False
    from apps.accounts import equipos
    from apps.accounts.models import RolEquipo
    from apps.grupos.models import GrupoMiembro

    de_gestion = [
        r.clave
        for r in RolEquipo.objects.filter(ambito="grupo", activo=True)
        if equipos.permisos_de_gestion(r.permisos)
    ]
    return GrupoMiembro.objects.filter(persona=persona, activo=True, rol__in=de_gestion).exists()


def _puede_solicitar(user, origen_tipo: str, origen_id: int) -> bool:
    """Quien participa y publica en algún tablero puede pedir un aviso a toda la iglesia."""
    from .origenes import ID_IGLESIA

    if origen_tipo != "iglesia" or origen_id != ID_IGLESIA:
        return False
    return any(
        o.puede_publicar(user, i)
        for o in registry.todos()
        if o.listar is not None and o.tipo not in ("iglesia", "persona")
        for i, _ in o.listar(user)
    )


def por_autorizar(user):
    """Avisos que esperan autorización: todos para quien autoriza; los propios para quien pidió."""
    qs = Mensaje.objects.filter(estado=Mensaje.Estado.PENDIENTE, eliminado=False)
    if puede_autorizar_iglesia(user):
        return qs
    return qs.filter(autor=user)


def resolver(mensaje: Mensaje, *, autorizar: bool, actor, request=None) -> Mensaje:
    if mensaje.estado != Mensaje.Estado.PENDIENTE:
        raise ValidationError("Este aviso ya se resolvió.")
    if not puede_autorizar_iglesia(actor):
        raise SinPermiso
    if mensaje.autor_id == actor.pk:
        raise SinPermiso  # nadie autoriza su propio aviso
    mensaje.resuelto_por = actor
    mensaje.resuelto_en = timezone.now()
    if autorizar:
        mensaje.estado = Mensaje.Estado.PUBLICADO
        mensaje.creado_en = timezone.now()  # llega como nuevo, no como algo viejo
        mensaje.save(update_fields=["estado", "resuelto_por", "resuelto_en", "creado_en"])
        _publicado(mensaje, registry.obtener(mensaje.origen_tipo), mensaje.autor)
        audit.log("tablero.autorizado", actor=actor, target=mensaje, request=request)
    else:
        mensaje.estado = Mensaje.Estado.RECHAZADO
        mensaje.save(update_fields=["estado", "resuelto_por", "resuelto_en"])
        audit.log("tablero.rechazado", actor=actor, target=mensaje, request=request)
    return mensaje


def mensajes_de(user, origen_tipo, origen_id):
    origen = registry.obtener(origen_tipo)
    if origen is None or not origen.puede_leer(user, origen_id):
        return None
    return Mensaje.objects.filter(
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        eliminado=False,
        estado=Mensaje.Estado.PUBLICADO,
    )


def puede_moderar(user, mensaje: Mensaje) -> bool:
    """Fijar o quitar: quien publicó o quien modera el origen (por omisión, quien publica)."""
    origen = registry.obtener(mensaje.origen_tipo)
    if origen is None:
        return False
    moderador = origen.puede_moderar or origen.puede_publicar
    return mensaje.autor_id == getattr(user, "pk", None) or moderador(user, mensaje.origen_id)


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
        qs = Mensaje.objects.filter(
            origen_tipo=origen.tipo, eliminado=False, estado=Mensaje.Estado.PUBLICADO
        ).exclude(autor=user)
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


MAX_DESTINOS = 60


def destinos_para_publicar(user) -> list[dict]:
    """Los tableros donde la persona puede publicar, para elegir a quién enviar un aviso."""
    filas = []
    for origen in registry.todos():
        if origen.listar is None or origen.tipo == "persona":
            continue  # a personas se elige una por una
        for origen_id, etiqueta in origen.listar(user):
            directo = origen.puede_publicar(user, origen_id)
            if directo or _puede_solicitar(user, origen.tipo, origen_id):
                filas.append(
                    {
                        "tipo": origen.tipo,
                        "tipo_display": origen.nombre,
                        "id": origen_id,
                        "etiqueta": etiqueta,
                        # Toda la iglesia: quien no la publica directo la pide y alguien la autoriza
                        "requiere_autorizacion": not directo,
                    }
                )
    return filas


def publicar_masivo(*, destinos, texto, actor, fijado=False, request=None) -> dict:
    """Publica el mismo aviso en varios tableros. Cada destino respeta sus propios permisos: los
    que la persona no puede publicar se omiten y se informan, sin detener el resto."""
    vistos, unicos = set(), []
    for d in destinos:
        clave = (d["tipo"], d["id"])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(d)
    if not unicos:
        raise ValidationError("Elige a quién enviar el aviso.")
    if len(unicos) > MAX_DESTINOS:
        raise ValidationError(f"Puedes enviar a {MAX_DESTINOS} destinos como máximo a la vez.")
    texto = (texto or "").strip()
    if not texto:
        raise ValidationError("Escribe el mensaje.")
    enviados, omitidos, pendientes = [], [], []
    for d in unicos:
        try:
            m = publicar(
                origen_tipo=d["tipo"],
                origen_id=d["id"],
                texto=texto,
                actor=actor,
                fijado=fijado,
                request=request,
            )
            fila = {"tipo": d["tipo"], "id": d["id"], "etiqueta": m.origen_etiqueta}
            (pendientes if m.estado == Mensaje.Estado.PENDIENTE else enviados).append(fila)
        except (OrigenDesconocido, SinPermiso, ValidationError):
            omitidos.append({"tipo": d["tipo"], "id": d["id"]})
    audit.log(
        "tablero.masivo", actor=actor, request=request,
        enviados=len(enviados), omitidos=len(omitidos), pendientes=len(pendientes),
    )  # fmt: skip
    return {"enviados": enviados, "omitidos": omitidos, "pendientes": pendientes}


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
        "estado": m.estado,
        "estado_display": m.get_estado_display(),
        "creado_en": m.creado_en.isoformat(),
        "es_mio": m.autor_id == user.pk,
        "puede_moderar": puede_moderar(user, m),
    }


_ = Q
