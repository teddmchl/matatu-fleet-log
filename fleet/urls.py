# ==============================================================================
# APP URLCONF (fleet/urls.py)
# ==============================================================================
# Role in MVT:
#   Routes requests delegated from config/urls.py to the appropriate view function.
#
# Request Flow Step 2:
#   1. Handed the empty path "" from root URLconf.
#   2. Matches path("", views.home, name="home").
#   3. Calls views.home(request).
#
# Key Concepts for Lecturer:
#   - app_name = "fleet": Creates an application namespace. In templates, we can
#     use {% url 'fleet:home' %} instead of hardcoding "/". This prevents route
#     collisions when multiple apps exist.
# ==============================================================================

from django.urls import path

from . import views

# Application namespace for reverse URL resolution
app_name = "fleet"

urlpatterns = [
    # Maps the landing page route ("") to the home view function
    path("", views.home, name="home"),
]

