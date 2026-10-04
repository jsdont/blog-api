from rest_framework import status
from rest_framework.test import APITestCase

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.auths.forms import UserCreationForm
from apps.auths.models import User

TEST_EMAIL = "student@example.com"
TEST_ADMIN_EMAIL = "admin@example.com"
TEST_PASSWORD = "Homework1-test-password!"
TEST_FIRST_NAME = "Test"
TEST_LAST_NAME = "Student"


class UserManagerTests(TestCase):
    def test_user_email_is_normalized_and_password_is_hashed(self) -> None:
        user = User.objects.create_user(
            email="  Student@EXAMPLE.COM  ",
            password=TEST_PASSWORD,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
        )

        self.assertEqual(user.email, TEST_EMAIL)
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_and_names_are_required(self) -> None:
        for missing_field in ("email", "first_name", "last_name"):
            with self.subTest(missing_field=missing_field):
                fields = {
                    "email": TEST_EMAIL,
                    "first_name": TEST_FIRST_NAME,
                    "last_name": TEST_LAST_NAME,
                }
                fields[missing_field] = " "
                with self.assertRaises(ValueError):
                    User.objects.create_user(password=TEST_PASSWORD, **fields)

    def test_duplicate_email_is_rejected(self) -> None:
        User.objects.create_user(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email=TEST_EMAIL.upper(),
                password=TEST_PASSWORD,
                first_name=TEST_FIRST_NAME,
                last_name=TEST_LAST_NAME,
            )

    def test_superuser_has_required_flags(self) -> None:
        user = User.objects.create_superuser(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(TEST_PASSWORD))

    def test_superuser_rejects_false_permissions(self) -> None:
        for flag in ("is_staff", "is_superuser"):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                User.objects.create_superuser(
                    email=TEST_EMAIL,
                    password=TEST_PASSWORD,
                    first_name=TEST_FIRST_NAME,
                    last_name=TEST_LAST_NAME,
                    **{flag: False},
                )

    def test_admin_creation_form_hashes_password(self) -> None:
        form = UserCreationForm(
            data={
                "email": "Student@EXAMPLE.COM",
                "first_name": TEST_FIRST_NAME,
                "last_name": TEST_LAST_NAME,
                "password1": TEST_PASSWORD,
                "password2": TEST_PASSWORD,
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, TEST_EMAIL)
        self.assertTrue(user.check_password(TEST_PASSWORD))

    def test_admin_add_page_creates_user(self) -> None:
        admin_user = User.objects.create_superuser(
            email=TEST_ADMIN_EMAIL,
            password=TEST_PASSWORD,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
        )
        self.client.force_login(admin_user)
        url = reverse("admin:auths_user_add")
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        response = self.client.post(
            url,
            {
                "email": TEST_EMAIL,
                "first_name": TEST_FIRST_NAME,
                "last_name": TEST_LAST_NAME,
                "password1": TEST_PASSWORD,
                "password2": TEST_PASSWORD,
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(
            User.objects.get(email=TEST_EMAIL).check_password(TEST_PASSWORD),
        )


class AuthenticationTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            first_name=TEST_FIRST_NAME,
            last_name=TEST_LAST_NAME,
        )

    def test_email_login_and_refresh(self) -> None:
        response = self.client.post(
            reverse("auths:token_obtain_pair"),
            {"email": TEST_EMAIL.upper(), "password": TEST_PASSWORD},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        refresh_response = self.client.post(
            reverse("auths:token_refresh"),
            {"refresh": response.data["refresh"]},
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    def test_inactive_user_cannot_log_in(self) -> None:
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("auths:token_obtain_pair"),
            {"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
