from django.contrib.auth.models import User
from django.urls import reverse

from ads.factories import DEFAULT_PASSWORD, UserFactory
from ads.tests.base import BaseTestCase


class RegistrationTests(BaseTestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_register_and_is_logged_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newcomer",
                "password1": "a-strong-pass-123",
                "password2": "a-strong-pass-123",
            },
        )
        self.assertRedirects(response, reverse("ads:ad-list"))
        self.assertTrue(User.objects.filter(username="newcomer").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_username_must_be_unique(self):
        UserFactory(username="taken")
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "taken",
                "password1": "a-strong-pass-123",
                "password2": "a-strong-pass-123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "username",
            "A user with that username already exists.",
        )

    def test_passwords_must_match(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "mismatch",
                "password1": "a-strong-pass-123",
                "password2": "a-different-pass-456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="mismatch").exists())
        self.assertIn("password2", response.context["form"].errors)


class LoginLogoutTests(BaseTestCase):
    def setUp(self):
        self.user = UserFactory(username="someone")

    def test_login_with_correct_password(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "someone", "password": DEFAULT_PASSWORD},
        )
        self.assertRedirects(response, reverse("ads:ad-list"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "someone", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_with_unknown_username_fails(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "ghost", "password": DEFAULT_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout(self):
        self.client.login(username="someone", password=DEFAULT_PASSWORD)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("ads:ad-list"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_honours_the_next_parameter(self):
        target = reverse("ads:wishlist")
        response = self.client.post(
            f'{reverse("accounts:login")}?next={target}',
            {"username": "someone", "password": DEFAULT_PASSWORD},
        )
        self.assertRedirects(response, target)
