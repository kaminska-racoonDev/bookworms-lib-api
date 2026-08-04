from django.db import models
from django.contrib.auth import get_user_model
import datetime
import stripe
from django.conf import settings

from jsonschema import ValidationError

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


class Book(models.Model):
    class CoverType(models.TextChoices):
        HARD = "HARD"
        SOFT = "SOFT"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(max_length=10, choices=CoverType.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.title} - {self.author}"


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    book_borrowed = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Borrowed book: {self.book_borrowed.title} "
            f"- Return by {self.expected_return_date}"
        )

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
        expected_return_date: datetime, borrow_date: datetime, error_to_raise
    ):
        if expected_return_date < borrow_date:
            raise error_to_raise(
                "Expected return date can't be before the borrow date."
            )

    @staticmethod
    def validate_book_inventory(book, error_to_raise):
        if book.inventory <= 0:
            raise error_to_raise(f"'{book.title}' is out of stock.")

    @staticmethod
    def validate_pending_payments(user, error_to_raise):
        has_pending_payments = Payment.objects.filter(
            borrowing__user=user, status=Payment.StatusText.PENDING
        ).exists()

        if has_pending_payments:
            raise error_to_raise(
                "You have pending payments. Pay them before borrowing new book."
            )

    def clean(self):
        self.validate_expected_return_date(
            self.expected_return_date,
            self.borrow_date,
            ValidationError,
        )

        self.validate_pending_payments(
            self.user,
            ValidationError,
        )

        self.validate_book_inventory(
            self.book_borrowed,
            ValidationError,
        )

    def full_clean(self, exclude=None, validate_unique=True):
        super().full_clean(
            exclude=exclude,
            validate_unique=validate_unique,
        )

    FINE_MULTIPLIER = 2

    def calculate_payment(self):
        expected_days = (self.expected_return_date - self.borrow_date).days
        return self.book_borrowed.daily_fee * expected_days

    def create_payment(self):
        payment = Payment.objects.create(
            borrowing=self,
            type=Payment.PaymentType.PAYMENT,
            status=Payment.StatusText.PENDING,
            money_to_pay=self.calculate_payment(),
        )
        payment.create_stripe_session()
        return payment

    def create_return_payment(self):
        fine_amount = self.calculate_fine()
        if fine_amount is None:
            return None
        payment = Payment.objects.create(
            borrowing=self,
            type=Payment.PaymentType.FINE,
            status=Payment.StatusText.PENDING,
            money_to_pay=fine_amount,
        )
        payment.create_stripe_session()
        return payment

    def calculate_fine(self):
        if not self.actual_return_date:
            return None
        days_overdue = (
            self.actual_return_date - self.expected_return_date
        ).days
        if days_overdue <= 0:
            return None
        return (
            self.book_borrowed.daily_fee * days_overdue * self.FINE_MULTIPLIER
        )

    @property
    def estimated_money_to_pay(self):
        if self.actual_return_date:
            base = self.calculate_payment()
            fine = self.calculate_fine() or 0
            return base + fine

        if datetime.date.today() > self.expected_return_date:
            days_overdue = (
                datetime.date.today() - self.expected_return_date
            ).days
            projected_fine = (
                self.book_borrowed.daily_fee
                * days_overdue
                * self.FINE_MULTIPLIER
            )
            return self.calculate_payment() + projected_fine

        return self.calculate_payment()


class Payment(models.Model):
    class StatusText(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"

    class PaymentType(models.TextChoices):
        PAYMENT = "PAYMENT"
        FINE = "FINE"

    status = models.CharField(max_length=10, choices=StatusText.choices)
    type = models.CharField(max_length=10, choices=PaymentType.choices)
    borrowing = models.ForeignKey(Borrowing, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255)
    session_url = models.URLField(null=True, blank=True)
    money_to_pay = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} - {self.status}"

    def create_stripe_session(self):
        product_name = (
            f"{self.get_type_display()} for"
            f"'{self.borrowing.book_borrowed.title}'"
        )

        success_url = (
            settings.APP_BASE_URL
            + "/api/v1/lib_app/payments/success/?session_id={CHECKOUT_SESSION_ID}"
        )
        cancel_url = settings.APP_BASE_URL + "/api/v1/lib_app/payments/cancel/"

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": product_name},
                        "unit_amount": int(self.money_to_pay * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        self.session_id = session.id
        self.session_url = session.url
        self.save()

        return session

    def mark_as_paid(self):
        self.status = self.StatusText.PAID
        self.save()

    @classmethod
    def confirm_from_session(cls, session_id):
        """
        Fetches the Stripe session and marks the matching Payment PAID
        if Stripe confirms it was actually paid.
        """
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status != "paid":
            return None

        try:
            payment = cls.objects.get(session_id=session_id)
        except cls.DoesNotExist:
            return None

        payment.mark_as_paid()
        return payment
