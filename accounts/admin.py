# ==============================================================================
# ADMIN (accounts/admin.py)
# ==============================================================================
# Registers Profile so a superuser can promote a user to SACCO admin at /admin/.
# ==============================================================================

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")
