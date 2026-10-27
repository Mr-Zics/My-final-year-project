"""
Fine service functions for UniLibrary Management System.
Handles recording payment of overdue fines.
Fine waivers have been completely removed per project simplification.
"""

from datetime import date
from django.db import transaction

from core.services import log_action
from fines.models import Fine


@transaction.atomic
def record_payment(fine, librarian, reference):
    """
    Records a full payment for an UNPAID fine.
    Sets status to PAID, records payment date, reference receipt number, and staff user.
    Returns (success: bool, message: str).
    """
    if fine.status != Fine.Status.UNPAID:
        return False, "Only unpaid fines can be paid."

    if not reference or not reference.strip():
        return False, "A payment reference (receipt number) is required."

    fine.status = Fine.Status.PAID
    fine.date_paid = date.today()
    fine.recorded_by = librarian
    fine.payment_reference = reference.strip()
    fine.save()

    log_action(librarian, 'FINE_PAID', (
        f"Payment of N{fine.amount:,.0f} recorded for "
        f"{fine.borrow_record.student.full_name}. Ref: {reference}"
    ))

    return True, f"Payment of N{fine.amount:,.0f} recorded successfully. Reference: {reference}"

