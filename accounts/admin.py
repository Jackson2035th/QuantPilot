from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "has_completed_onboarding")
    list_filter = ("has_completed_onboarding",)
