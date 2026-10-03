# ==============================================================================
# APP CONFIGURATION (fleet/apps.py)
# ==============================================================================
# Role:
#   Configures application metadata. Django loads FleetConfig when 'fleet'
#   is listed in INSTALLED_APPS in config/settings.py.
# ==============================================================================

from django.apps import AppConfig


class FleetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fleet'

