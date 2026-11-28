"""JSON API tests (fleet/api.py). Run: python manage.py test"""

import datetime
import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile

from .models import DailyReturn
from .tests import FleetTestCase


class ApiTestCase(FleetTestCase):
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.mine = DailyReturn.objects.create(
            vehicle=self.vehicle, recorded_by=self.owner, date=self.today - datetime.timedelta(days=1),
            collections=Decimal("9000"), fuel=Decimal("3000"), trips=7,
        )
        self.theirs = DailyReturn.objects.create(
            vehicle=self.other_vehicle, recorded_by=self.other, date=self.today,
            collections=Decimal("100"), trips=1,
        )

    def post_json(self, data, client=None, **headers):
        client = client or self.client
        return client.post(
            reverse("fleet:api_return_list"), data=json.dumps(data),
            content_type="application/json", **headers,
        )


class ApiAuthTests(ApiTestCase):
    def test_anonymous_gets_401_json(self):
        for name in ("fleet:api_vehicle_list", "fleet:api_return_list"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["error"], "Authentication required.")

    def test_wrong_method_is_405(self):
        self.client.force_login(self.owner)
        response = self.client.delete(reverse("fleet:api_vehicle_list"))
        self.assertEqual(response.status_code, 405)


class ApiReadTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_vehicle_list_only_shows_my_vehicles(self):
        data = self.client.get(reverse("fleet:api_vehicle_list")).json()
        self.assertEqual([v["plate"] for v in data["vehicles"]], ["KDA 123A"])

    def test_vehicle_detail(self):
        response = self.client.get(reverse("fleet:api_vehicle_detail", args=[self.vehicle.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["route"], "46 Kawangware - Town")

    def test_someone_elses_vehicle_is_404(self):
        response = self.client.get(reverse("fleet:api_vehicle_detail", args=[self.other_vehicle.pk]))
        self.assertEqual(response.status_code, 404)

    def test_return_list_is_scoped_and_has_net(self):
        returns = self.client.get(reverse("fleet:api_return_list")).json()["returns"]
        self.assertEqual(len(returns), 1)
        self.assertEqual(returns[0]["net"], "6000.00")

    def test_return_list_filters(self):
        url = reverse("fleet:api_return_list")
        self.assertEqual(len(self.client.get(url, {"date": self.today.isoformat()}).json()["returns"]), 0)
        self.assertEqual(len(self.client.get(url, {"vehicle": self.vehicle.pk}).json()["returns"]), 1)

    def test_bad_filters_are_400(self):
        url = reverse("fleet:api_return_list")
        self.assertEqual(self.client.get(url, {"date": "28-11-2026"}).status_code, 400)
        self.assertEqual(self.client.get(url, {"vehicle": "abc"}).status_code, 400)


class ApiCreateTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def test_create_return_is_201(self):
        response = self.post_json(self.return_data())
        self.assertEqual(response.status_code, 201)
        created = DailyReturn.objects.get(pk=response.json()["id"])
        self.assertEqual(created.recorded_by, self.owner)
        self.assertEqual(response.json()["net"], "5200.00")

    def test_created_amounts_match_what_get_returns(self):
        response = self.post_json(self.return_data(collections="9500"))
        self.assertEqual(response.json()["collections"], "9500.00")

    def test_form_rules_apply_to_the_api(self):
        response = self.post_json(self.return_data(vehicle=self.other_vehicle.pk))
        self.assertEqual(response.status_code, 400)
        self.assertIn("vehicle", response.json()["errors"])

    def test_invalid_json_is_400(self):
        response = self.client.post(
            reverse("fleet:api_return_list"), data="not json", content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = self.post_json(self.return_data(), client=client)
        self.assertEqual(response.status_code, 403)

    def test_post_with_csrf_token_header_works(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        token = client.get(reverse("fleet:api_csrf")).json()["csrfToken"]
        response = self.post_json(self.return_data(), client=client, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)


class ApiRoleTests(ApiTestCase):
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

    def test_driver_api_sees_only_assigned_vehicles_and_returns(self):
        self.client.force_login(self.driver)
        vehicles = self.client.get(reverse("fleet:api_vehicle_list")).json()["vehicles"]
        self.assertEqual([v["plate"] for v in vehicles], ["KDA 123A"])
        self.assertEqual(self.client.get(reverse("fleet:api_vehicle_detail", args=[self.vehicle.pk])).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("fleet:api_vehicle_detail", args=[self.other_vehicle.pk])).status_code,
            404,
        )
        returns = self.client.get(reverse("fleet:api_return_list")).json()["returns"]
        self.assertEqual([r["plate"] for r in returns], ["KDA 123A"])

    def test_driver_api_can_post_return_only_for_assigned_vehicle(self):
        self.client.force_login(self.driver)
        ok = self.post_json(self.return_data())
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()["recorded_by"], "mwangi")

        bad = self.post_json(self.return_data(vehicle=self.other_vehicle.pk))
        self.assertEqual(bad.status_code, 400)
        self.assertIn("vehicle", bad.json()["errors"])

    def test_sacco_admin_api_sees_all_but_cannot_post(self):
        self.client.force_login(self.admin)
        vehicles = self.client.get(reverse("fleet:api_vehicle_list")).json()["vehicles"]
        self.assertEqual([v["plate"] for v in vehicles], ["KCB 999B", "KDA 123A"])
        self.assertEqual(
            self.client.get(reverse("fleet:api_vehicle_detail", args=[self.other_vehicle.pk])).status_code,
            200,
        )
        returns = self.client.get(reverse("fleet:api_return_list")).json()["returns"]
        self.assertEqual(len(returns), 2)

        denied = self.post_json(self.return_data())
        self.assertEqual(denied.status_code, 403)
