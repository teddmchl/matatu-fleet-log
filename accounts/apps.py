# ==============================================================================
# APP CONFIGURATION (accounts/apps.py)
# ==============================================================================
# The accounts app owns everything about who the user is: sign-up, the
# login/logout templates and the profile page that shows the current session.
# It has no models of its own; it uses Django's built-in User.
# ==============================================================================

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
