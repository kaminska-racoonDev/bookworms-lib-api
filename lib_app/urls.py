from django.urls import path, include
from rest_framework import routers
from lib_app.views import (
    BookViewSet,
    BorrowingViewSet,
    PaymentViewSet,
    PaymentSuccessView,
    PaymentCancelView,
)

app_name = "lib_app"


router = routers.DefaultRouter()
router.register("book", BookViewSet)
router.register("borrowing", BorrowingViewSet, basename="borrowing")
router.register("payments", PaymentViewSet, basename="payment")


urlpatterns = [
    path("payments/success/", PaymentSuccessView.as_view(), name="payment-success"),
    path("payments/cancel/", PaymentCancelView.as_view(), name="payment-cancel"),
    path("", include(router.urls)),
]
