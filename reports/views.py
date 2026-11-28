# ==============================================================================
# APP VIEWS (reports/views.py)
# ==============================================================================
# summary() totals vehicles over a period using the ORM's aggregation
# (annotate + Sum) instead of looping in Python.
#   - owners see totals for their own fleet
#   - SACCO admins see totals across the whole fleet
#   - drivers receive 403 (HttpResponseForbidden)
# ==============================================================================

import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from accounts.roles import can_view_reports, vehicles_for

PERIODS = {"7": 7, "30": 30, "all": None}
ZERO = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))


@login_required
def summary(request):
    if not can_view_reports(request.user):
        return HttpResponseForbidden("Fleet reports are only available to vehicle owners and SACCO admins.")

    period = request.GET.get("period", "30")
    if period not in PERIODS:
        period = "30"
    days = PERIODS[period]

    in_period = Q()
    if days is not None:
        since = timezone.localdate() - datetime.timedelta(days=days - 1)
        in_period = Q(returns__date__gte=since)

    vehicles = (
        vehicles_for(request.user)
        .select_related("owner", "driver")
        .annotate(
            days_logged=Count("returns", filter=in_period),
            trips=Coalesce(Sum("returns__trips", filter=in_period), 0),
            collections=Coalesce(Sum("returns__collections", filter=in_period), ZERO),
            expenses=Coalesce(
                Sum(F("returns__fuel") + F("returns__other_expenses"), filter=in_period), ZERO
            ),
        )
        .annotate(net=F("collections") - F("expenses"))
        .order_by("-net")
    )
    totals = {
        "collections": sum(v.collections for v in vehicles),
        "expenses": sum(v.expenses for v in vehicles),
        "net": sum(v.net for v in vehicles),
    }
    return render(
        request,
        "reports/summary.html",
        {"vehicles": vehicles, "totals": totals, "period": period},
    )
