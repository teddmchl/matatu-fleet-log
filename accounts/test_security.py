"""Security tests (Week 9): password storage, CSRF, XSS, production settings."""

import os
import subprocess
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from fleet.models import Vehicle


class SecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("wanjiku", password="strong-pass-123")

    def test_password_is_stored_hashed(self):
        self.assertNotEqual(self.user.password, "strong-pass-123")
        self.assertTrue(self.user.password.startswith(("pbkdf2_sha256$", "argon2", "scrypt")))
        self.assertTrue(self.user.check_password("strong-pass-123"))

    def test_form_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(reverse("fleet:vehicle_new"), {
            "plate": "KDC 777D", "route": "Town", "capacity": 14, "status": "active",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Vehicle.objects.exists())

    def test_user_input_is_escaped_in_html(self):
        Vehicle.objects.create(owner=self.user, plate="KDA 123A", route="<script>alert(1)</script>")
        self.client.force_login(self.user)
        response = self.client.get(reverse("fleet:vehicle_list"))
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_session_cookie_not_readable_by_javascript(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)


class ProductionSettingsTests(TestCase):
    def run_settings(self, **env):
        """Import the settings in a fresh Python process with the given environment."""
        full_env = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        full_env.update(env)
        return subprocess.run(
            [sys.executable, "-c", "import config.settings as s; print(s.SECURE_SSL_REDIRECT, s.SESSION_COOKIE_SECURE)"],
            cwd=settings.BASE_DIR, env=full_env, capture_output=True, text=True,
        )

    def test_refuses_to_start_without_a_secret_key_in_production(self):
        result = self.run_settings(DJANGO_DEBUG="0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Set DJANGO_SECRET_KEY", result.stderr)

    def test_production_turns_on_https_settings(self):
        result = self.run_settings(DJANGO_DEBUG="0", DJANGO_SECRET_KEY="x" * 60, DJANGO_ALLOWED_HOSTS="example.com")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True True")
