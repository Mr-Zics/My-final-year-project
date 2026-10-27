"""
Fine models for UniLibrary Management System.
Implements Fine for tracking overdue penalties and payments.
Fines have only two statuses: Unpaid or Paid.
"""

from django.db import models
from django.conf import settings


class Fine(models.Model):
    """
    Represents an overdue fine created when a copy is returned late.
    A fine is only Unpaid or Paid. Waivers have been removed.
    """

    class Status(models.TextChoices):
        UNPAID = 'UNPAID', 'Unpaid'
        PAID = 'PAID', 'Paid'

    borrow_record = models.ForeignKey(
        'circulation.BorrowRecord',
        on_delete=models.PROTECT,
        related_name='fines',
        help_text="The loan that incurred this fine"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Fine amount in Nigerian Naira"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID,
        help_text="Current payment status (Unpaid or Paid)"
    )
    date_created = models.DateField(
        help_text="Date the fine was recorded (when the book was returned late)"
    )
    date_paid = models.DateField(
        null=True,
        blank=True,
        help_text="Date the fine was paid"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_fines',
        help_text="Librarian who recorded the payment"
    )
    payment_reference = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Receipt number for offline payment"
    )

    class Meta:
        db_table = 'fines_fine'
        ordering = ['-date_created']
        verbose_name = 'Fine'
        verbose_name_plural = 'Fines'

    def __str__(self):
        return (f"Fine #{self.id} - {self.borrow_record.student.full_name} - "
                f"N{self.amount} ({self.get_status_display()})")

    @property
    def status_symbol(self):
        """Symbol prefix for greyscale readability."""
        symbols = {
            'UNPAID': '!',
            'PAID': '+',
        }
        return symbols.get(self.status, '?')

    @property
    def status_class(self):
        """CSS badge class for fine status."""
        classes = {
            'UNPAID': 'danger',
            'PAID': 'success',
        }
        return classes.get(self.status, 'grey')
