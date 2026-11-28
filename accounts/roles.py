# ==============================================================================
# ROLES & AUTHORISATION HELPERS (accounts/roles.py)
# ==============================================================================
# Centralises role checks and queryset scoping so every HTML view, form and JSON
# API endpoint applies the exact same rules:
#
#   Action                     | owner        | driver                      | sacco_admin
#   ---------------------------+--------------+-----------------------------+----------------
#   See vehicles               | own          | assigned to them            | all (read-only)
#   Add/edit/delete vehicle    | own          | forbidden (403)             | forbidden (403)
#   See daily returns          | own vehicles | assigned vehicles           | all (read-only)
#   Add daily return           | own vehicles | assigned vehicles only      | forbidden (403)
#   Edit/delete daily return   | own vehicles | recorded by them, same day  | forbidden (403)
#   Reports summary            | own fleet    | forbidden (403)             | whole fleet
# ==============================================================================

from django.utils import timezone

from fleet.models import DailyReturn, Vehicle

from .models import Profile


def get_profile(user) -> Profile:
    """Return the user's Profile, creating a default owner profile if missing."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def role_of(user) -> str:
    """Return the role code ('owner', 'driver', 'sacco_admin') or '' if anonymous."""
    if not getattr(user, "is_authenticated", False):
        return ""
    return get_profile(user).role


def is_owner(user) -> bool:
    return role_of(user) == Profile.ROLE_OWNER


def is_driver(user) -> bool:
    return role_of(user) == Profile.ROLE_DRIVER


def is_sacco_admin(user) -> bool:
    return role_of(user) == Profile.ROLE_SACCO_ADMIN


def vehicles_for(user):
    """Vehicles this user is allowed to view."""
    if not getattr(user, "is_authenticated", False):
        return Vehicle.objects.none()
    if is_sacco_admin(user):
        return Vehicle.objects.all()
    if is_driver(user):
        return Vehicle.objects.filter(driver=user)
    return Vehicle.objects.filter(owner=user)


def loggable_vehicles_for(user):
    """Active vehicles this user may pick when logging a daily return."""
    if not getattr(user, "is_authenticated", False) or is_sacco_admin(user):
        return Vehicle.objects.none()
    return vehicles_for(user).filter(status="active")


def returns_for(user):
    """Daily returns this user is allowed to view."""
    if not getattr(user, "is_authenticated", False):
        return DailyReturn.objects.none()
    if is_sacco_admin(user):
        return DailyReturn.objects.all()
    if is_driver(user):
        return DailyReturn.objects.filter(vehicle__driver=user)
    return DailyReturn.objects.filter(vehicle__owner=user)


def can_manage_vehicles(user) -> bool:
    """Only matatu owners can add, edit or delete vehicles."""
    return is_owner(user)


def can_add_return(user) -> bool:
    """Owners and drivers log returns; SACCO admins have read-only access."""
    return is_owner(user) or is_driver(user)


def can_modify_return(user, daily_return: DailyReturn) -> bool:
    """
    Owners can edit or delete any return on their own vehicles.
    Drivers can only edit or delete returns they recorded themselves on the same day
    for a vehicle currently assigned to them.
    SACCO admins cannot modify returns.
    """
    if is_owner(user):
        return daily_return.vehicle.owner_id == user.id
    if is_driver(user):
        return (
            daily_return.vehicle.driver_id == user.id
            and daily_return.recorded_by_id == user.id
            and daily_return.date == timezone.localdate()
        )
    return False


def role_context(request) -> dict:
    """Template context processor exposing the logged-in user's role."""
    if not request.user.is_authenticated:
        return {}
    profile = get_profile(request.user)
    return {
        "user_role": profile.role,
        "user_role_label": profile.get_role_display(),
        "is_owner": profile.role == Profile.ROLE_OWNER,
        "is_driver": profile.role == Profile.ROLE_DRIVER,
        "is_sacco_admin": profile.role == Profile.ROLE_SACCO_ADMIN,
    }
