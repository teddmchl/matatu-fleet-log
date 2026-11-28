# ==============================================================================
# FORMS (accounts/forms.py)
# ==============================================================================
#   SignUpForm - extends Django's UserCreationForm (hashes the password and runs
#                the password validators), adds a required email, and lets the
#                new user register as an Owner or a Driver (never SACCO admin).
# ==============================================================================

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile
from .roles import get_profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=Profile.SIGNUP_ROLE_CHOICES,
        initial=Profile.ROLE_OWNER,
        required=False,
        help_text="SACCO admin accounts are assigned by an administrator.",
    )

    class Meta:
        model = User
        fields = ["username", "email", "role"]

    def clean_role(self) -> str:
        return self.cleaned_data.get("role") or Profile.ROLE_OWNER

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=commit)
        if commit:
            profile = get_profile(user)
            profile.role = self.cleaned_data["role"]
            profile.save()
        return user
