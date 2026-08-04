from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from lib_app.helpers import (
    create_borrowing, make_payment_with_session)
from lib_app.models import Payment


class PaymentStripeSessionTest(TestCase):
    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_create_payment_sets_session_id_and_url(self, mock_stripe_create):
        mock_session = MagicMock()
        mock_session.id = "cs_test_123"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_123"
        mock_stripe_create.return_value = mock_session

        borrowing = create_borrowing()
        payment = borrowing.create_payment()

        self.assertEqual(payment.session_id, "cs_test_123")
        self.assertEqual(
            payment.session_url, "https://checkout.stripe.com/pay/cs_test_123"
        )

    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_create_payment_calls_stripe_with_correct_amount(
        self, mock_stripe_create
    ):
        mock_session = MagicMock()
        mock_session.id = "cs_test_456"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_456"
        mock_stripe_create.return_value = mock_session

        borrowing = create_borrowing()
        payment = borrowing.create_payment()

        expected_cents = int(payment.money_to_pay * 100)
        called_kwargs = mock_stripe_create.call_args.kwargs
        actual_cents = called_kwargs["line_items"][0]["price_data"][
            "unit_amount"
        ]

        self.assertEqual(actual_cents, expected_cents)

    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_create_payment_mode_is_payment(self, mock_stripe_create):
        mock_session = MagicMock()
        mock_session.id = "cs_test_789"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_789"
        mock_stripe_create.return_value = mock_session

        borrowing = create_borrowing()
        borrowing.create_payment()

        called_kwargs = mock_stripe_create.call_args.kwargs
        self.assertEqual(called_kwargs["mode"], "payment")

    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_return_payment_fine_sets_session_data(self, mock_stripe_create):
        import datetime

        mock_session = MagicMock()
        mock_session.id = "cs_test_fine"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_fine"
        mock_stripe_create.return_value = mock_session

        borrow_date = datetime.date.today() - datetime.timedelta(days=10)
        expected_return = datetime.date.today() - datetime.timedelta(days=3)
        borrowing = create_borrowing(
            borrow_date=borrow_date,
            expected_return_date=expected_return,
            actual_return_date=datetime.date.today(),
        )

        fine_payment = borrowing.create_return_payment()

        self.assertEqual(fine_payment.session_id, "cs_test_fine")
        self.assertEqual(
            fine_payment.session_url,
            "https://checkout.stripe.com/pay/cs_test_fine",
        )

    @patch("lib_app.models.stripe.checkout.Session.create")
    def test_stripe_called_once_per_payment(self, mock_stripe_create):
        mock_session = MagicMock()
        mock_session.id = "cs_test_once"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_once"
        mock_stripe_create.return_value = mock_session

        borrowing = create_borrowing()
        borrowing.create_payment()

        self.assertEqual(mock_stripe_create.call_count, 1)


class PaymentConfirmationTest(TestCase):
    def test_mark_as_paid_sets_status(self):
        payment = make_payment_with_session()
        self.assertEqual(payment.status, Payment.StatusText.PENDING)

        payment.mark_as_paid()

        self.assertEqual(payment.status, Payment.StatusText.PAID)

    @patch("lib_app.models.stripe.checkout.Session.retrieve")
    def test_confirm_from_session_marks_paid_when_stripe_confirms(
        self, mock_retrieve
    ):
        payment = make_payment_with_session(session_id="cs_test_confirmed")

        mock_retrieve.return_value = MagicMock(payment_status="paid")

        result = Payment.confirm_from_session("cs_test_confirmed")

        payment.refresh_from_db()
        self.assertEqual(result.id, payment.id)
        self.assertEqual(payment.status, Payment.StatusText.PAID)

    @patch("lib_app.models.stripe.checkout.Session.retrieve")
    def test_confirm_from_session_does_nothing_if_unpaid(self, mock_retrieve):
        payment = make_payment_with_session(session_id="cs_test_unpaid")

        mock_retrieve.return_value = MagicMock(payment_status="unpaid")

        result = Payment.confirm_from_session("cs_test_unpaid")

        payment.refresh_from_db()
        self.assertIsNone(result)
        self.assertEqual(payment.status, Payment.StatusText.PENDING)

    @patch("lib_app.models.stripe.checkout.Session.retrieve")
    def test_confirm_from_session_returns_none_for_unknown_session(
        self, mock_retrieve
    ):
        mock_retrieve.return_value = MagicMock(payment_status="paid")

        result = Payment.confirm_from_session("cs_test_does_not_exist")

        self.assertIsNone(result)


class PaymentSuccessCancelViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.success_url = reverse("lib_app:payment-success")
        self.cancel_url = reverse("lib_app:payment-cancel")

    @patch("lib_app.models.stripe.checkout.Session.retrieve")
    def test_success_view_marks_payment_paid(self, mock_retrieve):
        payment = make_payment_with_session(session_id="cs_test_view_success")
        mock_retrieve.return_value = MagicMock(payment_status="paid")

        response = self.client.get(
            self.success_url, {"session_id": "cs_test_view_success"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment_id"], payment.id)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.StatusText.PAID)

    def test_success_view_missing_session_id_returns_400(self):
        response = self.client.get(self.success_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("lib_app.models.stripe.checkout.Session.retrieve")
    def test_success_view_unpaid_session_returns_400(self, mock_retrieve):
        make_payment_with_session(session_id="cs_test_view_unpaid")
        mock_retrieve.return_value = MagicMock(payment_status="unpaid")

        response = self.client.get(
            self.success_url, {"session_id": "cs_test_view_unpaid"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("lib_app.models.stripe.checkout.Session.retrieve")
    def test_success_view_unknown_session_returns_400(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(payment_status="paid")

        response = self.client.get(
            self.success_url, {"session_id": "cs_test_totally_unknown"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_success_view_is_publicly_accessible(self):
        """No auth required, since Stripe redirects the browser here directly."""
        response = self.client.get(self.success_url)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel_view_returns_200(self):
        response = self.client.get(self.cancel_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cancel_view_is_publicly_accessible(self):
        response = self.client.get(self.cancel_url)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
