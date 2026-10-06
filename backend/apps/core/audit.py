from .models import AuditEvent


def client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log(action: str, *, actor=None, target=None, request=None, **detail) -> AuditEvent:
    """Registra un evento en la bitácora. `target` es cualquier modelo con pk."""
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        actor_repr=str(actor) if actor else "",
        action=action,
        target_type=target.__class__.__name__ if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        detail=detail,
        ip=client_ip(request),
    )
