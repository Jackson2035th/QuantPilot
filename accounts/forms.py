from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .throttling import clear_login_failures, login_is_locked, record_failed_login


class ProfileForm(forms.Form):
    display_name = forms.CharField(max_length=80, required=False)

    def clean_display_name(self):
        return self.cleaned_data["display_name"].strip()


class RegistrationUsernameForm(forms.Form):
    username = forms.CharField(min_length=3, max_length=150)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already in use.")
        return username


class EmailAddressForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        return self.cleaned_data["email"].lower()


class RegistrationEmailForm(EmailAddressForm):
    def clean_email(self):
        email = super().clean_email()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("That email address is already in use.")
        return email


class VerificationCodeForm(forms.Form):
    code = forms.RegexField(r"^\d{6}$", error_messages={"invalid": "Enter the six-digit code."})


class PasswordSetupForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, min_length=8, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        errors = []
        try:
            validate_password(password, self.user)
        except ValidationError as exc:
            errors.extend(exc.messages)

        if not any(character.isalpha() for character in password) or not any(
            character.isdigit() for character in password
        ):
            errors.append("Use at least one letter and one number.")
        if errors:
            raise forms.ValidationError(errors)
        return password

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") and cleaned_data.get("password2"):
            if cleaned_data["password1"] != cleaned_data["password2"]:
                self.add_error("password2", "The passwords do not match.")
        return cleaned_data


class AccountDeletionForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label="Current password")


class RateLimitedAuthenticationForm(AuthenticationForm):
    lock_message = "Too many failed login attempts. Please wait 5 minutes and try again."

    def clean(self):
        if self.request and login_is_locked(self.request):
            raise forms.ValidationError(self.lock_message, code="login_locked")

        try:
            cleaned_data = super().clean()
        except forms.ValidationError:
            if self.request and record_failed_login(self.request):
                raise forms.ValidationError(self.lock_message, code="login_locked")
            raise

        if self.request:
            clear_login_failures(self.request)
        return cleaned_data
