import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status
from lib_app.helpers import create_book, create_borrowing
from lib_app.models import Payment

User = get_user_model()


class BorrowingBaseTestClass(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("lib_app:borrowing-list")

    def detail_url(self, pk):
        return reverse("lib_app:borrowing-detail", kwargs={"pk": pk})

    def return_url(self, pk):
        return reverse("lib_app:borrowing-return-borrowing", kwargs={"pk": pk})


class BorrowingUnauthTest(BorrowingBaseTestClass):
    def test_borrowing_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_borrowing_detail(self):
        borrowing = create_borrowing()
        response = self.client.get(self.detail_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_borrowing_create_forbidden(self):
        book = create_book()
        response = self.client.post(
            self.list_url,
            {
                "expected_return_date": "2026-08-15",
                "book_borrowed": book.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_borrowing_return_forbidden(self):
        borrowing = create_borrowing()
        response = self.client.post(self.return_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BorrowingAuthTest(BorrowingBaseTestClass):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_borrowing_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_borrowing_detail_own(self):
        borrowing = create_borrowing(user=self.user)
        response = self.client.get(self.detail_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_borrowing_detail_others_not_found(self):
        other_user = User.objects.create_user(
            email="other@test.com", password="pass1234"
        )
        borrowing = create_borrowing(user=other_user)
        response = self.client.get(self.detail_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_borrowing_list_only_own_borrowings(self):
        own = create_borrowing(user=self.user)
        other_user = User.objects.create_user(
            email="other2@test.com", password="pass1234"
        )
        other = create_borrowing(user=other_user)

        response = self.client.get(self.list_url)
        returned_ids = [b["id"] for b in response.data]

        self.assertIn(own.id, returned_ids)
        self.assertNotIn(other.id, returned_ids)

    def test_borrowing_filtering_is_active_true(self):
        active = create_borrowing(user=self.user)
        returned = create_borrowing(
            user=self.user,
            actual_return_date=datetime.date.today(),
        )
        response = self.client.get(self.list_url, {"is_active": "true"})
        returned_ids = [b["id"] for b in response.data]

        self.assertIn(active.id, returned_ids)
        self.assertNotIn(returned.id, returned_ids)

    def test_borrowing_filtering_is_active_false(self):
        active = create_borrowing(user=self.user)
        returned = create_borrowing(
            user=self.user,
            actual_return_date=datetime.date.today(),
        )
        response = self.client.get(self.list_url, {"is_active": "false"})
        returned_ids = [b["id"] for b in response.data]

        self.assertIn(returned.id, returned_ids)
        self.assertNotIn(active.id, returned_ids)

    def test_borrowing_create_success(self):
        book = create_book(inventory=3)
        response = self.client.post(
            self.list_url,
            {
                "borrow_date": datetime.date.today().isoformat(),
                "expected_return_date": (
                    datetime.date.today() + datetime.timedelta(days=14)
                ).isoformat(),
                "book_borrowed": book.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        book.refresh_from_db()
        self.assertEqual(book.inventory, 2)

        borrowing_id = response.data["id"]
        self.assertTrue(
            Payment.objects.filter(
                borrowing_id=borrowing_id,
                type=Payment.PaymentType.PAYMENT,
            ).exists()
        )

    def test_borrowing_create_ignores_supplied_user(self):
        other_user = User.objects.create_user(
            email="other3@test.com", password="pass1234"
        )
        book = create_book()
        response = self.client.post(
            self.list_url,
            {
                "borrow_date": datetime.date.today().isoformat(),
                "expected_return_date": (
                    datetime.date.today() + datetime.timedelta(days=14)
                ).isoformat(),
                "book_borrowed": book.id,
                "user": other_user.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.user.id)

    def test_borrowing_return_own_success(self):
        borrow_date = datetime.date.today() - datetime.timedelta(days=5)
        expected_return = datetime.date.today() + datetime.timedelta(days=2)
        book = create_book(inventory=1)
        borrowing = create_borrowing(
            user=self.user,
            book_borrowed=book,
            borrow_date=borrow_date,
            expected_return_date=expected_return,
        )

        response = self.client.post(self.return_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        borrowing.refresh_from_db()
        book.refresh_from_db()

        self.assertEqual(borrowing.actual_return_date, timezone.now().date())
        self.assertEqual(book.inventory, 2)

    def test_borrowing_return_creates_fine_if_late(self):
        borrow_date = datetime.date.today() - datetime.timedelta(days=10)
        expected_return = datetime.date.today() - datetime.timedelta(days=3)
        book = create_book(daily_fee=10)
        borrowing = create_borrowing(
            user=self.user,
            book_borrowed=book,
            borrow_date=borrow_date,
            expected_return_date=expected_return,
        )

        response = self.client.post(self.return_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fine = Payment.objects.filter(
            borrowing=borrowing, type=Payment.PaymentType.FINE
        ).first()
        self.assertIsNotNone(fine)
        # 3 days late * daily_fee(10) * FINE_MULTIPLIER(2)
        self.assertEqual(fine.money_to_pay, 60)

    def test_borrowing_return_no_fine_if_on_time(self):
        borrow_date = datetime.date.today() - datetime.timedelta(days=5)
        expected_return = datetime.date.today() + datetime.timedelta(days=2)
        borrowing = create_borrowing(
            user=self.user,
            borrow_date=borrow_date,
            expected_return_date=expected_return,
        )

        response = self.client.post(self.return_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(
            Payment.objects.filter(
                borrowing=borrowing, type=Payment.PaymentType.FINE
            ).exists()
        )

    def test_borrowing_return_already_returned_fails(self):
        borrowing = create_borrowing(
            user=self.user,
            actual_return_date=datetime.date.today(),
        )
        response = self.client.post(self.return_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_borrowing_return_others_not_found(self):
        other_user = User.objects.create_user(
            email="other4@test.com", password="pass1234"
        )
        borrowing = create_borrowing(user=other_user)
        response = self.client.post(self.return_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_borrowing_update_not_allowed(self):
        borrowing = create_borrowing(user=self.user)
        response = self.client.patch(
            self.detail_url(borrowing.pk),
            {"expected_return_date": "2026-12-31"},
        )
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_borrowing_delete_not_allowed(self):
        borrowing = create_borrowing(user=self.user)
        response = self.client.delete(self.detail_url(borrowing.pk))
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


class BorrowingAdminTest(BorrowingBaseTestClass):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_superuser(
            email="admin@test.com", password="admin.pass.test"
        )
        self.client.force_authenticate(user=self.user)

    def test_borrowing_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_borrowing_all_borrowings_shown(self):
        own = create_borrowing(user=self.user)
        other_user = User.objects.create_user(
            email="other5@test.com", password="pass1234"
        )
        other = create_borrowing(user=other_user)

        response = self.client.get(self.list_url)
        returned_ids = [b["id"] for b in response.data]

        self.assertIn(own.id, returned_ids)
        self.assertIn(other.id, returned_ids)

    def test_borrowing_filtering_by_user_id(self):
        target_user = User.objects.create_user(
            email="other6@test.com", password="pass1234"
        )
        target_borrowing = create_borrowing(user=target_user)
        create_borrowing(user=self.user)

        response = self.client.get(self.list_url, {"user_id": target_user.id})
        returned_ids = [b["id"] for b in response.data]

        self.assertEqual(returned_ids, [target_borrowing.id])

    def test_borrowing_detail(self):
        borrowing = create_borrowing()
        response = self.client.get(self.detail_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_borrowing_return_any_users_borrowing(self):
        other_user = User.objects.create_user(
            email="other7@test.com", password="pass1234"
        )
        book = create_book(inventory=1)
        borrowing = create_borrowing(user=other_user, book_borrowed=book)

        response = self.client.post(self.return_url(borrowing.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
