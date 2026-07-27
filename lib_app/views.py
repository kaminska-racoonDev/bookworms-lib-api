from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework import viewsets
from lib_app.serializers import (
    BookSerializer,
    BorrowingSerializer,
    PaymentSerializer,
)
from lib_app.models import (
    Book,
    Borrowing,
    Payment,
)
from rest_framework.permissions import IsAuthenticated
from lib_app.permissions import (
    IsAdminOrReadOnly,
)


class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    queryset = Book.objects.all()
    permission_classes = (IsAdminOrReadOnly,)


class BorrowingViewSet(viewsets.ModelViewSet):
    serializer_class = BorrowingSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            queryset = Borrowing.objects.all()
            user_id = self.request.query_params.get("user_id")
            if user_id is not None:
                queryset = queryset.filter(user_id=user_id)
        else:
            queryset = Borrowing.objects.filter(user=user)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(actual_return_date__isnull=False)
        return queryset

    def perform_create(self, serializer):
        borrowing = serializer.save(user=self.request.user)
        borrowing.book_borrowed.inventory -= 1
        borrowing.book_borrowed.save()
        borrowing.create_payment()

    @action(detail=True, methods=["post"], url_path="return")
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()

        if borrowing.actual_return_date is not None:
            return Response(
                {"detail": "This borrowing has already been returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        borrowing.actual_return_date = timezone.now().date()
        borrowing.save()

        borrowing.book_borrowed.inventory += 1
        borrowing.book_borrowed.save()

        borrowing.create_return_payment()

        serializer = self.get_serializer(borrowing)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(borrowing__user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
