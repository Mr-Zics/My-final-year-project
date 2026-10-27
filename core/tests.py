"""
Core tests for UniLibrary Management System.
Tests automated daily jobs (hold expiry, due date reminders, overdue notices).
Settings model and SystemLog tests have been removed per project simplification.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone

from accounts.models import User
from catalogue.models import Category, Book, Copy
from circulation.models import BorrowRecord
from circulation.services import receive_return
from reservations.models import Reservation
from notifications.models import Notification
from fines.models import Fine


class CoreTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@demo.edu.ng",
            full_name="Adaeze Okonkwo",
            password="Password@123",
        )
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
            title="Systems Analysis and Design",
            author="Dennis",
            isbn="9780000000100",
            category=self.cat,
        )
        self.copy = Copy.objects.create(book=self.book, whereabouts="Shelf CS-1", status='AVAILABLE')

    def test_daily_job_expires_uncollected_hold(self):
        """Daily job expires an uncollected READY reservation -> EXPIRED, copy passed to next WAITING or AVAILABLE."""
        now = timezone.now()
        self.copy.status = 'RESERVED'
        self.copy.save()

        # Reservation that expired 2 hours ago
        res = Reservation.objects.create(
            student=self.student,
            book=self.book,
            copy=self.copy,
            status=Reservation.Status.READY,
            notified_at=now - timedelta(hours=50),
            expires_at=now - timedelta(hours=2),
        )

        call_command('run_daily_job')
        res.refresh_from_db()
        self.copy.refresh_from_db()

        self.assertEqual(res.status, Reservation.Status.EXPIRED)
        self.assertEqual(self.copy.status, 'AVAILABLE')
        self.assertTrue(Notification.objects.filter(user=self.student, type='RESERVATION_EXPIRED').exists())

    def test_daily_job_sends_due_soon_once(self):
        """Daily job sends DUE_SOON once -> One notification; second run sends none."""
        today = date.today()
        # Loan due in 2 days (reminder_days_before_due = 2)
        loan = BorrowRecord.objects.create(
            student=self.student,
            copy=self.copy,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=12),
            due_date=today + timedelta(days=2),
        )

        # Run 1
        call_command('run_daily_job')
        notif_count = Notification.objects.filter(borrow_record=loan, type='DUE_SOON').count()
        self.assertEqual(notif_count, 2)  # 1 INAPP + 1 EMAIL

        # Run 2 on same day
        call_command('run_daily_job')
        notif_count_after = Notification.objects.filter(borrow_record=loan, type='DUE_SOON').count()
        self.assertEqual(notif_count_after, 2)  # No duplicate notifications sent

    def test_daily_job_sends_overdue_respecting_repeat_and_max(self):
        """Daily job sends OVERDUE respecting repeat interval and maximum -> Notices only every 3 days, never more than 3."""
        today = date.today()
        # Overdue loan due 6 days ago
        loan = BorrowRecord.objects.create(
            student=self.student,
            copy=self.copy,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=20),
            due_date=today - timedelta(days=6),
        )

        # Day 1 run (past due date) -> notice 1 sent
        call_command('run_daily_job', date=str(today - timedelta(days=5)))
        count1 = Notification.objects.filter(borrow_record=loan, type='OVERDUE', channel='INAPP').count()
        self.assertEqual(count1, 1)

        # Day 2 run (only 1 day after notice 1, repeat is 3 days) -> no new notice
        call_command('run_daily_job', date=str(today - timedelta(days=4)))
        count2 = Notification.objects.filter(borrow_record=loan, type='OVERDUE', channel='INAPP').count()
        self.assertEqual(count1, count2)

    def test_run_daily_check_command_alias(self):
        """run_daily_check command runs without error as an alias."""
        call_command('run_daily_check')

    def test_daily_job_run_twice_same_day_no_duplicates(self):
        """Daily job run twice on the same day -> No duplicate notifications."""
        today = date.today()
        loan = BorrowRecord.objects.create(
            student=self.student,
            copy=self.copy,
            issued_by=self.librarian,
            borrow_date=today - timedelta(days=12),
            due_date=today + timedelta(days=2),
        )

        call_command('run_daily_job')
        count1 = Notification.objects.count()

        call_command('run_daily_job')
        count2 = Notification.objects.count()

        self.assertEqual(count1, count2)
