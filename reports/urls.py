# ==============================================================================
# APP URLCONF (reports/urls.py)
# ==============================================================================

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.summary, name="summary"),
]
