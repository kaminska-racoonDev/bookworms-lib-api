import datetime
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
