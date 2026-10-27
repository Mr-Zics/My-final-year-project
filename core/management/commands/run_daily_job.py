"""
Django management command: run_daily_job.
Implements automated reservation hold expiry, due date reminders, and overdue notices (Section 6.7).
Can be run via CLI, Windows Task Scheduler / batch file, or Admin web dashboard button.
"""

from datetime import datetime, date, timedelta, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail

from core.services import log_action, get_int
from reservations.models import Reservation
from reservations.services import allocate_copy, _send_notification
from circulation.models import BorrowRecord
from notifications.models import Notification


class Command(BaseCommand):
    help = "Runs daily automated checks: expires uncollected holds, sends due reminders and overdue notices."

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help="Simulate running the job on a specific date (YYYY-MM-DD).",
        )

    def handle(self, *args, **options):
        date_str = options.get('date')
        if date_str:
            try:
                run_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {date_str}. Use YYYY-MM-DD."))
                return
        else:
            run_date = date.today()

        # Combine run_date with current or end-of-day time for simulation
        current_time = timezone.now().time()
        run_datetime = timezone.make_aware(
            datetime.combine(run_date, current_time)
        )

        self.stdout.write(self.style.NOTICE(f"--- Running Library Daily Automation Job for {run_date} ---"))

        expired_count = 0
        reminders_count = 0
        overdue_count = 0
        errors_count = 0

        # ======================================================================
        # Task 1: Expire uncollected READY reservations (48-hour pickup window)
        # ======================================================================
        ready_reservations = Reservation.objects.filter(
            status=Reservation.Status.READY,
            expires_at__lt=run_datetime,
        ).select_related('student', 'book', 'copy')

        for res in ready_reservations:
            try:
                with transaction.atomic():
                    held_copy = res.copy
                    res.status = Reservation.Status.EXPIRED
                    res.copy = None
                    res.save()

                    msg = (
                        f"Your reservation for '{res.book.title}' has expired because "
                        f"it was not collected within the pickup window."
                    )
                    _send_notification(
                        res.student,
                        'RESERVATION_EXPIRED',
                        msg,
                        reservation=res,
                        send_email=True
                    )

                    log_action(
                        None,
                        'RESERVATION_EXPIRED',
                        f"Reservation #{res.id} for {res.student.full_name} expired uncollected"
                    )

                    if held_copy:
                        allocate_copy(held_copy)

                    expired_count += 1
            except Exception as e:
                errors_count += 1
                self.stderr.write(self.style.ERROR(f"Error expiring reservation #{res.id}: {e}"))

        # ======================================================================
        # Task 2: Send DUE_SOON reminders
        # ======================================================================
        reminder_days = get_int('reminder_days_before_due')
        target_due_date = run_date + timedelta(days=reminder_days)

        due_soon_loans = BorrowRecord.objects.filter(
            return_date__isnull=True,
            due_date=target_due_date,
        ).select_related('student', 'copy__book')

        for loan in due_soon_loans:
            try:
                # Check if DUE_SOON notification already sent for this loan
                already_sent = Notification.objects.filter(
                    borrow_record=loan,
                    type=Notification.Type.DUE_SOON,
                    channel=Notification.Channel.INAPP,
                ).exists()

                if not already_sent:
                    msg = (
                        f"Reminder: '{loan.copy.book.title}' is due in {reminder_days} days "
                        f"on {loan.due_date.strftime('%d %b %Y')}. Please return it to the library desk."
                    )
                    _send_notification(
                        loan.student,
                        'DUE_SOON',
                        msg,
                        borrow_record=loan,
                        send_email=True,
                    )
                    reminders_count += 1
            except Exception as e:
                errors_count += 1
                self.stderr.write(self.style.ERROR(f"Error sending reminder for loan #{loan.id}: {e}"))

        # ======================================================================
        # Task 3: Send OVERDUE notices
        # ======================================================================
        overdue_repeat_days = get_int('overdue_repeat_days')
        max_overdue_notices = get_int('max_overdue_notices')

        overdue_loans = BorrowRecord.objects.filter(
            return_date__isnull=True,
            due_date__lt=run_date,
        ).select_related('student', 'copy__book')

        for loan in overdue_loans:
            try:
                days_late = (run_date - loan.due_date).days

                notices_sent = Notification.objects.filter(
                    borrow_record=loan,
                    type=Notification.Type.OVERDUE,
                    channel=Notification.Channel.INAPP,
                ).order_by('-date_sent')

                count = notices_sent.count()
                if count < max_overdue_notices:
                    send_now = False
                    if count == 0:
                        send_now = True
                    else:
                        last_sent = notices_sent.first().date_sent.date()
                        if (run_date - last_sent).days >= overdue_repeat_days:
                            send_now = True

                    if send_now:
                        notice_num = count + 1
                        msg = (
                            f"OVERDUE NOTICE {notice_num}/{max_overdue_notices}: "
                            f"'{loan.copy.book.title}' is {days_late} day(s) overdue. "
                            f"Overdue fines are accruing at ₦50/day. Return the book immediately."
                        )
                        _send_notification(
                            loan.student,
                            'OVERDUE',
                            msg,
                            borrow_record=loan,
                            send_email=True,
                        )
                        overdue_count += 1
            except Exception as e:
                errors_count += 1
                self.stderr.write(self.style.ERROR(f"Error sending overdue notice for loan #{loan.id}: {e}"))

        # Summary log & output
        summary = (
            f"Daily job ({run_date}): expired {expired_count}, "
            f"reminders {reminders_count}, overdue notices {overdue_count}, errors {errors_count}"
        )
        log_action(None, 'DAILY_JOB', summary)
        self.stdout.write(self.style.SUCCESS(summary))
