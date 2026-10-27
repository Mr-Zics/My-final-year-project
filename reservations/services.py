"""
Reservation service functions implementing Section 6 business rules.
Handles reservation creation, allocation, and cancellation.
"""

from datetime import timedelta
from django.db import transaction
from django.utils import timezone

from core.services import log_action, get_int
from catalogue.models import Copy
from reservations.models import Reservation


from notifications.services import send_notification

# Alias for backward compatibility with existing codebase
_send_notification = send_notification



@transaction.atomic
def reserve_book(student, book):
    """
    Section 6.2: Places a reservation for a book.
    Returns (success: bool, message: str, reservation or None).
    """
    from circulation.services import check_borrow_eligibility
    from circulation.models import BorrowRecord
    from django.db import IntegrityError

    # Step 1: Eligibility check
    ok, reason = check_borrow_eligibility(student)
    if not ok:
        return False, reason, None

    # Step 2: Check for existing active reservation
    existing = Reservation.objects.filter(
        student=student,
        book=book,
        status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
    ).first()
    if existing:
        if existing.status == Reservation.Status.READY:
            return False, f"You already have a reserved copy of '{book.title}' ready for pickup at the circulation desk.", existing
        else:
            pos = existing.queue_position()
            pos_text = f" (Queue Position #{pos})" if pos else ""
            return False, f"You already have an active reservation for '{book.title}'{pos_text}.", existing

    # Step 3: Check if student currently has an active loan of this book
    has_active_loan = BorrowRecord.objects.filter(
        student=student,
        copy__book=book,
        return_date__isnull=True
    ).exists()
    if has_active_loan:
        return False, f"You are currently borrowing a copy of '{book.title}'. You cannot place a reservation while borrowing it.", None

    # Step 4: Check maximum active reservations quota per student
    max_reservations = get_int('max_reservations_per_student')
    if max_reservations <= 0:
        max_reservations = 4
    active_reservations_count = Reservation.objects.filter(
        student=student,
        status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
    ).count()
    if active_reservations_count >= max_reservations:
        return False, (
            f"You have reached the maximum limit of {max_reservations} active reservations. "
            f"Please collect your held books or cancel an existing reservation before placing a new one."
        ), None

    # Step 5: Look for an available copy
    available_copy = Copy.objects.select_for_update().filter(
        book=book,
        status='AVAILABLE'
    ).first()

    pickup_hours = get_int('pickup_window_hours')
    now = timezone.now()

    try:
        if available_copy:
            # Copy found: create READY reservation
            reservation = Reservation.objects.create(
                student=student,
                book=book,
                copy=available_copy,
                status=Reservation.Status.READY,
                notified_at=now,
                expires_at=now + timedelta(hours=pickup_hours),
            )
            available_copy.status = 'RESERVED'
            available_copy.save()

            message = (
                f"Your reservation is confirmed and the book is being held for you "
                f"until {reservation.expires_at.strftime('%d %b %Y %H:%M')}. "
                f"Please collect it at the library desk."
            )

            # Send email / notification AFTER commit so DB transaction lock isn't held during network I/O
            transaction.on_commit(lambda: _send_notification(
                student, 'RESERVATION_READY', message,
                reservation=reservation, send_email=True
            ))

            log_action(student, 'RESERVE', f"Reserved '{book.title}' - copy ready for pickup")

        else:
            # No copy available: create WAITING reservation
            reservation = Reservation.objects.create(
                student=student,
                book=book,
                status=Reservation.Status.WAITING,
            )

            position = reservation.queue_position()
            message = (
                f"You are number {position} in the queue for '{book.title}'. "
                f"We will notify you when a copy is ready."
            )

            transaction.on_commit(lambda: _send_notification(
                student, 'RESERVATION_CONFIRMED', message,
                reservation=reservation, send_email=False
            ))

            log_action(student, 'RESERVE', f"Joined queue for '{book.title}' at position {position}")

    except IntegrityError:
        return False, f"You already have an active reservation for '{book.title}'.", None

    return True, message, reservation


@transaction.atomic
def allocate_copy(copy):
    """
    Section 6.4: Allocates a free copy to the next eligible waiting reservation.
    Called after a return, expired hold, or cancelled READY reservation.
    If a student in the queue is currently blocked from borrowing (e.g. owing unpaid
    fines >= threshold, maximum active loans reached, or deactivated account), the
    copy automatically bypasses them and allocates to the next eligible student in queue.
    Returns an allocation message string or None.
    """
    from circulation.services import check_borrow_eligibility

    # Never allocate withdrawn copies
    if copy.status == 'WITHDRAWN':
        return None

    copy = Copy.objects.select_for_update().get(pk=copy.pk)

    # Find all WAITING reservations for this book ordered by queue priority (oldest first)
    waiting_reservations = Reservation.objects.select_for_update().filter(
        book=copy.book,
        status=Reservation.Status.WAITING,
    ).select_related('student').order_by('reservation_date', 'id')

    pickup_hours = get_int('pickup_window_hours')
    now = timezone.now()

    for candidate in waiting_reservations:
        ok, reason = check_borrow_eligibility(candidate.student)
        if not ok:
            # Student is blocked from borrowing (e.g. unpaid fines, max active loans)
            bypass_msg = (
                f"A copy of '{copy.book.title}' became available, but your account is currently "
                f"blocked from borrowing ({reason}). The copy has automatically been passed to the next eligible "
                f"student in the queue. Please resolve your account balance to be eligible for future copies."
            )
            _send_notification(
                candidate.student, 'RESERVATION_BYPASSED', bypass_msg,
                reservation=candidate, send_email=True
            )
            log_action(None, 'QUEUE_BYPASS', (
                f"Reservation #{candidate.id} for {candidate.student.full_name} "
                f"bypassed during copy allocation: {reason}"
            ))
            continue

        # Found the first eligible student in line!
        candidate.status = Reservation.Status.READY
        candidate.copy = copy
        candidate.notified_at = now
        candidate.expires_at = now + timedelta(hours=pickup_hours)
        candidate.save()

        copy.status = 'RESERVED'
        copy.save()

        message = (
            f"Good news! '{copy.book.title}' is now ready for you. "
            f"Please collect it before {candidate.expires_at.strftime('%d %b %Y %H:%M')}, "
            f"or the reservation will expire and pass to the next student."
        )

        cand_student = candidate.student
        cand_res = candidate
        transaction.on_commit(lambda: _send_notification(
            cand_student, 'RESERVATION_READY', message,
            reservation=cand_res, send_email=True
        ))

        log_action(None, 'ALLOCATE', (
            f"Copy {copy.accession_number} allocated to "
            f"{candidate.student.full_name} for reservation"
        ))

        return f"Copy now held for {candidate.student.full_name} (next eligible in queue)."

    # No eligible student waiting — mark as available
    copy.status = 'AVAILABLE'
    copy.save()
    return "Copy is available."


@transaction.atomic
def cancel_reservation(reservation, by_user):
    """
    Section 6.6: Cancels a WAITING or READY reservation.
    If it was READY, the held copy is reallocated.
    Returns (success: bool, message: str).
    """
    if reservation.status not in [Reservation.Status.WAITING, Reservation.Status.READY]:
        return False, "Only active reservations (Waiting or Ready) can be cancelled."

    was_ready = reservation.status == Reservation.Status.READY
    held_copy = reservation.copy

    reservation.status = Reservation.Status.CANCELLED
    reservation.copy = None
    reservation.save()

    alloc_msg = ""
    if was_ready and held_copy:
        alloc_msg = allocate_copy(held_copy) or ""

    log_action(by_user, 'CANCEL_RESERVATION', (
        f"Cancelled reservation for '{reservation.book.title}' "
        f"by {reservation.student.full_name}"
    ))

    return True, f"Reservation cancelled. {alloc_msg}"

