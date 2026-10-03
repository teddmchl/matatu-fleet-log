from django.shortcuts import render


def home(request):
    """Landing page for the fleet daily-returns log."""
    return render(request, "fleet/home.html")
