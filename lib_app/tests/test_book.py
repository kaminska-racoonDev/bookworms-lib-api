from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status

from lib_app.helpers import create_book

User = get_user_model()


class BookBaseTestClass(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("lib_app:book-list")
        self.payload = {
            "title": "1984",
            "author": "G. Orwell",
            "cover": "SOFT",
            "inventory": 2,
            "daily_fee": 40.0,
        }

    def detail_url(self, pk):
        return reverse("lib_app:book-detail", kwargs={"pk": pk})


class BookUnauthTest(BookBaseTestClass):
    def test_book_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_detail(self):
        book = create_book()
        response = self.client.get(self.detail_url(book.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_create_forbidden(self):
        response = self.client.post(self.list_url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_update_forbidden(self):
        book = create_book()
        response = self.client.put(self.detail_url(book.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_patch_forbidden(self):
        book = create_book()
        response = self.client.patch(
            self.detail_url(book.pk), {"inventory": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_delete_forbidden(self):
        book = create_book()
        response = self.client.delete(self.detail_url(book.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BookAuthTest(BookBaseTestClass):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_book_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_detail(self):
        book = create_book()
        response = self.client.get(self.detail_url(book.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_create_forbidden(self):
        response = self.client.post(self.list_url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_update_forbidden(self):
        book = create_book()
        response = self.client.put(self.detail_url(book.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_patch_forbidden(self):
        book = create_book()
        response = self.client.patch(
            self.detail_url(book.pk), {"inventory": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_delete_forbidden(self):
        book = create_book()
        response = self.client.delete(self.detail_url(book.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BookAdminTest(BookBaseTestClass):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_superuser(
            email="admin@test.com", password="admin.pass.test"
        )
        self.client.force_authenticate(user=self.user)

    def test_book_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_detail(self):
        book = create_book()
        response = self.client.get(self.detail_url(book.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_create(self):
        response = self.client.post(self.list_url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_book_update(self):
        book = create_book()
        response = self.client.put(self.detail_url(book.pk), self.payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_patch(self):
        book = create_book()
        response = self.client.patch(
            self.detail_url(book.pk), {"inventory": 1}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_delete(self):
        book = create_book()
        response = self.client.delete(self.detail_url(book.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
