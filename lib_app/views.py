from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.views import APIView
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
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
from rest_framework.permissions import IsAuthenticated, AllowAny
from lib_app.permissions import (
    IsAdminOrReadOnly,
    IsAdminOrIfAuthenticatedReadOnly,
)


@extend_schema_view(
    list=extend_schema(
        summary="List books",
        description="Returns all books in the catalog. Read access is open to everyone; "
        "create/update/delete require admin rights.",
    ),
    retrieve=extend_schema(summary="Retrieve a book"),
    create=extend_schema(summary="Add a new book (admin only)"),
    update=extend_schema(summary="Update a book (admin only)"),
    partial_update=extend_schema(
        summary="Partially update a book (admin only)"
    ),
    destroy=extend_schema(summary="Delete a book (admin only)"),
)
class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    queryset = Book.objects.all()
    permission_classes = (IsAdminOrReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List borrowings",
        description="Regular users see only their own borrowings. Staff see all borrowings "
        "and can filter by `user_id`.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                type=int,
                description="Filter by user ID (staff only).",
                required=False,
            ),
            OpenApiParameter(
                name="is_active",
                type=str,
                description="Filter by active status: 'true' for not yet returned, "
                "'false' for already returned.",
                required=False,
            ),
        ],
    ),
    retrieve=extend_schema(summary="Retrieve a borrowing"),
    create=extend_schema(
        summary="Create a borrowing",
        description="Creates a borrowing for the authenticated user, decrements book "
        "inventory, and generates a payment.",
    ),
)
class BorrowingViewSet(viewsets.ModelViewSet):
    serializer_class = BorrowingSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ["get", "post", "head", "options"]

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

    @extend_schema(
        summary="Return a borrowed book",
        description="Marks the borrowing as returned, restores book inventory by 1, "
        "and creates a return payment if applicable.",
        request=None,
        responses={
            200: BorrowingSerializer,
            400: OpenApiParameter(
                name="detail", type=str, description="Already returned."
            ),
        },
    )
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


@extend_schema_view(
    list=extend_schema(
        summary="List payments",
        description="Regular authenticated users see only their own payments. "
        "Admins see all payments.",
    ),
    retrieve=extend_schema(summary="Retrieve a payment"),
)
class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(borrowing__user=user)


class PaymentSuccessView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"detail": "Missing session_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.confirm_from_session(session_id)
        if payment is None:
            return Response(
                {"detail": "Payment not found or not completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Payment successful.", "payment_id": payment.id},
            status=status.HTTP_200_OK,
        )


class PaymentCancelView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response(
            {"detail": "Payment was cancelled."},
            status=status.HTTP_200_OK,
        )
