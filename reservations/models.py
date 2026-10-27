"""
Reservation models for UniLibrary Management System.
Implements Reservation queue logic (Section 4.5).
"""

from django.db import models
from django.conf import settings


class Reservation(models.Model):
    """
    Represents a student's reservation for a book.
    Queue position is computed (not stored) based on reservation_date ordering.
    """

    class Status(models.TextChoices):
        WAITING = 'WAITING', 'Waiting'
        READY = 'READY', 'Ready'
        FULFILLED = 'FULFILLED', 'Fulfilled'
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reservations',
        help_text="The student who placed the reservation"
    )
    book = models.ForeignKey(
        'catalogue.Book',
        on_delete=models.PROTECT,
        related_name='reservations',
        help_text="The book being reserved"
    )
    copy = models.ForeignKey(
        'catalogue.Copy',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        help_text="The copy held for this reservation (null while WAITING)"
    )
    reservation_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When the reservation was placed; defines queue order"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
        help_text="Current state of the reservation"
    )
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the student was notified that the copy is ready"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Pickup deadline (set when status becomes READY)"
    )

    class Meta:
        db_table = 'reservations_reservation'
        ordering = ['reservation_date', 'id']
        indexes = [
            models.Index(fields=['book', 'status', 'reservation_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'book'],
                condition=models.Q(status__in=['WAITING', 'READY']),
                name='unique_active_reservation_per_student_book'
            )
        ]
        verbose_name = 'Reservation'
        verbose_name_plural = 'Reservations'

    def __str__(self):
        return f"{self.student.full_name} - {self.book.title} ({self.get_status_display()})"

    def queue_position(self):
        """
        Calculates this reservation's position in the queue (Section 4.5).
        Position = number of WAITING reservations for the same book with
        an earlier reservation_date (ties broken by id) plus 1.
        """
        if self.status != self.Status.WAITING:
            return None
        earlier = Reservation.objects.filter(
            book=self.book,
            status=self.Status.WAITING,
        ).filter(
            models.Q(reservation_date__lt=self.reservation_date) |
            models.Q(reservation_date=self.reservation_date, id__lt=self.id)
        ).count()
        return earlier + 1

    @property
    def status_symbol(self):
        """Symbol prefix for greyscale readability (Section 9.5)."""
        symbols = {
            'WAITING': '#',
            'READY': '*',
            'FULFILLED': '+',
            'CANCELLED': '-',
            'EXPIRED': 'X',
        }
        return symbols.get(self.status, '?')

    @property
    def status_class(self):
        """CSS badge class for reservation status."""
        classes = {
            'WAITING': 'warning',
            'READY': 'info',
            'FULFILLED': 'success',
            'CANCELLED': 'grey',
            'EXPIRED': 'danger',
        }
        return classes.get(self.status, 'grey')
