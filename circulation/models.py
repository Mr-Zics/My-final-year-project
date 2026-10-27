"""
Circulation models for UniLibrary Management System.
Implements BorrowRecord (Section 4.6) for tracking book loans.
"""

from datetime import date
from decimal import Decimal
from django.db import models
from django.conf import settings
from core.services import get_int, get_decimal


class BorrowRecord(models.Model):
    """
    Represents a single loan of a physical copy to a student.
    A loan is active while return_date is null.
    Fine calculations for active overdue loans are computed dynamically (not stored).
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='borrow_records',
        help_text="The student borrower"
    )
    copy = models.ForeignKey(
        'catalogue.Copy',
        on_delete=models.PROTECT,
        related_name='borrow_records',
        help_text="The physical copy being borrowed"
    )
    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='borrow_records',
        help_text="The reservation this loan fulfils (null for walk-ins)"
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='issued_records',
        help_text="The librarian who issued the copy"
    )
    borrow_date = models.DateField(
        help_text="Date the copy was issued to the student"
    )
    due_date = models.DateField(
        help_text="Date the copy must be returned"
    )
    return_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the copy was returned (null = still on loan)"
    )

    class Meta:
        db_table = 'circulation_borrowrecord'
        ordering = ['-borrow_date']
        verbose_name = 'Borrow Record'
        verbose_name_plural = 'Borrow Records'

    def __str__(self):
        status = 'Active' if self.is_active else 'Returned'
        return f"{self.student.full_name} - {self.copy.book.title} ({status})"

    @property
    def is_active(self):
        """A loan is active while return_date is null."""
        return self.return_date is None

    @property
    def is_overdue(self):
        """Active loan past due date."""
        return self.is_active and self.due_date < date.today()

    @property
    def days_overdue(self):
        """Number of days past due date (0 if not overdue or returned)."""
        if not self.is_active:
            # For returned loans, calculate based on return_date
            if self.return_date and self.return_date > self.due_date:
                return (self.return_date - self.due_date).days
            return 0
        if self.due_date < date.today():
            return (date.today() - self.due_date).days
        return 0

    @property
    def days_remaining(self):
        """Days until due date (negative if overdue)."""
        if not self.is_active:
            return 0
        return (self.due_date - date.today()).days

    @property
    def estimated_fine(self):
        """
        Estimated fine for display on active overdue loans.
        This is NOT stored — it's computed dynamically (Section 4.6).
        """
        if self.days_overdue > 0:
            fine_per_day = get_decimal('fine_per_day')
            return self.days_overdue * fine_per_day
        return Decimal('0.00')

    @property
    def status_display(self):
        """Returns a human-readable status with symbol for greyscale compatibility."""
        if not self.is_active:
            return 'Returned'
        if self.days_remaining <= 0:
            return '! Overdue'
        elif self.days_remaining <= get_int('reminder_days_before_due'):
            return 'Due soon'
        return 'On time'

    @property
    def status_class(self):
        """CSS class for the status badge."""
        if not self.is_active:
            return 'grey'
        if self.days_remaining <= 0:
            return 'danger'
        elif self.days_remaining <= get_int('reminder_days_before_due'):
            return 'warning'
        return 'success'

    @property
    def status_symbol(self):
        """Symbol prefix for greyscale readability (Section 9.5)."""
        if not self.is_active:
            return '-'
        if self.days_remaining <= 0:
            return '!'
        elif self.days_remaining <= get_int('reminder_days_before_due'):
            return '~'
        return '+'
