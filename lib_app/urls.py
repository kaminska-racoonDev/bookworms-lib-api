from django.urls import path, include
from rest_framework import routers
from lib_app.views import (
    BookViewSet,
    BorrowingViewSet,
    PaymentViewSet,
)

app_name = "lib_app"


router = routers.DefaultRouter()
router.register("book", BookViewSet)
router.register("borrowing", BorrowingViewSet, basename="borrowing")
router.register("payments", PaymentViewSet, basename="payment")

urlpatterns = [path("", include(router.urls))]
