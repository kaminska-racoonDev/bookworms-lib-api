from django.db import models
from django.contrib.auth import get_user_model
import datetime

from jsonschema import ValidationError

User = get_user_model()


class Book(models.Model):
    class CoverType(models.TextChoices):
        HARD = "HARD"
        SOFT = "SOFT"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(
        max_length=10,
        choices=CoverType.choices
    )
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.title} - {self.author}"


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book_borrowed = models.ForeignKey(
        Book, on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (f"Borrowed book: {self.book_borrowed.title} "
                f"- Return by {self.expected_return_date}")

    @property
    def days_before_return(self):
        if self.actual_return_date:
            return None

        return (self.expected_return_date - datetime.date.today()).days

    @property
    def is_active(self):
        return self.actual_return_date is None

    @staticmethod
    def validate_expected_return_date(
        expected_return_date: datetime,
        borrow_date: datetime,
        error_to_raise
    ):
        if expected_return_date < borrow_date:
            raise error_to_raise(
                "Expected return date can't be before the borrow date.")

    @staticmethod
    def validate_book_inventory(book, error_to_raise):
        if book.inventory <= 0:
            raise error_to_raise(f"'{book.title}' is out of stock.")

    def clean(self):
        Borrowing.validate_expected_return_date(
            self.expected_return_date, self.borrow_date, ValidationError
        )

    FINE_MULTIPLIER = 2

    def calculate_payment(self):
        expected_days = (self.expected_return_date - self.borrow_date).days
        return self.book_borrowed.daily_fee * expected_days

    def create_payment(self):
        return Payment.objects.create(
            borrowing=self,
            type=Payment.PaymentType.PAYMENT,
            status=Payment.StatusText.PENDING,
            money_to_pay=self.calculate_payment(),
        )

    def create_return_payment(self):
        fine_amount = self.calculate_fine()
        if fine_amount is None:
            return None
        return Payment.objects.create(
            borrowing=self,
            type=Payment.PaymentType.FINE,
            status=Payment.StatusText.PENDING,
            money_to_pay=fine_amount,
        )

    def calculate_fine(self):
        if not self.actual_return_date:
            return None
        days_overdue = (self.actual_return_date
                        - self.expected_return_date).days
        if days_overdue <= 0:
            return None
        return self.book_borrowed.daily_fee * days_overdue * self.FINE_MULTIPLIER

    @property
    def estimated_money_to_pay(self):
        if self.actual_return_date:
            # already returned — the estimate is settled, not a projection anymore
            base = self.calculate_payment()
            fine = self.calculate_fine() or 0
            return base + fine

        if datetime.date.today() > self.expected_return_date:
            # currently overdue and still not returned — estimate fine as of today
            days_overdue = (datetime.date.today()
                            - self.expected_return_date).days
            projected_fine = self.book_borrowed.daily_fee * \
                days_overdue * self.FINE_MULTIPLIER
            return self.calculate_payment() + projected_fine

        # still within the expected window — just the base fee
        return self.calculate_payment()


class Payment(models.Model):
    class StatusText(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"

    class PaymentType(models.TextChoices):
        PAYMENT = "PAYMENT"
        FINE = "FINE"
    status = models.CharField(
        max_length=10,
        choices=StatusText.choices
    )
    type = models.CharField(
        max_length=10,
        choices=PaymentType.choices
    )
    borrowing = models.ForeignKey(
        Borrowing, on_delete=models.CASCADE
    )
    session_id = models.CharField(max_length=255)
    session_url = models.URLField(null=True, blank=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} - {self.status}"
