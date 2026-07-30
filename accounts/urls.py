from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .forms import RateLimitedAuthenticationForm

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=RateLimitedAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("register/email/", views.register_email, name="register_email"),
    path("register/verify/", views.register_verify, name="register_verify"),
    path("register/password/", views.register_password, name="register_password"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/verify/", views.password_reset_verify, name="password_reset_verify"),
    path("password-reset/confirm/", views.password_reset_confirm, name="password_reset_confirm"),
    path("profile/", views.profile, name="profile"),
    path("restart-onboarding/", views.restart_onboarding, name="restart_onboarding"),
    path("delete-account/", views.delete_account, name="delete_account"),
]
