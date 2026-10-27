"""
Fine tests for UniLibrary Management System.
Tests fine payment recording. Waivers have been removed.
"""

from datetime import date
from decimal import Decimal
from django.test import TestCase

from accounts.models import User
from catalogue.models import Category, Book, Copy
from circulation.models import BorrowRecord
from circulation.services import get_unpaid_fines_total
from fines.models import Fine
from fines.services import record_payment


class FineTests(TestCase):
    def setUp(self):
        self.librarian = User.objects.create_user(
            email="emmanuel.udoh@demo.edu.ng",
            full_name="Emmanuel Udoh",
            password="Password@123",
            role=User.Role.LIBRARIAN,
        )
        self.student = User.objects.create_user(
            email="amina.bello@demo.edu.ng",
            full_name="Amina Bello",
            matric_number="2022/CSC/001",
            password="Password@123",
            role=User.Role.STUDENT,
        )
        self.cat = Category.objects.create(category_name="Computer Science", code="CS")
        self.book = Book.objects.create(
            title="Clean Code",
            author="Martin",
            isbn="9780000000070",
            category=self.cat,
        )
        self.copy = Copy.objects.create(book=self.book, whereabouts="Shelf CS-1", status='AVAILABLE')
        self.loan = BorrowRecord.objects.create(
            student=self.student,
            copy=self.copy,
            issued_by=self.librarian,
            borrow_date=date.today(),
            due_date=date.today(),
            return_date=date.today(),
        )

    def test_record_payment(self):
        """Record fine payment: status becomes PAID with receipt reference, excluded from unpaid total."""
        fine = Fine.objects.create(
            borrow_record=self.loan,
            amount=Decimal('200.00'),
            status=Fine.Status.UNPAID,
            date_created=date.today(),
        )
        self.assertEqual(get_unpaid_fines_total(self.student), Decimal('200.00'))

        success, msg = record_payment(fine, self.librarian, "RCPT-9999")
        self.assertTrue(success)
        fine.refresh_from_db()
        self.assertEqual(fine.status, Fine.Status.PAID)
        self.assertEqual(fine.payment_reference, "RCPT-9999")
        self.assertEqual(fine.recorded_by, self.librarian)
        self.assertEqual(get_unpaid_fines_total(self.student), Decimal('0.00'))

    def test_cannot_pay_already_paid_fine(self):
        """Attempting to pay an already paid fine is rejected."""
        fine = Fine.objects.create(
            borrow_record=self.loan,
            amount=Decimal('100.00'),
            status=Fine.Status.PAID,
            date_created=date.today(),
            payment_reference="RCPT-001",
        )
        success, msg = record_payment(fine, self.librarian, "RCPT-002")
        self.assertFalse(success)
        self.assertIn("Only unpaid fines", msg)
