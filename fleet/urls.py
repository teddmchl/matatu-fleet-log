# ==============================================================================
# APP URLCONF (fleet/urls.py)
# ==============================================================================
# app_name = "fleet" namespaces the routes: {% url 'fleet:vehicle_list' %}.
# The api/ routes return JSON instead of HTML pages.
# ==============================================================================

from django.urls import path

from . import api, views

app_name = "fleet"

urlpatterns = [
    path("", views.home, name="home"),
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("vehicles/new/", views.vehicle_new, name="vehicle_new"),
    path("vehicles/<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),
    path("vehicles/<int:pk>/delete/", views.vehicle_delete, name="vehicle_delete"),
    path("returns/", views.return_list, name="return_list"),
    path("returns/new/", views.return_new, name="return_new"),
    path("returns/<int:pk>/edit/", views.return_edit, name="return_edit"),
    path("returns/<int:pk>/delete/", views.return_delete, name="return_delete"),
    # JSON API (fleet/api.py)
    path("api/csrf/", api.csrf, name="api_csrf"),
    path("api/vehicles/", api.vehicle_list, name="api_vehicle_list"),
    path("api/vehicles/<int:pk>/", api.vehicle_detail, name="api_vehicle_detail"),
    path("api/returns/", api.return_list, name="api_return_list"),
]
