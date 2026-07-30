import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
@override_settings(AUTH_LOGIN_MAX_FAILURES=3, AUTH_LOGIN_LOCK_SECONDS=300)
def test_repeated_login_failures_temporarily_block_the_correct_password(
    client, django_user_model
):
    django_user_model.objects.create_user(username="locked-user", password="StrongPass123!")

    for _ in range(2):
        response = client.post(
            reverse("login"),
            {"username": "locked-user", "password": "wrong-password"},
        )
        assert response.status_code == 200

    response = client.post(
        reverse("login"),
        {"username": "locked-user", "password": "wrong-password"},
    )
    assert b"Too many failed login attempts" in response.content

    response = client.post(
        reverse("login"),
        {"username": "locked-user", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    assert b"Too many failed login attempts" in response.content
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@override_settings(AUTH_LOGIN_MAX_FAILURES=3, AUTH_LOGIN_LOCK_SECONDS=300)
def test_successful_login_clears_previous_failures(client, django_user_model):
    django_user_model.objects.create_user(username="retry-user", password="StrongPass123!")

    for _ in range(2):
        client.post(
            reverse("login"),
            {"username": "retry-user", "password": "wrong-password"},
        )

    response = client.post(
        reverse("login"),
        {"username": "retry-user", "password": "StrongPass123!"},
    )

    assert response.status_code == 302
    assert "_auth_user_id" in client.session
