# ==============================================================================
# FORMS (accounts/forms.py)
# ==============================================================================
#   SignUpForm - extends Django's UserCreationForm (hashes the password and runs
#                the password validators) and adds a required email.
# ==============================================================================

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email"]
