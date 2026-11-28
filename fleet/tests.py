"""Fleet app tests: models, forms, access control, roles and sessions. Run: python manage.py test"""

import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile

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


class RoleAuthorisationTests(FleetTestCase):
    def setUp(self):
        super().setUp()
        self.driver = User.objects.create_user("mwangi", password="strong-pass-123")
        self.driver.profile.role = Profile.ROLE_DRIVER
        self.driver.profile.save()

        self.admin = User.objects.create_user("sacco_boss", password="strong-pass-123")
        self.admin.profile.role = Profile.ROLE_SACCO_ADMIN
        self.admin.profile.save()

        self.vehicle.driver = self.driver
        self.vehicle.save()

    def test_vehicle_form_limits_driver_to_driver_role(self):
        ok_form = VehicleForm(data={
            "plate": "KDD 111A", "route": "23 Kangemi", "capacity": 14,
            "status": "active", "driver": self.driver.pk,
        })
        self.assertTrue(ok_form.is_valid(), ok_form.errors)

        bad_form = VehicleForm(data={
            "plate": "KDD 222B", "route": "23 Kangemi", "capacity": 14,
            "status": "active", "driver": self.owner.pk,
        })
        self.assertFalse(bad_form.is_valid())
        self.assertIn("driver", bad_form.errors)

    def test_driver_sees_only_assigned_vehicles(self):
        unassigned = Vehicle.objects.create(owner=self.owner, plate="KDE 555E", route="33 Utawala")
        self.client.force_login(self.driver)
        response = self.client.get(reverse("fleet:vehicle_list"))
        self.assertContains(response, self.vehicle.plate)
        self.assertNotContains(response, unassigned.plate)
        self.assertNotContains(response, self.other_vehicle.plate)
        self.assertNotContains(response, reverse("fleet:vehicle_new"))

    def test_driver_cannot_add_edit_or_delete_vehicles(self):
        self.client.force_login(self.driver)
        self.assertEqual(self.client.get(reverse("fleet:vehicle_new")).status_code, 403)
        self.assertEqual(self.client.post(reverse("fleet:vehicle_new"), {
            "plate": "KDF 123F", "route": "Town", "capacity": 14, "status": "active",
        }).status_code, 403)
        self.assertEqual(self.client.get(reverse("fleet:vehicle_edit", args=[self.vehicle.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("fleet:vehicle_edit", args=[self.vehicle.pk]), {
            "plate": "KDA 123A", "route": "Changed", "capacity": 14, "status": "active",
        }).status_code, 403)
        self.assertEqual(self.client.post(reverse("fleet:vehicle_delete", args=[self.vehicle.pk])).status_code, 403)
        self.assertTrue(Vehicle.objects.filter(pk=self.vehicle.pk).exists())

    def test_driver_can_add_return_only_for_assigned_vehicle(self):
        self.client.force_login(self.driver)
        # Assigned vehicle works
        response = self.client.post(reverse("fleet:return_new"), self.return_data())
        self.assertRedirects(response, reverse("fleet:return_list"))
        saved = DailyReturn.objects.get(vehicle=self.vehicle)
        self.assertEqual(saved.recorded_by, self.driver)

        # Unassigned vehicle is rejected by the form queryset
        bad = self.client.post(reverse("fleet:return_new"), self.return_data(vehicle=self.other_vehicle.pk))
        self.assertEqual(bad.status_code, 200)
        self.assertIn("vehicle", bad.context["form"].errors)

    def test_driver_sees_returns_for_assigned_vehicles_only(self):
        mine = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.driver, date=timezone.localdate(),
            collections=Decimal("9000"), trips=8,
        )
        other_ret = DailyReturn.objects.create(
            vehicle=self.other_vehicle, recorded_by=self.other, date=timezone.localdate(),
            collections=Decimal("7000"), trips=6,
        )
        self.client.force_login(self.driver)
        response = self.client.get(reverse("fleet:return_list"))
        self.assertContains(response, mine.vehicle.plate)
        self.assertNotContains(response, other_ret.vehicle.plate)

    def test_driver_can_edit_and_delete_own_same_day_return(self):
        ret = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.driver, date=timezone.localdate(),
            collections=Decimal("8000"), trips=6,
        )
        self.client.force_login(self.driver)
        response = self.client.post(
            reverse("fleet:return_edit", args=[ret.pk]),
            self.return_data(collections="9200.00"),
        )
        self.assertRedirects(response, reverse("fleet:return_list"))
        ret.refresh_from_db()
        self.assertEqual(ret.collections, Decimal("9200.00"))

        del_response = self.client.post(reverse("fleet:return_delete", args=[ret.pk]))
        self.assertRedirects(del_response, reverse("fleet:return_list"))
        self.assertFalse(DailyReturn.objects.filter(pk=ret.pk).exists())

    def test_driver_cannot_edit_or_delete_previous_day_or_owner_recorded_return(self):
        yesterday = timezone.localdate() - datetime.timedelta(days=1)
        old_ret = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.driver, date=yesterday,
            collections=Decimal("8000"), trips=6,
        )
        owner_ret = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.owner, date=timezone.localdate(),
            collections=Decimal("8500"), trips=7,
        )
        self.client.force_login(self.driver)
        for target in (old_ret, owner_ret):
            self.assertEqual(self.client.get(reverse("fleet:return_edit", args=[target.pk])).status_code, 403)
            self.assertEqual(
                self.client.post(reverse("fleet:return_edit", args=[target.pk]), self.return_data()).status_code,
                403,
            )
            self.assertEqual(self.client.post(reverse("fleet:return_delete", args=[target.pk])).status_code, 403)
            self.assertTrue(DailyReturn.objects.filter(pk=target.pk).exists())

    def test_sacco_admin_sees_all_vehicles_and_returns_read_only(self):
        r1 = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.driver, date=timezone.localdate(),
            collections=Decimal("9000"), trips=8,
        )
        r2 = DailyReturn.objects.create(
            vehicle=self.other_vehicle, recorded_by=self.other, date=timezone.localdate(),
            collections=Decimal("7500"), trips=6,
        )
        self.client.force_login(self.admin)

        veh_page = self.client.get(reverse("fleet:vehicle_list"))
        self.assertContains(veh_page, self.vehicle.plate)
        self.assertContains(veh_page, self.other_vehicle.plate)
        self.assertNotContains(veh_page, reverse("fleet:vehicle_new"))
        self.assertNotContains(veh_page, reverse("fleet:vehicle_edit", args=[self.vehicle.pk]))

        ret_page = self.client.get(reverse("fleet:return_list"))
        self.assertContains(ret_page, r1.vehicle.plate)
        self.assertContains(ret_page, r2.vehicle.plate)
        self.assertNotContains(ret_page, reverse("fleet:return_new"))
        self.assertNotContains(ret_page, reverse("fleet:return_edit", args=[r1.pk]))

    def test_sacco_admin_cannot_add_edit_or_delete_vehicles_or_returns(self):
        ret = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.owner, date=timezone.localdate(),
            collections=Decimal("9000"), trips=8,
        )
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("fleet:vehicle_new")).status_code, 403)
        self.assertEqual(self.client.post(reverse("fleet:vehicle_new"), {
            "plate": "KDG 111G", "route": "Town", "capacity": 14, "status": "active",
        }).status_code, 403)
        self.assertEqual(self.client.get(reverse("fleet:vehicle_edit", args=[self.vehicle.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("fleet:vehicle_delete", args=[self.vehicle.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("fleet:return_new")).status_code, 403)
        self.assertEqual(self.client.post(reverse("fleet:return_new"), self.return_data()).status_code, 403)
        self.assertEqual(self.client.get(reverse("fleet:return_edit", args=[ret.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("fleet:return_delete", args=[ret.pk])).status_code, 403)

    def test_owner_can_assign_and_clear_driver_on_vehicle_edit(self):
        unassigned = Vehicle.objects.create(owner=self.owner, plate="KDH 222H", route="46")
        self.client.force_login(self.owner)

        # Assigning a non-driver is rejected.
        bad = self.client.post(reverse("fleet:vehicle_edit", args=[unassigned.pk]), {
            "plate": "KDH 222H", "route": "46", "capacity": 14, "status": "active", "driver": self.other.pk,
        })
        self.assertEqual(bad.status_code, 200)
        self.assertIn("driver", bad.context["form"].errors)

        # Assigning a driver succeeds.
        ok = self.client.post(reverse("fleet:vehicle_edit", args=[unassigned.pk]), {
            "plate": "KDH 222H", "route": "46", "capacity": 14, "status": "active", "driver": self.driver.pk,
        })
        self.assertRedirects(ok, reverse("fleet:vehicle_list"))
        unassigned.refresh_from_db()
        self.assertEqual(unassigned.driver, self.driver)

        # Clearing the driver leaves the vehicle unassigned.
        cleared = self.client.post(reverse("fleet:vehicle_edit", args=[unassigned.pk]), {
            "plate": "KDH 222H", "route": "46", "capacity": 14, "status": "active", "driver": "",
        })
        self.assertRedirects(cleared, reverse("fleet:vehicle_list"))
        unassigned.refresh_from_db()
        self.assertIsNone(unassigned.driver)

    def test_driver_gets_404_editing_or_deleting_unassigned_vehicles_return(self):
        other_ret = DailyReturn.objects.create(
            vehicle=self.other_vehicle, recorded_by=self.other, date=timezone.localdate(),
            collections=Decimal("7000"), trips=6,
        )
        self.client.force_login(self.driver)
        self.assertEqual(self.client.get(reverse("fleet:return_edit", args=[other_ret.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("fleet:return_delete", args=[other_ret.pk])).status_code, 404)
        self.assertTrue(DailyReturn.objects.filter(pk=other_ret.pk).exists())

    def test_driver_cannot_log_return_for_inactive_assigned_vehicle(self):
        self.vehicle.status = "garage"
        self.vehicle.save()
        self.client.force_login(self.driver)
        response = self.client.post(reverse("fleet:return_new"), self.return_data())
        self.assertEqual(response.status_code, 200)
        self.assertIn("vehicle", response.context["form"].errors)

    def test_return_list_avoids_per_row_profile_queries(self):
        today = timezone.localdate()
        DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.driver, date=today,
            collections=Decimal("9000"), trips=8,
        )
        self.client.force_login(self.driver)
        with CaptureQueriesContext(connection) as one_row_queries:
            self.client.get(reverse("fleet:return_list"))

        for days_ago in range(1, 5):
            DailyReturn.objects.create(
                vehicle=self.vehicle, recorded_by=self.driver,
                date=today - datetime.timedelta(days=days_ago),
                collections=Decimal("8000"), trips=6,
            )
        with CaptureQueriesContext(connection) as five_row_queries:
            self.client.get(reverse("fleet:return_list"))

        self.assertEqual(len(five_row_queries), len(one_row_queries))
