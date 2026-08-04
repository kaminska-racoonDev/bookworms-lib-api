import datetime
from unittest.mock import patch, MagicMock
import uuid

from django.contrib.auth import get_user_model

from lib_app.models import Book, Borrowing

User = get_user_model()


def create_book(
    title="1984", author="G. Orwell", cover="HARD", inventory=4, daily_fee=20.2
):
    return Book.objects.create(
        title=title,
        author=author,
        cover=cover,
        inventory=inventory,
        daily_fee=daily_fee,
    )


def create_borrowing(
    borrow_date=None,
    expected_return_date=None,
    actual_return_date=None,
    book_borrowed=None,
    user=None,
):
    borrow_date = borrow_date or datetime.date.today()
    expected_return_date = expected_return_date or (
        datetime.date.today() + datetime.timedelta(days=14)
    )
    book_borrowed = book_borrowed or create_book()
    user = user or User.objects.create_user(
        email=f"borrower_{uuid.uuid4().hex[:8]}@test.com",
        password="testpass123",
    )

    return Borrowing.objects.create(
        borrow_date=borrow_date,
        expected_return_date=expected_return_date,
        actual_return_date=actual_return_date,
        book_borrowed=book_borrowed,
        user=user,
    )


def make_payment_with_session(session_id="cs_test_confirm"):
    """Helper: creates a Payment with a Stripe session already mocked in."""
    with patch("lib_app.models.stripe.checkout.Session.create") as mock_create:
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.url = f"https://checkout.stripe.com/pay/{session_id}"
        mock_create.return_value = mock_session

        borrowing = create_borrowing()
        payment = borrowing.create_payment()

    return payment
