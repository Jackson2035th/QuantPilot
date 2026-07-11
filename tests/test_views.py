from django.contrib.auth.models import User
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_user_can_register_and_is_redirected_to_dashboard(client):
    response = client.post(
        reverse("register"),
        {
            "username": "alice",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard")
    assert User.objects.filter(username="alice").exists()
