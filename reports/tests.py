"""Reports app tests: per-vehicle totals and access control."""

import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from fleet.models import DailyReturn, Vehicle


class ReportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("wanjiku", password="strong-pass-123")
        other = User.objects.create_user("otieno", password="strong-pass-123")
        self.vehicle = Vehicle.objects.create(owner=self.owner, plate="KDA 123A", route="46")
        Vehicle.objects.create(owner=other, plate="KCB 999B", route="111")
        today = timezone.localdate()
        for days_ago, collections in ((0, "9000"), (1, "8000"), (40, "5000")):
            DailyReturn.objects.create(
                vehicle=self.vehicle, recorded_by=self.owner,
                date=today - datetime.timedelta(days=days_ago), trips=8,
                collections=Decimal(collections), fuel=Decimal("3000"), other_expenses=Decimal("500"),
            )
        self.client.force_login(self.owner)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("reports:summary"))
        self.assertEqual(response.status_code, 302)

    def test_last_30_days_totals(self):
        response = self.client.get(reverse("reports:summary"), {"period": "30"})
        [row] = response.context["vehicles"]
        self.assertEqual(row.days_logged, 2)
        self.assertEqual(row.collections, Decimal("17000"))
        self.assertEqual(row.net, Decimal("10000"))

    def test_all_time_and_only_own_vehicles(self):
        response = self.client.get(reverse("reports:summary"), {"period": "all"})
        rows = list(response.context["vehicles"])
        self.assertEqual([r.plate for r in rows], ["KDA 123A"])
        self.assertEqual(rows[0].days_logged, 3)
        self.assertEqual(response.context["totals"]["net"], Decimal("11500"))
