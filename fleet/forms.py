# ==============================================================================
# FORMS (fleet/forms.py)
# ==============================================================================
#   VehicleForm     - ModelForm; clean_plate() normalises the plate
#   DailyReturnForm - ModelForm; only offers the user's own vehicles,
#                     clean_date() blocks future dates, clean() checks totals
# ==============================================================================

import re

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import DailyReturn, Vehicle

# Kenyan plates: KAA 123A style (3 letters, 3 digits, optional letter)
PLATE_PATTERN = re.compile(r"^K[A-Z]{2}\d{3}[A-Z]?$")


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["plate", "route", "capacity", "status"]
        widgets = {
            "plate": forms.TextInput(attrs={"placeholder": "KDA 123A"}),
            "route": forms.TextInput(attrs={"placeholder": "46 Kawangware - Town"}),
        }

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
        # A user can only log returns against vehicles they own.
        self.fields["vehicle"].queryset = Vehicle.objects.filter(owner=user, status="active")

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
