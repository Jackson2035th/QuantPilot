from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=80, blank=True)
    has_completed_onboarding = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} profile"


def get_user_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile
