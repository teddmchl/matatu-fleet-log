# ==============================================================================
# JSON API (fleet/api.py)
# ==============================================================================
# Small read/write API on top of the same models, built with JsonResponse:
#
#   GET  /api/csrf/            -> {"csrfToken": "..."} (also sets the csrftoken cookie)
#   GET  /api/vehicles/        -> vehicles visible to your role (own / assigned / all)
#   GET  /api/vehicles/<id>/   -> one visible vehicle (404 if outside your scope)
#   GET  /api/returns/         -> daily returns visible to your role, optional ?vehicle=<id>&date=YYYY-MM-DD
#   POST /api/returns/         -> create a daily return from a JSON body (owners and drivers; 403 for SACCO admin)
#
# Authentication: the API uses the normal login session. Anonymous requests get
#   a 401 JSON error instead of a redirect to the HTML login page.
# Authorisation: uses vehicles_for(user), returns_for(user) and can_add_return(user)
#   from accounts/roles.py, matching the HTML views.
# CSRF: POST is still CSRF-protected (no csrf_exempt). A client sends the token
#   from /api/csrf/ in the X-CSRFToken header, the same check the HTML forms pass.
# Validation: POST data goes through DailyReturnForm, so the API enforces exactly
#   the same rules as the web form (allowed vehicles only, no future dates ...).
# ==============================================================================

import json
from functools import wraps

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_http_methods

from accounts.roles import can_add_return, returns_for, vehicles_for

from .forms import DailyReturnForm
from .models import DailyReturn, Vehicle


def api_login_required(view):
    """Like @login_required, but answers 401 JSON instead of redirecting."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def vehicle_to_dict(vehicle: Vehicle) -> dict:
    return {
        "id": vehicle.pk,
        "plate": vehicle.plate,
        "route": vehicle.route,
        "capacity": vehicle.capacity,
        "status": vehicle.status,
        "driver": vehicle.driver.username if vehicle.driver_id else None,
    }


def return_to_dict(daily_return: DailyReturn) -> dict:
    # Decimals are sent as strings so no cents are lost to float rounding.
    return {
        "id": daily_return.pk,
        "vehicle": daily_return.vehicle_id,
        "plate": daily_return.vehicle.plate,
        "date": daily_return.date.isoformat(),
        "trips": daily_return.trips,
        "collections": str(daily_return.collections),
        "fuel": str(daily_return.fuel),
        "other_expenses": str(daily_return.other_expenses),
        "net": str(daily_return.net),
        "notes": daily_return.notes,
        "recorded_by": daily_return.recorded_by.username,
    }


@require_GET
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
@api_login_required
def vehicle_list(request):
    vehicles = [vehicle_to_dict(v) for v in vehicles_for(request.user).select_related("driver")]
    return JsonResponse({"vehicles": vehicles})


@require_GET
@api_login_required
def vehicle_detail(request, pk: int):
    vehicle = get_object_or_404(vehicles_for(request.user).select_related("driver"), pk=pk)
    return JsonResponse(vehicle_to_dict(vehicle))


@require_http_methods(["GET", "POST"])
@api_login_required
def return_list(request):
    if request.method == "POST":
        return create_return(request)

    returns = returns_for(request.user).select_related("vehicle", "recorded_by")

    vehicle_id = request.GET.get("vehicle")
    if vehicle_id:
        if not vehicle_id.isdigit():
            return JsonResponse({"error": "vehicle must be a number."}, status=400)
        returns = returns.filter(vehicle_id=int(vehicle_id))

    date_text = request.GET.get("date")
    if date_text:
        date = parse_date(date_text)
        if date is None:
            return JsonResponse({"error": "date must look like YYYY-MM-DD."}, status=400)
        returns = returns.filter(date=date)

    return JsonResponse({"returns": [return_to_dict(r) for r in returns]})


def create_return(request):
    if not can_add_return(request.user):
        return JsonResponse({"error": "Your role cannot log daily returns."}, status=403)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Body must be valid JSON."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Body must be a JSON object."}, status=400)

    form = DailyReturnForm(data=payload, user=request.user)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

    daily_return = form.save(commit=False)
    daily_return.recorded_by = request.user
    daily_return.save()
    daily_return.refresh_from_db()  # reload so amounts come back as stored, e.g. "9500.00"
    return JsonResponse(return_to_dict(daily_return), status=201)
