# ==============================================================================
# APP VIEWS (accounts/views.py)
# ==============================================================================
# Authentication:
#   - login/logout use Django's built-in LoginView/LogoutView (config/urls.py)
#   - signup() creates the user and their role profile, then login() starts
#     their session
#
# Sessions:
#   - profile() reads request.session to show when this session expires and
#     what the app has stored in it
# ==============================================================================

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignUpForm
from .roles import get_profile, is_driver


def signup(request):
    if request.user.is_authenticated:
        return redirect("fleet:home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # creates the session and sets the session cookie
            if is_driver(user):
                messages.success(request, f"Welcome, {user.username}. Log returns for your assigned vehicles.")
                return redirect("fleet:home")
            messages.success(request, f"Welcome, {user.username}. Add your first vehicle.")
            return redirect("fleet:vehicle_new")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def profile(request):
    session = request.session
    user_profile = get_profile(request.user)
    context = {
        "role_label": user_profile.get_role_display(),
        "session_expires": session.get_expiry_date(),
        "expires_at_browser_close": session.get_expire_at_browser_close(),
        "last_vehicle_id": session.get("last_vehicle_id"),
    }
    return render(request, "accounts/profile.html", context)
