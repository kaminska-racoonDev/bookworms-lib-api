from rest_framework import serializers
from lib_app.models import (
    Book,
    Borrowing,
    Payment,
)


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "cover",
            "inventory",
            "daily_fee",
        ]


class BorrowingSerializer(serializers.ModelSerializer):
    book_borrowed = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all()
    )

    def validate(self, attrs):
        data = super(BorrowingSerializer, self).validate(attrs)
        Borrowing.validate_expected_return_date(
            attrs["expected_return_date"],
            attrs["borrow_date"],
            serializers.ValidationError
        )
        Borrowing.validate_book_inventory(
            attrs["book_borrowed"],
            serializers.ValidationError,
        )
        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["book_borrowed"] = BookSerializer(
            instance.book_borrowed).data
        return representation

    class Meta:
        model = Borrowing
        fields = [
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "days_before_return",
            "estimated_money_to_pay",
            "book_borrowed",
            "user",
            "created_at",
        ]
        read_only_fields = [
            "user",
            "actual_return_date",
            "estimated_money_to_pay",
            "days_before_return",
            "created_at"
        ]


class PaymentSerializer(serializers.ModelSerializer):
    borrowing = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "status",
            "type",
            "borrowing",
            "session_url",
            "session_id",
            "money_to_pay",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]
