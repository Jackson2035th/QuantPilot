import pytest
from django.contrib.auth.models import User

from accounts.forms import PasswordSetupForm


@pytest.mark.parametrize(
    "password",
    [
        "short1",
        "password123",
        "alice2026",
        "12345678",
    ],
)
def test_password_policy_rejects_weak_passwords(password):
    user = User(username="alice", email="alice@example.com")
    form = PasswordSetupForm(
        {"password1": password, "password2": password},
        user=user,
    )

    assert not form.is_valid()
    assert "password1" in form.errors


def test_password_policy_accepts_a_strong_password():
    user = User(username="alice", email="alice@example.com")
    form = PasswordSetupForm(
        {"password1": "AlpineRiver829", "password2": "AlpineRiver829"},
        user=user,
    )

    assert form.is_valid()
