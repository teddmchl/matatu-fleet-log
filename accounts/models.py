# ==============================================================================
# APP MODELS (accounts/models.py)
# ==============================================================================
# Profile extends Django's built-in User with a role (OneToOneField):
#   - owner        registers their own matatus and reviews per-vehicle totals
#   - driver       logs daily returns for vehicles assigned to them
#   - sacco_admin  read-only view of the whole fleet across all owners
#
# Every User gets a Profile automatically through a post_save signal (defaulting
# to "owner"). Sign-up only offers "owner" or "driver"; "sacco_admin" is granted
# exclusively through Django admin so strangers cannot escalate their own role.
# ==============================================================================

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    """Stores the user's role in the matatu SACCO."""

    ROLE_OWNER = "owner"
    ROLE_DRIVER = "driver"
    ROLE_SACCO_ADMIN = "sacco_admin"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_DRIVER, "Driver"),
        (ROLE_SACCO_ADMIN, "SACCO admin"),
    ]

    # Public sign-up choices exclude sacco_admin.
    SIGNUP_ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_DRIVER, "Driver"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_OWNER,
    )

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Ensure every newly created User has a Profile row."""
    if created:
        Profile.objects.get_or_create(user=instance)
