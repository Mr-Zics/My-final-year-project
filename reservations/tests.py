"""
Reservation tests for UniLibrary Management System.
Implements Acceptance Tests T06, T07, T08, T09, T10, T11, T12, T13, T25 from Section 12.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase

from accounts.models import User
from catalogue.models import Category, Book, Copy
from circulation.models import BorrowRecord
from circulation.services import receive_return
from reservations.models import Reservation
from reservations.services import reserve_book, cancel_reservation
from fines.models import Fine
from core.services import seed_default_settings


class ReservationTests(TestCase):
    def setUp(self):
        seed_default_settings()

        self.librarian = User.objects.create_user(
            email="emmanuel.udoh@demo.edu.ng",
            full_name="Emmanuel Udoh",
            password="Password@123",
            role=User.Role.LIBRARIAN,
        )
        self.student1 = User.objects.create_user(
            email="amina.bello@demo.edu.ng",
            full_name="Amina Bello",
            matric_number="2022/CSC/001",
            password="Password@123",
            role=User.Role.STUDENT,
        )
        self.student2 = User.objects.create_user(
            email="chinedu.okafor@demo.edu.ng",
            full_name="Chinedu Okafor",
            matric_number="2022/CSC/002",
            password="Password@123",
            role=User.Role.STUDENT,
        )
        self.student3 = User.objects.create_user(
            email="blessing.etim@demo.edu.ng",
            full_name="Blessing Etim",
            matric_number="2022/CSC/003",
            password="Password@123",
            role=User.Role.STUDENT,
        )

        self.cat = Category.objects.create(category_name="Computer Science", code="CS")
        self.book = Book.objects.create(
            title="Database System Concepts",
            author="Silberschatz",
            isbn="9780000000020",
            category=self.cat,
        )

    def test_T06_reserve_with_available_copy(self):
        """T06: Reserve a book with an available copy -> READY, copy RESERVED, 48h expiry, notification."""
        copy = Copy.objects.create(book=self.book, whereabouts="Shelf CS-1", status='AVAILABLE')

        success, msg, res = reserve_book(self.student1, self.book)
        self.assertTrue(success)
        self.assertEqual(res.status, Reservation.Status.READY)
        self.assertEqual(res.copy, copy)
        copy.refresh_from_db()
        self.assertEqual(copy.status, 'RESERVED')
        self.assertIsNotNone(res.expires_at)
        self.assertIsNotNone(res.notified_at)

    def test_T07_reserve_with_no_available_copy(self):
        """T07: Reserve a book with no available copy -> WAITING, queue position correct."""
        # No available copies
        copy = Copy.objects.create(book=self.book, whereabouts="Shelf CS-1", status='BORROWED')

        success, msg, res = reserve_book(self.student1, self.book)
        self.assertTrue(success)
        self.assertEqual(res.status, Reservation.Status.WAITING)
        self.assertIsNone(res.copy)
        self.assertEqual(res.queue_position(), 1)

    def test_T08_three_students_reserve_in_order(self):
        """T08: Three students reserve one book in order -> Positions 1, 2, 3."""
        # All copies borrowed
        Copy.objects.create(book=self.book, whereabouts="Shelf CS-1", status='BORROWED')

        ok1, m1, r1 = reserve_book(self.student1, self.book)
        ok2, m2, r2 = reserve_book(self.student2, self.book)
        ok3, m3, r3 = reserve_book(self.student3, self.book)

        self.assertTrue(ok1 and ok2 and ok3)
        self.assertEqual(r1.queue_position(), 1)
        self.assertEqual(r2.queue_position(), 2)
        self.assertEqual(r3.queue_position(), 3)

    def test_T09_duplicate_active_reservation_rejected(self):
        """T09: Duplicate active reservation for the same book -> Rejected."""
        reserve_book(self.student1, self.book)
        success, msg, res = reserve_book(self.student1, self.book)
        self.assertFalse(success)
        self.assertIn("already have an active reservation", msg)

    def test_T10_reserve_at_max_loans_rejected(self):
        """T10: Reserve while at max loans -> Rejected with correct reason."""
        today = date.today()
        # Create 3 active loans for student1 (max loans = 3)
        for i in range(3):
            c = Copy.objects.create(book=self.book, whereabouts=f"Shelf-{i}", status='BORROWED')
            BorrowRecord.objects.create(
                student=self.student1,
                copy=c,
                issued_by=self.librarian,
                borrow_date=today,
                due_date=today + timedelta(days=14),
            )

        success, msg, res = reserve_book(self.student1, self.book)
        self.assertFalse(success)
        self.assertIn("maximum limit of 3 borrowed books", msg)

    def test_T11_reserve_with_unpaid_fines_allowed(self):
        """Per project simplification, unpaid fines do NOT block reservations."""
        today = date.today()
        c = Copy.objects.create(book=self.book, whereabouts="Shelf-1", status='AVAILABLE')
        loan = BorrowRecord.objects.create(
            student=self.student1,
            copy=c,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=30),
            due_date=today - timedelta(days=16),
            return_date=today - timedelta(days=10),
        )
        Fine.objects.create(
            borrow_record=loan,
            amount=Decimal('5000.00'),
            status=Fine.Status.UNPAID,
            date_created=today - timedelta(days=10),
        )

        # Reserving copy should succeed even with unpaid fines
        success, msg, res = reserve_book(self.student1, self.book)
        self.assertTrue(success)
        self.assertIsNotNone(res)

    def test_T12_return_copy_when_reservation_waiting(self):
        """T12: Return a copy when a reservation is waiting -> First WAITING becomes READY, copy RESERVED, student notified."""
        today = date.today()
        copy = Copy.objects.create(book=self.book, whereabouts="Shelf-1", status='BORROWED')
        loan = BorrowRecord.objects.create(
            student=self.student2,
            copy=copy,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=5),
            due_date=today + timedelta(days=9),
        )

        # student1 places WAITING reservation
        reserve_book(self.student1, self.book)
        res = Reservation.objects.get(student=self.student1, book=self.book)
        self.assertEqual(res.status, Reservation.Status.WAITING)

        # Return book
        msg, fine = receive_return(loan, self.librarian)
        res.refresh_from_db()
        copy.refresh_from_db()
        self.assertEqual(res.status, Reservation.Status.READY)
        self.assertEqual(res.copy, copy)
        self.assertEqual(copy.status, 'RESERVED')

    def test_T13_return_copy_when_nobody_waiting(self):
        """T13: Return a copy when nobody is waiting -> Copy AVAILABLE."""
        today = date.today()
        copy = Copy.objects.create(book=self.book, whereabouts="Shelf-1", status='BORROWED')
        loan = BorrowRecord.objects.create(
            student=self.student2,
            copy=copy,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=5),
            due_date=today + timedelta(days=9),
        )

        msg, fine = receive_return(loan, self.librarian)
        copy.refresh_from_db()
        self.assertEqual(copy.status, 'AVAILABLE')

    def test_T25_student_cancels_ready_reservation(self):
        """T25: Student cancels a READY reservation -> Cancelled and copy reallocated."""
        copy = Copy.objects.create(book=self.book, whereabouts="Shelf-1", status='AVAILABLE')

        # student1 reserves -> READY
        reserve_book(self.student1, self.book)
        res1 = Reservation.objects.get(student=self.student1, book=self.book)
        self.assertEqual(res1.status, Reservation.Status.READY)

        # student2 reserves -> WAITING
        reserve_book(self.student2, self.book)
        res2 = Reservation.objects.get(student=self.student2, book=self.book)
        self.assertEqual(res2.status, Reservation.Status.WAITING)

        # student1 cancels reservation
        ok, msg = cancel_reservation(res1, self.student1)
        self.assertTrue(ok)
        res1.refresh_from_db()
        self.assertEqual(res1.status, Reservation.Status.CANCELLED)

        # copy should be reallocated to student2 (now READY)
        res2.refresh_from_db()
        copy.refresh_from_db()
        self.assertEqual(res2.status, Reservation.Status.READY)
        self.assertEqual(res2.copy, copy)
        self.assertEqual(copy.status, 'RESERVED')

    def test_cannot_reserve_same_book_twice(self):
        """Verify student cannot place multiple active reservations for the same book."""
        Copy.objects.create(book=self.book, whereabouts="Shelf-1", status='AVAILABLE')

        # First reservation succeeds (READY)
        ok, msg, res = reserve_book(self.student1, self.book)
        self.assertTrue(ok)
        self.assertIsNotNone(res)

        # Second reservation attempt by same student for same book is rejected
        ok2, msg2, res2 = reserve_book(self.student1, self.book)
        self.assertFalse(ok2)
        self.assertIn("already have a reserved copy", msg2)
        self.assertEqual(Reservation.objects.filter(student=self.student1, book=self.book).count(), 1)

    def test_max_reservations_limit_per_student(self):
        """Verify student cannot exceed the maximum active reservations quota (default: 4)."""
        books = [
            Book.objects.create(title=f"Test Book {i}", author="Author", isbn=f"97800000000{i:02d}", category=self.cat)
            for i in range(10, 15)
        ]

        # Place 4 active reservations (allowed)
        for i in range(4):
            ok, msg, res = reserve_book(self.student1, books[i])
            self.assertTrue(ok, f"Reservation {i+1} should succeed: {msg}")

        self.assertEqual(
            Reservation.objects.filter(student=self.student1, status__in=[Reservation.Status.WAITING, Reservation.Status.READY]).count(),
            4
        )

        # 5th reservation attempt must be rejected
        ok5, msg5, res5 = reserve_book(self.student1, books[4])
        self.assertFalse(ok5)
        self.assertIn("reached the maximum limit of 4 active reservations", msg5)
        self.assertIsNone(res5)
