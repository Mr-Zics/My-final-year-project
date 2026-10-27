"""
Circulation service functions implementing Section 6 business rules.
All multi-step operations are wrapped in transaction.atomic() with select_for_update().
"""

from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q

from core.services import log_action, get_int, get_decimal
from catalogue.models import Copy
from fines.models import Fine


def check_borrow_eligibility(student):
    """
    Checks whether a student may reserve or borrow books.
    Per project simplification, unpaid fines do NOT block borrowing or reservations.
    Only active account status and the maximum loan limit of 3 books are enforced.
    Returns (ok: bool, reason: str or None).
    """
    from circulation.models import BorrowRecord

    if not student.is_active:
        return False, "Your account is deactivated. Please contact the library."

    # Enforce maximum of 3 active loans per student
    max_loans = get_int('max_loans_per_student')
    active_loans = BorrowRecord.objects.filter(
        student=student, return_date__isnull=True
    ).count()
    if active_loans >= max_loans:
        return False, (
            f"You have reached the maximum limit of {max_loans} borrowed books. "
            f"Please return a book first."
        )

    return True, None


def get_unpaid_fines_total(student):
    """Returns the total unpaid fines for a student."""
    return Fine.objects.filter(
        borrow_record__student=student,
        status=Fine.Status.UNPAID
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')


@transaction.atomic
def issue_copy(student, copy, librarian, reservation=None):
    """
    Issues a copy to a student (held copy or walk-in).
    Returns (success: bool, message: str, borrow_record or None).
    """
    from circulation.models import BorrowRecord

    # Eligibility check (max 3 loans)
    ok, reason = check_borrow_eligibility(student)
    if not ok:
        return False, reason, None

    # Lock the copy for update
    copy = Copy.objects.select_for_update().get(pk=copy.pk)

    # Validate copy status
    if copy.status == 'WITHDRAWN':
        return False, "This copy has been withdrawn and cannot be issued.", None
    if copy.status == 'BORROWED':
        return False, "This copy is already on loan.", None

    # If copy is RESERVED, verify it's held for this student
    if copy.status == 'RESERVED':
        from reservations.models import Reservation
        held_reservation = Reservation.objects.filter(
            copy=copy, status=Reservation.Status.READY
        ).first()
        if held_reservation and held_reservation.student != student:
            return False, (
                f"This copy is reserved for {held_reservation.student.full_name}. "
                f"It cannot be issued to a different student."
            ), None
        if held_reservation:
            reservation = held_reservation

    # Calculate dates: loan period is 14 days
    loan_period = get_int('loan_period_days')
    borrow_date = date.today()
    due_date = borrow_date + timedelta(days=loan_period)

    # Create the borrow record
    record = BorrowRecord.objects.create(
        student=student,
        copy=copy,
        reservation=reservation,
        issued_by=librarian,
        borrow_date=borrow_date,
        due_date=due_date,
    )

    # Update copy status
    copy.status = 'BORROWED'
    copy.save()

    # If fulfilling a reservation, mark it fulfilled
    if reservation:
        reservation.status = 'FULFILLED'
        reservation.save()

    log_action(librarian, 'ISSUE', (
        f"Issued {copy.accession_number} ({copy.book.title}) to "
        f"{student.full_name}. Due: {due_date}"
    ))

    return True, (
        f"Successfully issued '{copy.book.title}' ({copy.accession_number}) to "
        f"{student.full_name}. Due date: {due_date.strftime('%d %b %Y')}."
    ), record


@transaction.atomic
def receive_return(borrow_record, librarian=None):
    """
    Receives a returned copy.
    Calculates overdue fine (₦50/day) if returned late.
    Allocates copy to first waiting student if any, or marks copy available.
    Returns (message: str, fine_amount: Decimal or None).
    """
    from reservations.services import allocate_copy

    # Lock the copy
    copy = Copy.objects.select_for_update().get(pk=borrow_record.copy.pk)

    # Mark the loan as returned
    borrow_record.return_date = date.today()
    borrow_record.save()

    # Calculate late return fine (₦50 per overdue day)
    fine_amount = None
    if borrow_record.return_date > borrow_record.due_date:
        days_late = (borrow_record.return_date - borrow_record.due_date).days
        fine_per_day = get_decimal('fine_per_day')
        fine_amount = days_late * fine_per_day

        Fine.objects.create(
            borrow_record=borrow_record,
            amount=fine_amount,
            status=Fine.Status.UNPAID,
            date_created=date.today(),
        )

        message = (
            f"Late by {days_late} day{'s' if days_late != 1 else ''}. "
            f"Fine of N{fine_amount:,.0f} recorded."
        )
    else:
        message = f"'{copy.book.title}' returned on time. No fine."

    # Allocate the copy to next waiting reservation or mark as available
    alloc_msg = allocate_copy(copy)
    if alloc_msg:
        message += f" {alloc_msg}"

    log_action(librarian, 'RETURN', (
        f"Returned {copy.accession_number} ({copy.book.title}) from "
        f"{borrow_record.student.full_name}. {message}"
    ))

    return message, fine_amount

