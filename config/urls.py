"""
ROOT URLCONF (config/urls.py)

  /admin/     Django admin (superusers)
  /accounts/  accounts app (signup/, profile/) + Django's built-in auth views
              (login/, logout/, password_change/ ...)
  /reports/   reports app: per-vehicle totals
  /           fleet app: vehicles and daily returns
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("reports/", include("reports.urls")),
    path("", include("fleet.urls")),
]
