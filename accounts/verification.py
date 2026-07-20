import secrets
import time

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail


CODE_LIFETIME_SECONDS = 10 * 60


def send_email_code(session, purpose, email):
    code = f"{secrets.randbelow(1_000_000):06d}"
    session[f"{purpose}_challenge"] = {
        "email": email,
        "code_hash": make_password(code),
        "expires_at": time.time() + CODE_LIFETIME_SECONDS,
    }
    session.modified = True
    send_mail(
        "QuantPilot verification code",
        f"Your QuantPilot verification code is {code}. It expires in 10 minutes.",
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )


def verify_email_code(session, purpose, code):
    challenge = session.get(f"{purpose}_challenge")
    if not challenge or challenge["expires_at"] < time.time():
        session.pop(f"{purpose}_challenge", None)
        return None
    if check_password(code, challenge["code_hash"]):
        return challenge["email"]
    return False


def clear_email_code(session, purpose):
    session.pop(f"{purpose}_challenge", None)
    session.modified = True
