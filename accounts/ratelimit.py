from django.conf import settings
from django.core.cache import cache


def _key(request, username):
    ip = request.META.get("REMOTE_ADDR", "")
    return f"login-fail:{ip}:{(username or '').lower()}"


def is_locked(request, username):
    return cache.get(_key(request, username), 0) >= settings.LOGIN_MAX_ATTEMPTS


def register_failure(request, username):
    key = _key(request, username)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, settings.LOGIN_LOCKOUT_SECONDS)


def reset(request, username):
    cache.delete(_key(request, username))
