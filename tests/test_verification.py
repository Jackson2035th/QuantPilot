import re
from unittest.mock import patch

import pytest
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from accounts.verification import verify_email_code


@pytest.fixture(autouse=True)
def clear_verification_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_registration_code_can_only_be_sent_once_during_the_cooldown(client):
    client.post(reverse("register"), {"username": "cooldown-user"})
    first = client.post(reverse("register_email"), {"email": "cooldown@example.com"})
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    second = client.post(reverse("register_email"), {"email": "cooldown@example.com"})

    assert first.status_code == 302
    assert second.status_code == 302
    assert len(mail.outbox) == 1

    response = client.post(reverse("register_verify"), {"code": code})
    assert response["Location"] == reverse("register_password")


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    VERIFICATION_CODE_MAX_FAILURES=3,
)
def test_verification_code_is_removed_after_too_many_failures(client):
    client.post(reverse("register"), {"username": "attempt-user"})
    client.post(reverse("register_email"), {"email": "attempt@example.com"})
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    wrong_code = "000001" if code == "000000" else "000000"

    for _ in range(3):
        response = client.post(reverse("register_verify"), {"code": wrong_code})
        assert response.status_code == 200

    assert "registration_challenge" not in client.session
    response = client.post(reverse("register_verify"), {"code": code})
    assert response.status_code == 200
    assert b"invalid or has expired" in response.content


@pytest.mark.django_db
def test_verification_code_expires_at_the_exact_deadline(client):
    session = client.session
    session["registration_challenge"] = {
        "email": "expiry@example.com",
        "code_hash": make_password("123456"),
        "expires_at": 100,
        "failed_attempts": 0,
    }

    with patch("accounts.verification.time.time", return_value=100):
        assert verify_email_code(session, "registration", "123456") is None

    assert "registration_challenge" not in session
