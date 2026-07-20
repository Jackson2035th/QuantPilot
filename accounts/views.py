from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render

from backtests.models import BacktestRun

from .forms import (
    PasswordSetupForm,
    AccountDeletionForm,
    EmailAddressForm,
    ProfileForm,
    RegistrationEmailForm,
    RegistrationUsernameForm,
    VerificationCodeForm,
)
from .models import get_user_profile
from .verification import clear_email_code, send_email_code, verify_email_code


def _render_password_setup(request, form, title):
    return render(request, "accounts/set_password.html", {"form": form, "title": title})


def register(request):
    if request.method == "POST":
        form = RegistrationUsernameForm(request.POST)
        if form.is_valid():
            request.session["registration_username"] = form.cleaned_data["username"]
            clear_email_code(request.session, "registration")
            request.session.pop("registration_email", None)
            return redirect("register_email")
    else:
        form = RegistrationUsernameForm()
    return render(request, "accounts/register.html", {"form": form})


def register_email(request):
    if not request.session.get("registration_username"):
        return redirect("register")
    if request.method == "POST":
        form = RegistrationEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            request.session["registration_email"] = email
            send_email_code(request.session, "registration", email)
            return redirect("register_verify")
    else:
        form = RegistrationEmailForm(initial={"email": request.session.get("registration_email", "")})
    return render(request, "accounts/register_email.html", {"form": form})


def register_verify(request):
    if not request.session.get("registration_username") or not request.session.get("registration_email"):
        return redirect("register")
    if request.method == "POST":
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            verified_email = verify_email_code(request.session, "registration", form.cleaned_data["code"])
            if verified_email == request.session["registration_email"]:
                request.session["registration_verified"] = True
                return redirect("register_password")
            form.add_error("code", "That code is invalid or has expired.")
    else:
        form = VerificationCodeForm()
    return render(request, "accounts/verify_code.html", {"form": form, "email": request.session["registration_email"], "flow": "registration"})


def register_password(request):
    username = request.session.get("registration_username")
    email = request.session.get("registration_email")
    if not username or not email or not request.session.get("registration_verified"):
        return redirect("register")
    if request.method == "POST":
        form = PasswordSetupForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = get_user_model().objects.create_user(
                        username=username, email=email, password=form.cleaned_data["password1"]
                    )
            except IntegrityError:
                messages.error(request, "That username or email address is no longer available. Please start again.")
                return redirect("register")
            for key in ("registration_username", "registration_email", "registration_verified"):
                request.session.pop(key, None)
            clear_email_code(request.session, "registration")
            login(request, user)
            return redirect("dashboard")
    else:
        form = PasswordSetupForm()
    return _render_password_setup(request, form, "Set your password")


def password_reset_request(request):
    if request.method == "POST":
        form = EmailAddressForm(request.POST)
        if form.is_valid():
            user = get_user_model().objects.filter(email__iexact=form.cleaned_data["email"]).first()
            if user:
                send_email_code(request.session, "password_reset", user.email)
            else:
                clear_email_code(request.session, "password_reset")
            request.session["password_reset_requested"] = True
            messages.success(request, "If an account uses that email address, a verification code has been sent.")
            return redirect("password_reset_verify")
    else:
        form = EmailAddressForm()
    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_verify(request):
    if not request.session.get("password_reset_requested"):
        return redirect("password_reset_request")
    if request.method == "POST":
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            verified_email = verify_email_code(request.session, "password_reset", form.cleaned_data["code"])
            if verified_email:
                request.session["password_reset_email"] = verified_email
                return redirect("password_reset_confirm")
            form.add_error("code", "That code is invalid or has expired.")
    else:
        form = VerificationCodeForm()
    return render(request, "accounts/verify_code.html", {"form": form, "email": "your email address", "flow": "password reset"})


def password_reset_confirm(request):
    email = request.session.get("password_reset_email")
    if not email:
        return redirect("password_reset_request")
    if request.method == "POST":
        form = PasswordSetupForm(request.POST)
        if form.is_valid():
            user = get_user_model().objects.get(email__iexact=email)
            user.set_password(form.cleaned_data["password1"])
            user.save(update_fields=["password"])
            for key in ("password_reset_requested", "password_reset_email"):
                request.session.pop(key, None)
            clear_email_code(request.session, "password_reset")
            messages.success(request, "Your password has been reset. You can now log in.")
            return redirect("login")
    else:
        form = PasswordSetupForm()
    return _render_password_setup(request, form, "Choose a new password")


@login_required
def profile(request):
    user_profile = get_user_profile(request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            user_profile.display_name = form.cleaned_data["display_name"]
            user_profile.save(update_fields=["display_name"])
            return redirect("profile")
    else:
        form = ProfileForm(initial={"display_name": user_profile.display_name})

    completed_runs = BacktestRun.objects.filter(user=request.user, status="completed")
    latest_run = completed_runs.order_by("-completed_at", "-id").first()
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "profile": user_profile,
            "completed_backtest_count": completed_runs.count(),
            "latest_run": latest_run,
        },
    )


@login_required
@require_POST
def restart_onboarding(request):
    user_profile = get_user_profile(request.user)
    user_profile.has_completed_onboarding = False
    user_profile.save(update_fields=["has_completed_onboarding"])
    return redirect("dashboard")


@login_required
@require_POST
def delete_account(request):
    form = AccountDeletionForm(request.POST)
    if not form.is_valid() or not request.user.check_password(form.cleaned_data["password"]):
        messages.error(request, "Your current password was incorrect. Your account was not deleted.")
        return redirect("profile")

    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your account and all associated data have been permanently deleted.")
    return redirect("login")
