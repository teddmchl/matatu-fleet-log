# ==============================================================================
# APP CONFIGURATION (reports/apps.py)
# ==============================================================================
# The reports app is read-only: it summarises the fleet app's data per vehicle.
# It has no models of its own.
# ==============================================================================

from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
