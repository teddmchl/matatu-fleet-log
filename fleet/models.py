# ==============================================================================
# APP MODELS (fleet/models.py)
# ==============================================================================
# Two tables in the fleet app, linked to Django's built-in User (and accounts.Profile):
#
#   User (owner) 1 ──< Vehicle 1 ──< DailyReturn >── 1 User (recorded_by)
#                         │
#                         └──> 0..1 User (driver)
#
#   - Vehicle.owner       ForeignKey -> User   (an owner can have many matatus)
#   - Vehicle.driver      ForeignKey -> User   (optional driver assigned by the owner)
#   - DailyReturn.vehicle ForeignKey -> Vehicle (a matatu has one return per day)
#   - DailyReturn.recorded_by ForeignKey -> User (who logged it)
# ==============================================================================

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse


class Vehicle(models.Model):
    """A matatu registered by an owner, optionally assigned to a driver."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("garage", "In the garage"),
        ("retired", "Retired"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # delete the owner -> their vehicles go too
        related_name="vehicles",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # delete the driver -> vehicle stays, becomes unassigned
        null=True,
        blank=True,
        related_name="assigned_vehicles",
        limit_choices_to={"profile__role": "driver"},
    )
    plate = models.CharField("number plate", max_length=10, unique=True)
    route = models.CharField(max_length=60, help_text="e.g. 46 Kawangware - Town")
    capacity = models.PositiveSmallIntegerField(default=14)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["plate"]

    def __str__(self):
        return f"{self.plate} ({self.route})"


class DailyReturn(models.Model):
    """What one vehicle collected and spent on one day."""

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="returns",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # keep the audit trail: can't delete a user who logged returns
        related_name="returns_recorded",
    )
    date = models.DateField()
    trips = models.PositiveSmallIntegerField(default=0)
    collections = models.DecimalField(max_digits=9, decimal_places=2, help_text="Fares collected (KES)")
    fuel = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0"))
    other_expenses = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=Decimal("0"),
        help_text="SACCO fee, parking, repairs (KES)",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "vehicle__plate"]
        constraints = [
            models.UniqueConstraint(fields=["vehicle", "date"], name="one_return_per_vehicle_per_day"),
        ]

    def __str__(self):
        return f"{self.vehicle.plate} on {self.date}"

    @property
    def net(self):
        """Collections minus all expenses."""
        return self.collections - self.fuel - self.other_expenses

    def get_absolute_url(self):
        return reverse("fleet:return_edit", args=[self.pk])
