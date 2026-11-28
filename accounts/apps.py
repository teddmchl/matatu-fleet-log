# ==============================================================================
# APP CONFIGURATION (accounts/apps.py)
# ==============================================================================
# The accounts app owns everything about who the user is: sign-up, the
# login/logout templates, the Profile model (user roles) and the profile page
# that shows the current session.
# ==============================================================================

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
