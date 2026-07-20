from django.shortcuts import render
from rest_framework import viewsets, mixins
from lib_app.serializers import (
    BookSerializer,
)
from lib_app.models import (
    Book,
)


class BookViewSet(
        mixins.ListModelMixin,
        mixins.CreateModelMixin,
        mixins.UpdateModelMixin,
        mixins.DestroyModelMixin,
        mixins.RetrieveModelMixin,
        viewsets.GenericViewSet):
    serializer_class = BookSerializer
    queryset = Book.objects.all()
