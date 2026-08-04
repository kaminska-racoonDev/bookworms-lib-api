from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status

from lib_app.helpers import create_book
from lib_app.models import Payment

User = get_user_model()


class BorrowingStripeIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("lib_app:borrowing-list")
        self.user = User.objects.create_user(
            email="stripeuser@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_borrowing_create_triggers_stripe_session(
        self, mock_stripe_create
    ):
        mock_session = MagicMock()
        mock_session.id = "cs_test_borrow"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_borrow"
        mock_stripe_create.return_value = mock_session

        book = create_book(inventory=3)
        response = self.client.post(
            self.list_url,
            {
                "borrow_date": "2026-08-04",
                "expected_return_date": "2026-08-18",
                "book_borrowed": book.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_stripe_create.assert_called_once()

        payment = Payment.objects.get(borrowing_id=response.data["id"])
        self.assertEqual(payment.session_id, "cs_test_borrow")
        self.assertEqual(
            payment.session_url,
            "https://checkout.stripe.com/pay/cs_test_borrow",
        )

    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_borrowing_return_late_triggers_second_stripe_session(
        self, mock_stripe_create
    ):
        mock_session = MagicMock()
        mock_session.id = "cs_test_return"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_return"
        mock_stripe_create.return_value = mock_session

        book = create_book(inventory=1, daily_fee=10)
        create_response = self.client.post(
            self.list_url,
            {
                "borrow_date": "2026-07-01",
                "expected_return_date": "2026-07-10",
                "book_borrowed": book.id,
            },
        )
        borrowing_id = create_response.data["id"]

        mock_stripe_create.reset_mock()

        return_url = reverse(
            "lib_app:borrowing-return-borrowing", kwargs={"pk": borrowing_id}
        )
        response = self.client.post(return_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_stripe_create.assert_called_once()

        fine = Payment.objects.filter(
            borrowing_id=borrowing_id, type=Payment.PaymentType.FINE
        ).first()
        self.assertIsNotNone(fine)
        self.assertEqual(fine.session_id, "cs_test_return")

    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_borrowing_create_fails_gracefully_if_stripe_errors(
        self, mock_stripe_create
    ):
        mock_stripe_create.side_effect = Exception("Stripe API error")

        book = create_book(inventory=3)

        with self.assertRaises(Exception):
            self.client.post(
                self.list_url,
                {
                    "borrow_date": "2026-08-04",
                    "expected_return_date": "2026-08-18",
                    "book_borrowed": book.id,
                },
            )
