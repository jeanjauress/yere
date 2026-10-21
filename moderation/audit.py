def log_action(request, action, target, details=""):
    from .models import AuditLog

    return AuditLog.objects.create(
        actor=request.user if request and request.user.is_authenticated else None,
        action=action,
        target_type=target._meta.label,
        target_id=str(target.pk),
        target_repr=str(target)[:200],
        details=details or "",
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )
