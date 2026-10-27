"""
Notification models for UniLibrary Management System.
Implements Notification (Section 4.8) for in-app and email alerts.
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Stores notification records for students (in-app and email).
    Each event creates one INAPP row; certain events also create an EMAIL row.
    """

    class Type(models.TextChoices):
        RESERVATION_CONFIRMED = 'RESERVATION_CONFIRMED', 'Reservation Confirmed'
        RESERVATION_READY = 'RESERVATION_READY', 'Reservation Ready'
        RESERVATION_EXPIRED = 'RESERVATION_EXPIRED', 'Reservation Expired'
        DUE_SOON = 'DUE_SOON', 'Due Soon Reminder'
        OVERDUE = 'OVERDUE', 'Overdue Notice'

    class Channel(models.TextChoices):
        INAPP = 'INAPP', 'In-App'
        EMAIL = 'EMAIL', 'Email'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user receiving the notification"
    )
    borrow_record = models.ForeignKey(
        'circulation.BorrowRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Related loan (for DUE_SOON and OVERDUE notifications)"
    )
    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Related reservation (for RESERVATION_* notifications)"
    )
    type = models.CharField(
        max_length=30,
        choices=Type.choices,
        help_text="Type of notification"
    )
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.INAPP,
        help_text="Delivery channel: in-app or email"
    )
    message = models.CharField(
        max_length=500,
        help_text="Notification message text"
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the user has read this notification"
    )
    date_sent = models.DateTimeField(
        help_text="When the notification was sent"
    )

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-date_sent']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.get_type_display()} for {self.user.full_name}"

    @property
    def type_icon(self):
        """Icon for notification type display."""
        icons = {
            'RESERVATION_CONFIRMED': '#',
            'RESERVATION_READY': '*',
            'RESERVATION_EXPIRED': 'X',
            'DUE_SOON': '~',
            'OVERDUE': '!',
        }
        return icons.get(self.type, '?')
