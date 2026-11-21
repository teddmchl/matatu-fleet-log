# ==============================================================================
# APP URLCONF (accounts/urls.py)
# ==============================================================================
# Mounted at /accounts/ next to django.contrib.auth.urls (login/, logout/ ...).
# ==============================================================================

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("profile/", views.profile, name="profile"),
]
