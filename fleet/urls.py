# ==============================================================================
# APP URLCONF (fleet/urls.py)
# ==============================================================================
# app_name = "fleet" namespaces the routes: {% url 'fleet:vehicle_list' %}.
# ==============================================================================

from django.urls import path

from . import views

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
]
