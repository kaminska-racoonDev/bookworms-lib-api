from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status

from lib_app.helpers import create_borrowing

User = get_user_model()


class PaymentBaseTestClass(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("lib_app:payment-list")

    def detail_url(self, pk):
        return reverse("lib_app:payment-detail", kwargs={"pk": pk})


class PaymentUnauthTest(PaymentBaseTestClass):
    def test_payment_list_forbidden(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_detail_forbidden(self):
        borrowing = create_borrowing()
        payment = borrowing.create_payment()
        response = self.client.get(self.detail_url(payment.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_create_not_allowed(self):
        response = self.client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentAuthTest(PaymentBaseTestClass):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_payment_list_only_own(self):
        own_borrowing = create_borrowing(user=self.user)
        own_payment = own_borrowing.create_payment()

        other_user = User.objects.create_user(
            email="other@test.com", password="pass1234"
        )
        other_borrowing = create_borrowing(user=other_user)
        other_payment = other_borrowing.create_payment()

        response = self.client.get(self.list_url)
        returned_ids = [p["id"] for p in response.data]

        self.assertIn(own_payment.id, returned_ids)
        self.assertNotIn(other_payment.id, returned_ids)

    def test_payment_detail_own(self):
        borrowing = create_borrowing(user=self.user)
        payment = borrowing.create_payment()
        response = self.client.get(self.detail_url(payment.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payment_detail_others_not_found(self):
        other_user = User.objects.create_user(
            email="other2@test.com", password="pass1234"
        )
        borrowing = create_borrowing(user=other_user)
        payment = borrowing.create_payment()
        response = self.client.get(self.detail_url(payment.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_create_not_allowed(self):
        borrowing = create_borrowing(user=self.user)
        response = self.client.post(self.list_url, {"borrowing": borrowing.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_payment_update_not_allowed(self):
        borrowing = create_borrowing(user=self.user)
        payment = borrowing.create_payment()
        response = self.client.patch(
            self.detail_url(payment.pk), {"status": "PAID"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_payment_delete_not_allowed(self):
        borrowing = create_borrowing(user=self.user)
        payment = borrowing.create_payment()
        response = self.client.delete(self.detail_url(payment.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PaymentAdminTest(PaymentBaseTestClass):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_superuser(
            email="admin@test.com", password="admin.pass.test"
        )
        self.client.force_authenticate(user=self.user)

    def test_payment_list_shows_all(self):
        own_borrowing = create_borrowing(user=self.user)
        own_payment = own_borrowing.create_payment()

        other_user = User.objects.create_user(
            email="other3@test.com", password="pass1234"
        )
        other_borrowing = create_borrowing(user=other_user)
        other_payment = other_borrowing.create_payment()

        response = self.client.get(self.list_url)
        returned_ids = [p["id"] for p in response.data]

        self.assertIn(own_payment.id, returned_ids)
        self.assertIn(other_payment.id, returned_ids)

    def test_payment_detail_any_user(self):
        other_user = User.objects.create_user(
            email="other4@test.com", password="pass1234"
        )
        borrowing = create_borrowing(user=other_user)
        payment = borrowing.create_payment()
        response = self.client.get(self.detail_url(payment.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payment_create_not_allowed_even_for_admin(self):
        borrowing = create_borrowing()
        response = self.client.post(self.list_url, {"borrowing": borrowing.id})
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_payment_update_not_allowed_even_for_admin(self):
        borrowing = create_borrowing()
        payment = borrowing.create_payment()
        response = self.client.patch(
            self.detail_url(payment.pk), {"status": "PAID"}
        )
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_payment_delete_not_allowed_even_for_admin(self):
        borrowing = create_borrowing()
        payment = borrowing.create_payment()
        response = self.client.delete(self.detail_url(payment.pk))
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
