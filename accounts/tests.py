"""Accounts app tests: sign-up, login/logout and the profile page."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("wanjiku", password="strong-pass-123")

    def test_signup_logs_the_user_in(self):
        response = self.client.post(reverse("accounts:signup"), {
            "username": "kamau", "email": "kamau@example.com",
            "password1": "matatu-rocks-2026", "password2": "matatu-rocks-2026",
        })
        self.assertRedirects(response, reverse("fleet:vehicle_new"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_signup_rejects_mismatched_passwords(self):
        response = self.client.post(reverse("accounts:signup"), {
            "username": "kamau", "email": "kamau@example.com",
            "password1": "matatu-rocks-2026", "password2": "different-2026",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="kamau").exists())

    def test_login_and_logout(self):
        response = self.client.post(reverse("login"), {"username": "wanjiku", "password": "strong-pass-123"})
        self.assertRedirects(response, reverse("fleet:home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('accounts:profile')}")

    def test_profile_shows_session_details(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "wanjiku")
        self.assertTrue(response.context["expires_at_browser_close"])
