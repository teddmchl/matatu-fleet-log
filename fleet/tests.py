"""Fleet app tests: models, forms, access control and sessions. Run: python manage.py test"""

import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import DailyReturnForm, VehicleForm
from .models import DailyReturn, Vehicle


class FleetTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("wanjiku", password="strong-pass-123")
        self.other = User.objects.create_user("otieno", password="strong-pass-123")
        self.vehicle = Vehicle.objects.create(owner=self.owner, plate="KDA 123A", route="46 Kawangware - Town")
        self.other_vehicle = Vehicle.objects.create(owner=self.other, plate="KCB 999B", route="111 Ngong - Town")

    def return_data(self, **overrides):
        data = {
            "vehicle": self.vehicle.pk,
            "date": timezone.localdate().isoformat(),
            "trips": 8,
            "collections": "9500.00",
            "fuel": "3500.00",
            "other_expenses": "800.00",
            "notes": "",
        }
        data.update(overrides)
        return data


class ModelTests(FleetTestCase):
    def test_net_is_collections_minus_expenses(self):
        r = DailyReturn(
            vehicle=self.vehicle, recorded_by=self.owner, date=timezone.localdate(),
            collections=Decimal("9500"), fuel=Decimal("3500"), other_expenses=Decimal("800"),
        )
        self.assertEqual(r.net, Decimal("5200"))


class FormTests(FleetTestCase):
    def test_plate_is_normalised(self):
        form = VehicleForm(data={"plate": "kdb456c", "route": "Town", "capacity": 14, "status": "active"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["plate"], "KDB 456C")

    def test_bad_plate_rejected(self):
        form = VehicleForm(data={"plate": "ABC", "route": "Town", "capacity": 14, "status": "active"})
        self.assertFalse(form.is_valid())
        self.assertIn("plate", form.errors)

    def test_future_date_rejected(self):
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        form = DailyReturnForm(data=self.return_data(date=tomorrow.isoformat()), user=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_cannot_pick_someone_elses_vehicle(self):
        form = DailyReturnForm(data=self.return_data(vehicle=self.other_vehicle.pk), user=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("vehicle", form.errors)

    def test_one_return_per_vehicle_per_day(self):
        DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.owner, date=timezone.localdate(), collections=Decimal("100"), trips=1,
        )
        form = DailyReturnForm(data=self.return_data(), user=self.owner)
        self.assertFalse(form.is_valid())

    def test_collections_with_zero_trips_rejected(self):
        form = DailyReturnForm(data=self.return_data(trips=0), user=self.owner)
        self.assertFalse(form.is_valid())
        self.assertIn("trips", form.errors)


class AccessControlTests(FleetTestCase):
    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse("fleet:return_list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('fleet:return_list')}")

    def test_cannot_edit_another_users_return(self):
        theirs = DailyReturn.objects.create(
            vehicle=self.other_vehicle, recorded_by=self.other, date=timezone.localdate(),
            collections=Decimal("100"), trips=1,
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse("fleet:return_edit", args=[theirs.pk]))
        self.assertEqual(response.status_code, 404)


class SessionAndCrudTests(FleetTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_create_return_saves_and_remembers_vehicle_in_session(self):
        response = self.client.post(reverse("fleet:return_new"), self.return_data())
        self.assertRedirects(response, reverse("fleet:return_list"))
        saved = DailyReturn.objects.get()
        self.assertEqual(saved.recorded_by, self.owner)
        self.assertEqual(self.client.session["last_vehicle_id"], self.vehicle.pk)

        form = self.client.get(reverse("fleet:return_new")).context["form"]
        self.assertEqual(form.initial["vehicle"], self.vehicle.pk)

    def test_update_return_with_instance(self):
        r = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.owner, date=timezone.localdate(),
            collections=Decimal("100"), trips=1,
        )
        self.client.post(reverse("fleet:return_edit", args=[r.pk]), self.return_data(collections="12000.00"))
        r.refresh_from_db()
        self.assertEqual(r.collections, Decimal("12000.00"))
        self.assertEqual(DailyReturn.objects.count(), 1)

    def test_new_vehicle_belongs_to_logged_in_user(self):
        self.client.post(reverse("fleet:vehicle_new"), {
            "plate": "KDC 777D", "route": "58 Buruburu - Town", "capacity": 33, "status": "active",
        })
        self.assertEqual(Vehicle.objects.get(plate="KDC 777D").owner, self.owner)


class DeleteTests(FleetTestCase):
    def setUp(self):
        super().setUp()
        self.mine = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.owner, date=timezone.localdate(),
            collections=Decimal("100"), trips=1,
        )

    def test_anonymous_user_cannot_reach_delete(self):
        url = reverse("fleet:return_delete", args=[self.mine.pk])
        response = self.client.post(url)
        self.assertRedirects(response, f"{reverse('login')}?next={url}")
        self.assertTrue(DailyReturn.objects.filter(pk=self.mine.pk).exists())

    def test_get_shows_confirm_page_and_deletes_nothing(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("fleet:return_delete", args=[self.mine.pk]))
        self.assertContains(response, "Yes, delete")
        self.assertTrue(DailyReturn.objects.filter(pk=self.mine.pk).exists())

    def test_owner_can_delete_return(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("fleet:return_delete", args=[self.mine.pk]))
        self.assertRedirects(response, reverse("fleet:return_list"))
        self.assertFalse(DailyReturn.objects.filter(pk=self.mine.pk).exists())

    def test_owner_can_delete_vehicle_and_its_returns(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("fleet:vehicle_delete", args=[self.vehicle.pk]))
        self.assertRedirects(response, reverse("fleet:vehicle_list"))
        self.assertFalse(Vehicle.objects.filter(pk=self.vehicle.pk).exists())
        self.assertEqual(DailyReturn.objects.count(), 0)

    def test_cannot_delete_another_users_vehicle(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("fleet:vehicle_delete", args=[self.other_vehicle.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Vehicle.objects.filter(pk=self.other_vehicle.pk).exists())

    def test_cannot_delete_another_users_return(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("fleet:return_delete", args=[self.mine.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(DailyReturn.objects.filter(pk=self.mine.pk).exists())


class LayoutTests(FleetTestCase):
    def test_pages_load_the_stylesheet(self):
        response = self.client.get(reverse("fleet:home"))
        self.assertContains(response, "css/style.css")

    def test_list_buttons_link_to_delete(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("fleet:vehicle_list"))
        self.assertContains(response, reverse("fleet:vehicle_delete", args=[self.vehicle.pk]))
