from .models import AuditEvent

# Semáforo de la bitácora: lo que no aparece aquí es informativo (verde).
ACCIONES_ERROR = frozenset({"auth.locked", "ofrenda.aval_pin_incorrecto"})
ACCIONES_AVISO = frozenset(
    {
        "auth.login_failed",
        "auth.reset_issued",
        "auth.unlocked",
        "rbac.roles_changed",
        "persona.baja",
        "peticion.purgadas",
        "tablero.eliminado",
        "tablero.purgados",
    }
)


def nivel_de(action: str) -> str:
    """Clasifica un evento: «error» (rojo), «aviso» (amarillo) o «info» (verde)."""
    if action in ACCIONES_ERROR:
        return "error"
    return "aviso" if action in ACCIONES_AVISO else "info"


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
