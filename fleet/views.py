# ==============================================================================
# APP VIEWS (fleet/views.py)
# ==============================================================================
# Role in MVT:
#   The 'V' (View) in Django's Model-View-Template architecture.
#   A view is a Python callable that takes an HttpRequest object and returns an
#   HttpResponse object (rendered HTML, JSON, redirect, or 404).
#
# Request Flow Step 3:
#   1. fleet/urls.py routes the request here: home(request).
#   2. render() takes the request, locates "fleet/home.html" using Django's
#      template loaders, compiles the context, and returns an HttpResponse (200 OK).
#   3. In later weeks, this view will query models (e.g. DailyReturn, Vehicle)
#      and pass querysets into the template context dictionary.
# ==============================================================================

from django.shortcuts import render


def home(request):
    """
    Landing page for the fleet daily-returns log.
    Renders the app-level template fleet/templates/fleet/home.html.
    """
    return render(request, "fleet/home.html")

