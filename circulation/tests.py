"""
Circulation tests for UniLibrary Management System.
Tests borrowing, return, fine calculations (₦50/day), 14-day loan duration,
and maximum 3 loans per student quota.
Loan renewals and fine-block restrictions have been removed.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase

from accounts.models import User
from catalogue.models import Category, Book, Copy
from circulation.models import BorrowRecord
from circulation.services import (
    issue_copy,
    receive_return,
    check_borrow_eligibility,
)
from reservations.models import Reservation
from reservations.services import reserve_book
from fines.models import Fine


class CirculationTests(TestCase):
    def setUp(self):
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
        self.cat = Category.objects.create(category_name="Computer Science", code="CS")
        self.book = Book.objects.create(
            title="Algorithms",
            author="Cormen",
            isbn="9780000000010",
            category=self.cat,
        )
        self.copy1 = Copy.objects.create(book=self.book, whereabouts="Shelf CS-1", status='AVAILABLE')
        self.copy2 = Copy.objects.create(book=self.book, whereabouts="Shelf CS-2", status='AVAILABLE')

    def test_return_copy_4_days_late(self):
        """Return a copy 4 days late at ₦50/day -> Fine of ₦200 UNPAID created."""
        today = date.today()
        loan = BorrowRecord.objects.create(
            student=self.student1,
            copy=self.copy1,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=18),
            due_date=today - timedelta(days=4),  # 4 days overdue
        )
        self.copy1.status = 'BORROWED'
        self.copy1.save()

        msg, fine = receive_return(loan, self.librarian)
        self.assertEqual(fine, Decimal('200.00'))  # 4 days late * ₦50/day
        self.assertTrue(Fine.objects.filter(borrow_record=loan, amount=Decimal('200.00'), status=Fine.Status.UNPAID).exists())

    def test_return_copy_on_time(self):
        """Return a copy on time -> No fine created."""
        today = date.today()
        loan = BorrowRecord.objects.create(
            student=self.student1,
            copy=self.copy1,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=5),
            due_date=today + timedelta(days=9),
        )
        self.copy1.status = 'BORROWED'
        self.copy1.save()

        msg, fine = receive_return(loan, self.librarian)
        self.assertIsNone(fine)
        self.assertFalse(Fine.objects.filter(borrow_record=loan).exists())

    def test_issue_held_copy_to_reserving_student(self):
        """Issue a held copy to the reserving student -> Loan created, reservation FULFILLED, copy BORROWED, due in 14 days."""
        success, msg, res = reserve_book(self.student1, self.book)
        self.assertTrue(success)
        self.assertEqual(res.status, Reservation.Status.READY)
        held_copy = res.copy

        # Issue held copy to student1
        ok, issue_msg, record = issue_copy(self.student1, held_copy, self.librarian)
        self.assertTrue(ok)
        self.assertIsNotNone(record)
        self.assertEqual(record.due_date, date.today() + timedelta(days=14))
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.Status.FULFILLED)
        held_copy.refresh_from_db()
        self.assertEqual(held_copy.status, 'BORROWED')

    def test_issue_held_copy_to_different_student_rejected(self):
        """Issue a held copy to a different student -> Rejected."""
        success, msg, res = reserve_book(self.student1, self.book)
        held_copy = res.copy

        # Attempt to issue to student2
        ok, issue_msg, record = issue_copy(self.student2, held_copy, self.librarian)
        self.assertFalse(ok)
        self.assertIn("reserved for", issue_msg)
        self.assertIsNone(record)

    def test_maximum_three_loans_enforced(self):
        """A student cannot borrow more than 3 books at a time."""
        today = date.today()
        # Create 3 active loans for student1
        for i in range(3):
            c = Copy.objects.create(book=self.book, whereabouts=f"Shelf CS-{i+10}", status='AVAILABLE')
            BorrowRecord.objects.create(
                student=self.student1,
                copy=c,
                issued_by=self.librarian,
                borrow_date=today,
                due_date=today + timedelta(days=14),
            )

        # 4th borrow must be blocked
        ok, reason = check_borrow_eligibility(self.student1)
        self.assertFalse(ok)
        self.assertIn("maximum limit of 3 borrowed books", reason)

        # Direct issue must also be rejected
        extra_copy = Copy.objects.create(book=self.book, whereabouts="Shelf CS-99", status='AVAILABLE')
        ok_issue, msg_issue, _ = issue_copy(self.student1, extra_copy, self.librarian)
        self.assertFalse(ok_issue)
        self.assertIn("maximum limit of 3", msg_issue)

    def test_unpaid_fines_do_not_block_borrowing(self):
        """Per project simplification, unpaid fines do NOT block borrowing."""
        # Create an unpaid fine for student1
        dummy_loan = BorrowRecord.objects.create(
            student=self.student1,
            copy=self.copy1,
            issued_by=self.librarian,
            borrow_date=date.today() - timedelta(days=30),
            due_date=date.today() - timedelta(days=16),
            return_date=date.today() - timedelta(days=10),
        )
        Fine.objects.create(
            borrow_record=dummy_loan,
            amount=Decimal('5000.00'),
            status=Fine.Status.UNPAID,
            date_created=date.today(),
        )

        # Student has 0 active loans and ₦5000 in unpaid fines -> Borrowing is allowed
        ok, reason = check_borrow_eligibility(self.student1)
        self.assertTrue(ok)
        self.assertIsNone(reason)
