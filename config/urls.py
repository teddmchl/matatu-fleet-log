"""
ROOT URLCONF (config/urls.py)

  /admin/     Django admin (superusers)
  /accounts/  Django's built-in auth views: login/, logout/, password_change/ ...
  /           everything else is handled by the fleet app
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("fleet.urls")),
]
