import hashlib
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core import audit

from .models import ActivationToken, User
from .phone import normalize_whatsapp


class InvalidCredentials(Exception):
    pass


class AccountLocked(Exception):
    def __init__(self, minutes: int):
        self.minutes = minutes


class InvalidToken(Exception):
    pass


class DuplicateWhatsapp(Exception):
    pass


def find_user(identifier: str) -> User | None:
    """Busca por correo (si trae @) o por número de WhatsApp."""
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    if "@" in identifier:
        return User.objects.filter(email=identifier.lower(), is_active=True).first()
    try:
        return User.objects.filter(whatsapp=normalize_whatsapp(identifier), is_active=True).first()
    except ValidationError:
        return None


def authenticate(identifier: str, credential: str, request=None) -> User:
    user = find_user(identifier)
    if user is None:
        make_password(credential)  # costo similar para no revelar si la cuenta existe
        raise InvalidCredentials
    if user.is_locked():
        remaining = max(1, int((user.locked_until - timezone.now()).total_seconds() // 60) + 1)
        raise AccountLocked(remaining)
    if not user.has_usable_password() or not user.check_password(credential):
        user.register_failure()
        audit.log("auth.login_failed", target=user, request=request)
        if user.is_locked():
            audit.log("auth.locked", target=user, request=request)
        raise InvalidCredentials
    user.clear_failures()
    audit.log("auth.login", actor=user, target=user, request=request)
    return user


# --- tokens de activación / reinicio ---
def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_token(user: User, purpose: str, created_by=None) -> tuple[str, ActivationToken]:
    """Genera un enlace nuevo e invalida los anteriores. Devuelve (token_en_claro, fila)."""
    ActivationToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    raw = secrets.token_urlsafe(32)
    token = ActivationToken.objects.create(
        user=user,
        token_hash=_hash(raw),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(hours=settings.ACTIVATION_TOKEN_HOURS),
        created_by=created_by,
    )
    return raw, token


def get_valid_token(raw: str) -> ActivationToken:
    token = (
        ActivationToken.objects.select_related("user").filter(token_hash=_hash(raw or "")).first()
    )
    if token is None or not token.is_valid() or not token.user.is_active:
        raise InvalidToken
    return token


def complete_activation(raw: str, credential: str, request=None) -> User:
    token = get_valid_token(raw)
    user = token.user
    user.set_credential(credential)  # puede lanzar ValidationError
    with transaction.atomic():
        user.save()
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
    audit.log(f"auth.{token.purpose}_completed", actor=user, target=user, request=request)
    return user


def activation_url(raw: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/activar/{raw}"


def whatsapp_invite_url(user: User, url: str, reset: bool = False) -> str:
    """Enlace de «clic para chatear»: lo envía la persona que invita, sin costo de API."""
    motivo = "reiniciar tu acceso a" if reset else "activar tu cuenta en"
    texto = (
        f"Hola {user.nombre.split()[0]}, entra aquí para {motivo} MDF360 "
        f"(Mundo de Fe México): {url}"
    )
    return f"https://wa.me/{user.whatsapp.lstrip('+')}?text={quote(texto)}"


# --- cambio de número ---
def change_whatsapp(user: User, new_whatsapp: str, credential: str, request=None) -> User:
    if not user.check_password(credential):
        raise InvalidCredentials
    new = normalize_whatsapp(new_whatsapp)
    old = user.whatsapp
    if new == old:
        return user
    user.whatsapp = new
    try:
        with transaction.atomic():
            user.save(update_fields=["whatsapp"])
    except IntegrityError as exc:
        raise DuplicateWhatsapp from exc
    audit.log("auth.whatsapp_changed", actor=user, target=user, request=request, old=old, new=new)
    return user
