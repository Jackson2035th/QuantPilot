import hashlib

from django.conf import settings
from django.core.cache import cache


def _login_key(request, name):
    username = request.POST.get("username", "").strip().casefold()
    address = request.META.get("REMOTE_ADDR", "unknown")
    value = hashlib.sha256(f"{address}:{username}".encode()).hexdigest()
    return f"login:{name}:{value}"


def login_is_locked(request):
    if not request.POST.get("username", "").strip():
        return False
    return bool(cache.get(_login_key(request, "locked")))


def record_failed_login(request):
    if not request.POST.get("username", "").strip() or not request.POST.get("password"):
        return False

    failures_key = _login_key(request, "failures")
    limit = getattr(settings, "AUTH_LOGIN_MAX_FAILURES", 5)
    lock_seconds = getattr(settings, "AUTH_LOGIN_LOCK_SECONDS", 5 * 60)
    if cache.add(failures_key, 1, timeout=lock_seconds):
        failures = 1
    else:
        try:
            failures = cache.incr(failures_key)
        except ValueError:
            # The key may expire between add() and incr(). Start a new window if it does.
            if cache.add(failures_key, 1, timeout=lock_seconds):
                failures = 1
            else:
                failures = cache.incr(failures_key)

    if failures >= limit:
        cache.delete(failures_key)
        cache.set(_login_key(request, "locked"), True, timeout=lock_seconds)
        return True

    return False


def clear_login_failures(request):
    cache.delete_many(
        [
            _login_key(request, "failures"),
            _login_key(request, "locked"),
        ]
    )
