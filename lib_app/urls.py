from django.urls import path, include
from rest_framework import routers
from lib_app.views import BookViewSet

app_name = "lib_app"


router = routers.DefaultRouter()
router.register("book", BookViewSet)

urlpatterns = [
    path("", include(router.urls))
]
