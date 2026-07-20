from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

User = get_user_model()


class UserTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_access(self):
        payload = {
            "email": "usertest@test.com",
            "password": "testpss123"
        }
        url = reverse("user:register")
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login_access(self):
        User.objects.create_user(
            email="usertest@test.com",
            password="testpass123"
        )
        payload = {
            "email": "usertest@test.com",
            "password": "testpass123"
        }
        url = reverse("user:login")
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_manage_access(self):
        user = User.objects.create_user(
            email="usertest@test.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user:manage")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "usertest@test.com")

    def test_token_refresh(self):
        User.objects.create_user(
            email="usertest@test.com",
            password="testpass123"
        )
        login_response = self.client.post(
            reverse("user:login"),
            {
                "email": "usertest@test.com",
                "password": "testpass123"
            })
        refresh_token = login_response.data["refresh"]

        url = reverse("user:token_refresh")
        response = self.client.post(url, {"refresh": refresh_token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
