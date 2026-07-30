import hashlib
import secrets
import time

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.mail import send_mail


def _cooldown_key(purpose, email):
    value = hashlib.sha256(f"{purpose}:{email.casefold()}".encode()).hexdigest()
    return f"verification-code:{value}"


def send_email_code(session, purpose, email, deliver=True):
    cooldown = getattr(settings, "VERIFICATION_CODE_SEND_COOLDOWN_SECONDS", 60)
    if not cache.add(_cooldown_key(purpose, email), True, timeout=cooldown):
        return False

    clear_email_code(session, purpose)
    code = f"{secrets.randbelow(1_000_000):06d}"
    lifetime = getattr(settings, "VERIFICATION_CODE_LIFETIME_SECONDS", 10 * 60)
    if not deliver:
        # Keep the unknown-email path closer in cost without creating a usable challenge.
        make_password(code)
        return True

    challenge = {
        "email": email,
        "code_hash": make_password(code),
        "expires_at": time.time() + lifetime,
        "failed_attempts": 0,
    }
    send_mail(
        "QuantPilot verification code",
        f"Your QuantPilot verification code is {code}. It expires in 10 minutes.",
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )
    session[f"{purpose}_challenge"] = challenge
    session.modified = True


def verify_email_code(session, purpose, code):
    challenge = session.get(f"{purpose}_challenge")
    if not challenge or challenge["expires_at"] <= time.time():
        clear_email_code(session, purpose)
        return None
    if check_password(code, challenge["code_hash"]):
        email = challenge["email"]
        clear_email_code(session, purpose)
        return email

    challenge["failed_attempts"] = challenge.get("failed_attempts", 0) + 1
    max_failures = getattr(settings, "VERIFICATION_CODE_MAX_FAILURES", 5)
    if challenge["failed_attempts"] >= max_failures:
        clear_email_code(session, purpose)
    else:
        session[f"{purpose}_challenge"] = challenge
        session.modified = True
    return False


def clear_email_code(session, purpose):
    session.pop(f"{purpose}_challenge", None)
    session.modified = True
