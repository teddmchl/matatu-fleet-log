# ==============================================================================
# APP VIEWS (fleet/views.py)
# ==============================================================================
# Authentication:
#   - sign-up, login and logout live in the accounts app
#   - @login_required sends anonymous users to settings.LOGIN_URL
#
# Authorisation (Week 8 — roles in accounts/roles.py):
#   - every query goes through vehicles_for(request.user) / returns_for(request.user)
#   - owners see and manage their own vehicles and returns
#   - drivers see their assigned vehicles, log returns for them, and can edit or
#     delete only returns they recorded themselves on the same day
#   - SACCO admins see all vehicles and returns across the fleet (read-only)
#   - actions a role is not allowed to perform return 403 (HttpResponseForbidden);
#     records outside a user's queryset return 404 (get_object_or_404)
#
# Deleting:
#   - the delete views show a confirm page on GET and only delete on POST, so a
#     link (or a crawler following one) can never remove data by itself
#
# Sessions:
#   - request.session["last_vehicle_id"] remembers the vehicle you last logged,
#     so the next "new return" form starts on it
# ==============================================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.roles import (
    can_add_return,
    can_manage_vehicles,
    can_modify_return,
    returns_for,
    vehicles_for,
)

from .forms import DailyReturnForm, VehicleForm
from .models import Vehicle

LAST_VEHICLE_KEY = "last_vehicle_id"


def home(request):
    """Public landing page; shows role-scoped totals once you are logged in."""
    context = {}
    if request.user.is_authenticated:
        vehicles = vehicles_for(request.user)
        returns = returns_for(request.user)
        context = {
            "vehicle_count": vehicles.count(),
            "return_count": returns.count(),
            "total_collections": returns.aggregate(total=Sum("collections"))["total"] or 0,
        }
    return render(request, "fleet/home.html", context)


@login_required
def vehicle_list(request):
    vehicles = vehicles_for(request.user).select_related("owner", "driver")
    return render(request, "fleet/vehicle_list.html", {"vehicles": vehicles})


@login_required
def vehicle_new(request):
    if not can_manage_vehicles(request.user):
        return HttpResponseForbidden("Only matatu owners can add vehicles.")
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user  # set server-side, never from the form
            vehicle.save()
            messages.success(request, f"{vehicle.plate} added.")
            return redirect("fleet:vehicle_list")
    else:
        form = VehicleForm()
    return render(request, "fleet/form.html", {"form": form, "title": "Add a vehicle"})


@login_required
def vehicle_edit(request, pk: int):
    if not can_manage_vehicles(request.user):
        return HttpResponseForbidden("Only matatu owners can edit vehicles.")
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    form = VehicleForm(request.POST or None, instance=vehicle)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{vehicle.plate} updated.")
        return redirect("fleet:vehicle_list")
    return render(request, "fleet/form.html", {"form": form, "title": f"Edit {vehicle.plate}"})


@login_required
def vehicle_delete(request, pk: int):
    if not can_manage_vehicles(request.user):
        return HttpResponseForbidden("Only matatu owners can delete vehicles.")
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    if request.method == "POST":
        plate = vehicle.plate
        vehicle.delete()  # its daily returns go too (on_delete=CASCADE)
        messages.success(request, f"{plate} deleted.")
        return redirect("fleet:vehicle_list")
    context = {
        "object": vehicle,
        "warning": f"This also deletes its {vehicle.returns.count()} daily return(s).",
        "cancel_url": "fleet:vehicle_list",
    }
    return render(request, "fleet/confirm_delete.html", context)


@login_required
def return_list(request):
    returns = returns_for(request.user).select_related("vehicle", "recorded_by")
    editable_ids = {r.pk for r in returns if can_modify_return(request.user, r)}
    return render(
        request,
        "fleet/return_list.html",
        {"returns": returns, "editable_ids": editable_ids},
    )


@login_required
def return_new(request):
    if not can_add_return(request.user):
        return HttpResponseForbidden("SACCO admins have read-only access.")
    if request.method == "POST":
        form = DailyReturnForm(request.POST, user=request.user)
        if form.is_valid():
            daily_return = form.save(commit=False)
            daily_return.recorded_by = request.user
            daily_return.save()
            request.session[LAST_VEHICLE_KEY] = daily_return.vehicle_id
            messages.success(request, f"Return for {daily_return} saved. Net KES {daily_return.net:,.2f}.")
            return redirect("fleet:return_list")
    else:
        initial = {"vehicle": request.session.get(LAST_VEHICLE_KEY)}
        form = DailyReturnForm(user=request.user, initial=initial)
    return render(request, "fleet/form.html", {"form": form, "title": "Log a daily return"})


@login_required
def return_edit(request, pk: int):
    if not can_add_return(request.user):
        return HttpResponseForbidden("SACCO admins have read-only access.")
    daily_return = get_object_or_404(returns_for(request.user).select_related("vehicle"), pk=pk)
    if not can_modify_return(request.user, daily_return):
        return HttpResponseForbidden("Drivers can only edit returns they recorded today.")
    form = DailyReturnForm(request.POST or None, instance=daily_return, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Return for {daily_return} updated.")
        return redirect("fleet:return_list")
    return render(request, "fleet/form.html", {"form": form, "title": f"Edit return: {daily_return}"})


@login_required
def return_delete(request, pk: int):
    if not can_add_return(request.user):
        return HttpResponseForbidden("SACCO admins have read-only access.")
    daily_return = get_object_or_404(returns_for(request.user).select_related("vehicle"), pk=pk)
    if not can_modify_return(request.user, daily_return):
        return HttpResponseForbidden("Drivers can only delete returns they recorded today.")
    if request.method == "POST":
        label = str(daily_return)
        daily_return.delete()
        messages.success(request, f"Return for {label} deleted.")
        return redirect("fleet:return_list")
    context = {"object": daily_return, "cancel_url": "fleet:return_list"}
    return render(request, "fleet/confirm_delete.html", context)
