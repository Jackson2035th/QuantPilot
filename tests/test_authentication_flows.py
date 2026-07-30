import re

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from backtests.models import BacktestRun, Strategy


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_registration_creates_account_only_after_email_code_and_valid_password(client):
    response = client.post(reverse("register"), {"username": "alice"})
    assert response.status_code == 302
    assert response["Location"] == reverse("register_email")

    response = client.post(reverse("register_email"), {"email": "alice@example.com"})
    assert response.status_code == 302
    assert response["Location"] == reverse("register_verify")
    assert len(mail.outbox) == 1
    assert "QuantPilot verification code" in mail.outbox[0].subject
    assert not User.objects.filter(username="alice").exists()

    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    response = client.post(reverse("register_verify"), {"code": code})
    assert response.status_code == 302
    assert response["Location"] == reverse("register_password")

    response = client.post(
        reverse("register_password"),
        {"password1": "abcdef", "password2": "abcdef"},
    )
    assert response.status_code == 200
    assert b"at least 8 characters" in response.content
    assert not User.objects.filter(username="alice").exists()

    response = client.post(
        reverse("register_password"),
        {"password1": "AlpineRiver829", "password2": "AlpineRiver829"},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")
    user = User.objects.get(username="alice")
    assert user.email == "alice@example.com"
    assert user.check_password("AlpineRiver829")


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_password_reset_uses_email_code_without_disclosing_unknown_addresses(client):
    user = User.objects.create_user(
        username="reset-user", email="reset@example.com", password="original123"
    )

    response = client.post(reverse("password_reset_request"), {"email": user.email})
    assert response.status_code == 302
    assert response["Location"] == reverse("password_reset_verify")
    assert len(mail.outbox) == 1

    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    response = client.post(reverse("password_reset_verify"), {"code": code})
    assert response.status_code == 302
    assert response["Location"] == reverse("password_reset_confirm")

    response = client.post(
        reverse("password_reset_confirm"),
        {"password1": "HarbourStone456", "password2": "HarbourStone456"},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("login")
    user.refresh_from_db()
    assert user.check_password("HarbourStone456")

    mail.outbox.clear()
    response = client.post(
        reverse("password_reset_request"), {"email": "missing@example.com"}, follow=True
    )
    assert response.status_code == 200
    assert b"If an account uses that email address" in response.content
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_rejects_an_invalid_email_address(client):
    response = client.post(reverse("password_reset_request"), {"email": "not-an-email"})

    assert response.status_code == 200
    assert b"Enter a valid email address" in response.content


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_starting_a_new_registration_clears_the_previous_email_verification(client):
    client.post(reverse("register"), {"username": "first-user"})
    client.post(reverse("register_email"), {"email": "first@example.com"})
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    client.post(reverse("register_verify"), {"code": code})

    client.post(reverse("register"), {"username": "second-user"})
    client.post(reverse("register_email"), {"email": "second@example.com"})
    response = client.post(
        reverse("register_password"),
        {"password1": "AlpineRiver829", "password2": "AlpineRiver829"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("register")
    assert not User.objects.filter(username="second-user").exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_starting_a_new_password_reset_clears_the_previous_verified_email(client):
    user = User.objects.create_user(
        username="stale-reset", email="stale@example.com", password="OriginalPass123!"
    )
    client.post(reverse("password_reset_request"), {"email": user.email})
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)
    client.post(reverse("password_reset_verify"), {"code": code})

    client.post(reverse("password_reset_request"), {"email": "missing@example.com"})
    response = client.post(
        reverse("password_reset_confirm"),
        {"password1": "ChangedPass456!", "password2": "ChangedPass456!"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("password_reset_request")
    user.refresh_from_db()
    assert user.check_password("OriginalPass123!")


@pytest.mark.django_db
def test_profile_displays_bound_email_address(client):
    user = User.objects.create_user(
        username="email-profile", email="profile@example.com", password="profile123"
    )
    client.force_login(user)

    response = client.get(reverse("profile"))

    assert response.status_code == 200
    assert b"profile@example.com" in response.content


@pytest.mark.django_db
def test_account_deletion_requires_current_password_and_releases_username(client):
    user = User.objects.create_user(
        username="delete-me", email="delete@example.com", password="delete123"
    )
    strategy = Strategy.objects.create(
        user=user,
        name="Delete strategy",
        original_prompt="Delete this data.",
        strategy_type="ma_crossover",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_cash=10000,
        parameters_json={"short_window": 5, "long_window": 20},
        buy_rule="Buy",
        sell_rule="Sell",
    )
    BacktestRun.objects.create(user=user, strategy=strategy, status="completed")
    client.force_login(user)

    response = client.post(reverse("delete_account"), {"password": "wrong-password"})
    assert response.status_code == 302
    assert response["Location"] == reverse("profile")
    assert User.objects.filter(username="delete-me").exists()
    assert Strategy.objects.filter(user=user).exists()

    response = client.post(reverse("delete_account"), {"password": "delete123"})
    assert response.status_code == 302
    assert response["Location"] == reverse("login")
    assert not User.objects.filter(username="delete-me").exists()
    assert not Strategy.objects.filter(name="Delete strategy").exists()
    assert not BacktestRun.objects.filter(strategy=strategy).exists()

    replacement = User.objects.create_user(username="delete-me", password="replacement123")
    assert replacement.username == "delete-me"
