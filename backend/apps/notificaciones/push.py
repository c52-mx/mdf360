"""Envío de notificaciones push (M1-09).

El servidor firma cada envío con las claves VAPID y el servicio push del navegador (Google, Apple
o Mozilla) lo entrega al teléfono aunque la aplicación esté cerrada. El sonido y la vibración los
define el service worker al mostrarla y el sistema operativo según los ajustes del teléfono.
"""

import json
import logging
import threading
from collections.abc import Callable

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from pywebpush import WebPushException, webpush

from apps.core import config

from .models import Suscripcion

log = logging.getLogger(__name__)

CUERPO_MAX = 140


def configurado() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def disponible() -> bool:
    return configurado() and bool(config.obtener("notificaciones.activas"))


def _transporte(info: dict, payload: str) -> None:
    webpush(
        subscription_info=info,
        data=payload,
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": settings.VAPID_SUBJECT},
        ttl=24 * 60 * 60,
    )


def _recortar(texto: str) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= CUERPO_MAX else texto[: CUERPO_MAX - 1].rstrip() + "…"


def _enviar(destinos: list[tuple[int, dict]], payload: str) -> None:
    caducadas = []
    enviadas = []
    for pk, info in destinos:
        try:
            _transporte(info, payload)
            enviadas.append(pk)
        except WebPushException as exc:
            codigo = getattr(exc.response, "status_code", None)
            if codigo in (404, 410):  # el dispositivo ya no existe o revocó el permiso
                caducadas.append(pk)
            else:
                log.warning("Push no entregado (%s): %s", codigo, exc)
        except Exception:  # un fallo con un dispositivo no debe frenar a los demás
            log.exception("Push no entregado")
    if caducadas:
        Suscripcion.objects.filter(pk__in=caducadas).delete()
    if enviadas:
        Suscripcion.objects.filter(pk__in=enviadas).update(ultimo_envio=timezone.now())


def _enviar_en_segundo_plano(destinos, payload):
    try:
        _enviar(destinos, payload)
    finally:
        close_old_connections()


def notificar(
    *,
    titulo: str,
    cuerpo: str,
    url: str = "/",
    etiqueta: str | None = None,
    puede_recibir: Callable[[object], bool] | None = None,
    excluir=None,
    usuarios=None,
) -> int:
    """Avisa a los dispositivos suscritos; devuelve cuántos dispositivos recibirán el aviso.

    `puede_recibir(usuario)` filtra por permisos (cada módulo decide quién ve qué), `excluir` deja
    fuera a quien originó el aviso y `usuarios` limita a esas personas. El envío ocurre después de
    confirmar la transacción y sin hacer esperar a quien publicó.
    """
    if not disponible():
        return 0
    suscripciones = Suscripcion.objects.select_related("usuario").filter(usuario__is_active=True)
    if usuarios is not None:
        suscripciones = suscripciones.filter(usuario__in=usuarios)
    if excluir is not None:
        suscripciones = suscripciones.exclude(usuario=excluir)
    permitidos: dict[int, bool] = {}
    destinos = []
    for s in suscripciones:
        if puede_recibir is not None:
            if s.usuario_id not in permitidos:
                permitidos[s.usuario_id] = bool(puede_recibir(s.usuario))
            if not permitidos[s.usuario_id]:
                continue
        info = {"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}}
        destinos.append((s.pk, info))
    if not destinos:
        return 0
    payload = json.dumps(
        {"titulo": titulo, "cuerpo": _recortar(cuerpo), "url": url, "etiqueta": etiqueta},
        ensure_ascii=False,
    )

    def enviar():
        if settings.PUSH_EN_SEGUNDO_PLANO:
            threading.Thread(
                target=_enviar_en_segundo_plano, args=(destinos, payload), daemon=True
            ).start()
        else:
            _enviar(destinos, payload)

    transaction.on_commit(enviar)
    return len(destinos)
