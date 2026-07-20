import pytest
from django.contrib.auth.models import User

from accounts.models import UserProfile, get_user_profile


@pytest.mark.django_db
def test_creating_user_creates_incomplete_onboarding_profile():
    user = User.objects.create_user(username="new-investor", password="StrongPass123!")

    profile = UserProfile.objects.get(user=user)

    assert profile.has_completed_onboarding is False


@pytest.mark.django_db
def test_get_user_profile_repairs_missing_profile():
    user = User.objects.create_user(username="profile-repair", password="StrongPass123!")
    UserProfile.objects.filter(user=user).delete()

    profile = get_user_profile(user)

    assert profile.user == user
    assert profile.has_completed_onboarding is False


@pytest.mark.django_db
def test_profile_has_an_optional_display_name():
    user = User.objects.create_user(username="profile-name", password="StrongPass123!")
    profile = get_user_profile(user)

    assert profile.display_name == ""
