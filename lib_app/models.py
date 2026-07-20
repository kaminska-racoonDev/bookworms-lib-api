from django.db import models
from django.contrib.auth import get_user_model

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
