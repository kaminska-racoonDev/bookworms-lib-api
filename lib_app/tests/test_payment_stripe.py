from unittest.mock import patch, MagicMock

from django.test import TestCase

from lib_app.helpers import create_borrowing
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
