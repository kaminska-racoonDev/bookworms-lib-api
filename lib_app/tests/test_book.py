from lib_app.serializers import BookSerializer
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status
from lib_app.helpers import (
    create_book,
)


User = get_user_model()


class BookUnauthTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_book_list(self):
        url = reverse("lib_app:book-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_detail(self):
        book = create_book()
        url = reverse("lib_app:book-detail", kwargs={"pk": book.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_create(self):
        book = create_book()
        url = reverse("lib_app:book-detail")
        response = self.client.post(url, book)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_book_update(self):
        book = create_book()
        url = reverse("lib_app:book-detail", kwargs={"pk": book.pk})
        payload = {
            "title": "1985",
            "author": "J. Orwell",
            "cover": "SOFT",
            "inventory": 2,
            "daily_fee": 40.0
        }
        response = self.client.put(url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_book_patch(self):
        book = create_book()
        payload = {
            "inventory": 50
        }
        url = reverse("lib_app:book-detail", kwargs={"pk": book.pk})
        response = self.client.patch(url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
