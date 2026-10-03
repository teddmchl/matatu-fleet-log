# ==============================================================================
# PROJECT ROOT URLCONF (config/urls.py)
# ==============================================================================
# Role in MVT:
#   Entry point for all incoming HTTP requests into the Django application.
#
# Request Flow Step 1:
#   1. Browser requests "GET /"
#   2. Django matches against ROOT_URLCONF ('config.urls').
#   3. 'admin/' -> routes to Django's built-in administration site.
#   4. '' (root) -> include('fleet.urls') delegates routing to the fleet app.
#
# Key Concepts for Lecturer:
#   - Why include()? Decouples application routing from project configuration.
#     The 'fleet' app remains self-contained and pluggable into any Django project.
# ==============================================================================

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Built-in Django admin interface (proves auth/sessions apps are active)
    path('admin/', admin.site.urls),

    # Delegate all root and sub-paths to the 'fleet' app URLconf
    path('', include('fleet.urls')),
]

