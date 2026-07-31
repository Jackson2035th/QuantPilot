from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    # Django calls this function automatically after a new User is saved.
    if created:
        UserProfile.objects.create(user=instance)
