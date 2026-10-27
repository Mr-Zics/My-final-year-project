"""
Notification and email delivery services for UniLibrary Management System.
Handles in-app notification persistence and real email dispatch via Django's EmailMultiAlternatives.
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from core.services import log_action
from notifications.models import Notification


# Events that trigger real email notifications to the borrower/student
EMAIL_TRIGGER_EVENTS = {
    'RESERVATION_READY',
    'DUE_SOON',
    'OVERDUE',
    Notification.Type.RESERVATION_READY,
    Notification.Type.DUE_SOON,
    Notification.Type.OVERDUE,
}


def send_notification(user, notification_type, message, reservation=None, borrow_record=None, send_email=False):
    """
    Creates an in-app notification, and sends an email to the user's registered email
    for RESERVATION_READY, DUE_SOON, and OVERDUE events.
    
    If email delivery fails (e.g. no internet or authentication error), the error is
    logged to SystemLog and does not crash, leaving the in-app notification intact.
    """
    now = timezone.now()

    # 1. Always create the INAPP notification record
    inapp_notif = Notification.objects.create(
        user=user,
        type=notification_type,
        channel=Notification.Channel.INAPP,
        message=message,
        reservation=reservation,
        borrow_record=borrow_record,
        date_sent=now,
    )

    # 2. Check if this notification event requires email delivery
    should_email = send_email or (notification_type in EMAIL_TRIGGER_EVENTS)

    if should_email and notification_type in EMAIL_TRIGGER_EVENTS:
        recipient_email = getattr(user, 'email', None)
        if not recipient_email:
            log_action(user, 'EMAIL_FAILED', f"Cannot send {notification_type} email: User {user.full_name} has no email address.")
            return inapp_notif

        # Extract book title and relevant date
        book_title = "Unknown Book"
        if reservation:
            if getattr(reservation, 'book', None):
                book_title = reservation.book.title
            elif getattr(reservation, 'copy', None) and getattr(reservation.copy, 'book', None):
                book_title = reservation.copy.book.title
        elif borrow_record:
            if getattr(borrow_record, 'copy', None) and getattr(borrow_record.copy, 'book', None):
                book_title = borrow_record.copy.book.title

        subject = ""
        plain_message = ""
        badge_text = "Notice"
        badge_bg = "#E2E8F0"
        badge_color = "#1A365D"
        lead_text = ""
        detail_label = "Date"
        detail_value = ""
        action_text = ""

        if notification_type in ['RESERVATION_READY', Notification.Type.RESERVATION_READY]:
            deadline_str = "the stated pickup deadline"
            if reservation and getattr(reservation, 'expires_at', None):
                deadline_str = reservation.expires_at.strftime('%d/%m/%Y at %H:%M')

            subject = f"UniLibrary: Reserved Book Ready for Collection - {book_title}"
            badge_text = "Ready for Collection"
            badge_bg = "#EBF8FF"
            badge_color = "#2B6CB0"
            lead_text = f"Good news! Your reserved physical textbook '{book_title}' is held and ready for you at the library circulation desk."
            detail_label = "Pickup Deadline"
            detail_value = deadline_str
            action_text = f"Please collect this book on or before {deadline_str}. If uncollected by then, your reservation will expire and the copy will automatically pass to the next student in the queue."
            plain_message = (
                f"Dear {user.full_name},\n\n"
                f"Good news! Your reserved book '{book_title}' is now ready for collection at the UniLibrary circulation desk.\n\n"
                f"Pickup Deadline: {deadline_str}\n\n"
                f"Please collect this book on or before the deadline. If uncollected by then, your reservation will expire and the book will pass to the next student in the queue.\n\n"
                f"Thank you,\n"
                f"UniLibrary Circulation Desk"
            )

        elif notification_type in ['DUE_SOON', Notification.Type.DUE_SOON]:
            due_str = "the scheduled due date"
            if borrow_record and getattr(borrow_record, 'due_date', None):
                due_str = borrow_record.due_date.strftime('%d/%m/%Y')

            subject = f"UniLibrary Reminder: '{book_title}' Due Soon"
            badge_text = "Due Date Reminder"
            badge_bg = "#FEFCBF"
            badge_color = "#975A16"
            lead_text = f"This is an automated reminder that your borrowed textbook '{book_title}' is scheduled for return on {due_str}."
            detail_label = "Scheduled Due Date"
            detail_value = due_str
            action_text = f"Please return the book to the circulation desk on or before {due_str} to avoid overdue fine charges."
            plain_message = (
                f"Dear {user.full_name},\n\n"
                f"This is a friendly reminder that your borrowed book '{book_title}' is due for return on {due_str}.\n\n"
                f"Due Date: {due_str}\n\n"
                f"Please return the book on or before the due date to avoid overdue fines.\n\n"
                f"Thank you,\n"
                f"UniLibrary Circulation Desk"
            )

        elif notification_type in ['OVERDUE', Notification.Type.OVERDUE]:
            due_str = "the due date"
            if borrow_record and getattr(borrow_record, 'due_date', None):
                due_str = borrow_record.due_date.strftime('%d/%m/%Y')

            subject = f"UniLibrary Notice: '{book_title}' is Overdue"
            badge_text = "Overdue Notice"
            badge_bg = "#FED7D7"
            badge_color = "#9B2C2C"
            lead_text = f"Your borrowed textbook '{book_title}' was due on {due_str} and is now overdue."
            detail_label = "Original Due Date"
            detail_value = due_str
            action_text = "Overdue fines are accruing daily on your student account. Please return the book to the central circulation desk immediately to stop further fine liability."
            plain_message = (
                f"Dear {user.full_name},\n\n"
                f"Your borrowed book '{book_title}' was due on {due_str} and is now overdue.\n\n"
                f"Due Date: {due_str}\n\n"
                f"Overdue fines are accruing daily on your account. Please return the book to the library circulation desk immediately to stop further fine accruals.\n\n"
                f"Thank you,\n"
                f"UniLibrary Circulation Desk"
            )

        # Build RFC-compliant sender with Display Name: "UniLibrary Circulation Desk" <address>
        raw_from = getattr(settings, 'DEFAULT_FROM_EMAIL', 'iumoh936@gmail.com')
        clean_email = raw_from.split('<')[-1].replace('>', '').strip()
        from_email = f"UniLibrary Circulation Desk <{clean_email}>"

        try:
            html_message = render_to_string('notifications/email_notification.html', {
                'subject': subject,
                'user_name': user.full_name,
                'book_title': book_title,
                'badge_text': badge_text,
                'badge_bg': badge_bg,
                'badge_color': badge_color,
                'lead_text': lead_text,
                'detail_label': detail_label,
                'detail_value': detail_value,
                'action_text': action_text,
            })

            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=[recipient_email],
                reply_to=[clean_email],
            )
            email_msg.attach_alternative(html_message, "text/html")
            email_msg.extra_headers['Auto-Submitted'] = 'auto-generated'
            email_msg.extra_headers['X-Auto-Response-Suppress'] = 'All'
            email_msg.extra_headers['List-Unsubscribe'] = f'<mailto:{clean_email}?subject=unsubscribe>'
            email_msg.send(fail_silently=False)

            # Create EMAIL notification record in Notification table for audit tracking
            Notification.objects.create(
                user=user,
                type=notification_type,
                channel=Notification.Channel.EMAIL,
                message=plain_message,
                reservation=reservation,
                borrow_record=borrow_record,
                date_sent=now,
            )
            log_action(user, 'EMAIL_SENT', f"Sent {notification_type} email to {recipient_email} for '{book_title}'")
        except Exception as e:
            error_detail = f"Failed to send {notification_type} email to {recipient_email}: {str(e)}"
            log_action(user, 'EMAIL_FAILED', error_detail)

    return inapp_notif
