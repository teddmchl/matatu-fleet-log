# ==============================================================================
# ADMIN (fleet/admin.py)
# ==============================================================================
# Registers the models so a superuser can manage them at /admin/.
# list_display = columns, search_fields = search box, list_filter = sidebar filters.
# ==============================================================================

from django.contrib import admin

from .models import DailyReturn, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate", "route", "capacity", "status", "owner")
    search_fields = ("plate", "route", "owner__username")
    list_filter = ("status",)


@admin.register(DailyReturn)
class DailyReturnAdmin(admin.ModelAdmin):
    list_display = ("date", "vehicle", "trips", "collections", "fuel", "other_expenses", "net", "recorded_by")
    search_fields = ("vehicle__plate",)
    list_filter = ("date", "vehicle")
    date_hierarchy = "date"
