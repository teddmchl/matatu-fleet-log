# ==============================================================================
# FORMS (fleet/forms.py)
# ==============================================================================
#   VehicleForm     - ModelForm; clean_plate() normalises the plate and limits
#                     the optional driver dropdown to users with the driver role
#   DailyReturnForm - ModelForm; offers only the active vehicles the user is
#                     allowed to log against (own vehicles for owners, assigned
#                     vehicles for drivers), blocks future dates, checks totals
# ==============================================================================

import re

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import Profile
from accounts.roles import loggable_vehicles_for

from .models import DailyReturn, Vehicle

# Kenyan plates: KAA 123A style (3 letters, 3 digits, optional letter)
PLATE_PATTERN = re.compile(r"^K[A-Z]{2}\d{3}[A-Z]?$")


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["plate", "route", "capacity", "status", "driver"]
        widgets = {
            "plate": forms.TextInput(attrs={"placeholder": "KDA 123A"}),
            "route": forms.TextInput(attrs={"placeholder": "46 Kawangware - Town"}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["driver"].queryset = User.objects.filter(
            profile__role=Profile.ROLE_DRIVER
        ).order_by("username")
        self.fields["driver"].required = False
        self.fields["driver"].empty_label = "Unassigned"

    def clean_plate(self) -> str:
        plate = self.cleaned_data["plate"].upper().replace(" ", "")
        if not PLATE_PATTERN.match(plate):
            raise forms.ValidationError("Enter a Kenyan plate like KDA 123A.")
        return f"{plate[:3]} {plate[3:]}"


class DailyReturnForm(forms.ModelForm):
    class Meta:
        model = DailyReturn
        fields = ["vehicle", "date", "trips", "collections", "fuel", "other_expenses", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "collections": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "fuel": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "other_expenses": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user: User, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Owners can pick their own active vehicles; drivers can pick active vehicles assigned to them.
        self.fields["vehicle"].queryset = loggable_vehicles_for(user)

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > timezone.localdate():
            raise forms.ValidationError("You can't log a return for a future date.")
        return date

    def clean(self):
        cleaned = super().clean()
        for field in ("collections", "fuel", "other_expenses"):
            value = cleaned.get(field)
            if value is not None and value < 0:
                self.add_error(field, "Amounts can't be negative.")
        if cleaned.get("trips") == 0 and (cleaned.get("collections") or 0) > 0:
            self.add_error("trips", "You recorded collections but zero trips.")
        return cleaned
