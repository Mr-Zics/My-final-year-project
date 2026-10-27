"""
Circulation views for UniLibrary Management System.
Implements Issue, Return, Active Loans, Overdue (Section 7.3) and Student My Loans (Section 7.2).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, TemplateView
from django.contrib import messages
from django.db.models import Q

from accounts.models import User
from accounts.permissions import LibrarianRequiredMixin, StudentRequiredMixin, StaffReadMixin
from catalogue.models import Copy, Book
from circulation.models import BorrowRecord
from circulation.services import issue_copy, receive_return, check_borrow_eligibility, get_unpaid_fines_total
from core.services import get_int


class StaffIssueView(LibrarianRequiredMixin, View):
    """
    Librarian issue page (Section 7.3): Two-step process.
    Step 1: Find student by matric/name. Step 2: Select copy to issue.
    """
    template_name = 'circulation/staff_issue.html'

    def get(self, request):
        from reservations.models import Reservation
        ready_holds = Reservation.objects.filter(
            status=Reservation.Status.READY
        ).select_related('student', 'book', 'copy').order_by('expires_at')

        context = {
            'step': 1,
            'ready_holds': ready_holds,
        }
        matric_query = request.GET.get('matric', '').strip()

        if matric_query:
            # Find student
            student = User.objects.filter(
                Q(matric_number__iexact=matric_query) |
                Q(full_name__icontains=matric_query) |
                Q(email__icontains=matric_query),
                role=User.Role.STUDENT
            ).first()

            if student:
                ok, reason = check_borrow_eligibility(student)
                max_loans = get_int('max_loans_per_student')
                active_loans = BorrowRecord.objects.filter(
                    student=student, return_date__isnull=True
                ).count()
                unpaid_fines = get_unpaid_fines_total(student)

                # Get student's ready reservations
                from reservations.models import Reservation
                ready_reservations = Reservation.objects.filter(
                    student=student,
                    status=Reservation.Status.READY
                ).select_related('book', 'copy')

                # Get available copies for walk-in
                copy_query = request.GET.get('copy_q', '').strip()
                available_copies = []
                if copy_query:
                    available_copies = Copy.objects.filter(
                        Q(book__title__icontains=copy_query) |
                        Q(id__icontains=copy_query.replace('C', '').replace('c', '')),
                        status='AVAILABLE'
                    ).select_related('book')[:20]

                context.update({
                    'step': 2,
                    'found_student': student,
                    'eligible': ok,
                    'reason': reason,
                    'active_loans': active_loans,
                    'max_loans': max_loans,
                    'unpaid_fines': unpaid_fines,
                    'ready_reservations': ready_reservations,
                    'available_copies': available_copies,
                    'copy_query': copy_query,
                })
            else:
                messages.warning(request, f"No student found matching '{matric_query}'.")

        context['matric_query'] = matric_query
        return render(request, self.template_name, context)

    def post(self, request):
        student_id = request.POST.get('student_id')
        copy_id = request.POST.get('copy_id')

        if not student_id or not copy_id:
            messages.error(request, "Student and copy must be specified.")
            return redirect('staff_issue')

        student = get_object_or_404(User, pk=student_id, role=User.Role.STUDENT)
        copy = get_object_or_404(Copy, pk=copy_id)

        success, message, record = issue_copy(student, copy, request.user)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect(f"{request.path}?matric={student.matric_number or student.email}")


class StaffReturnView(LibrarianRequiredMixin, View):
    """
    Librarian return page (Section 7.3): Enter accession number to process return.
    """
    template_name = 'circulation/staff_return.html'

    def get(self, request):
        context = {}
        accession = request.GET.get('accession', '').strip()

        # Query all active unreturned loans ("books that are out")
        active_loans = BorrowRecord.objects.filter(
            return_date__isnull=True
        ).select_related('copy__book', 'student').order_by('due_date')
        context['active_loans'] = active_loans

        if accession:
            # Parse accession number (e.g. C0012 -> id 12)
            try:
                copy_id = int(accession.upper().replace('C', ''))
                copy = Copy.objects.select_related('book').get(pk=copy_id)
                active_loan = BorrowRecord.objects.filter(
                    copy=copy, return_date__isnull=True
                ).select_related('student', 'copy__book').first()

                if active_loan:
                    context.update({
                        'copy': copy,
                        'loan': active_loan,
                        'fine_preview': active_loan.estimated_fine if active_loan.is_overdue else None,
                    })
                else:
                    messages.info(request, f"Copy {copy.accession_number} has no active loan.")
            except (ValueError, Copy.DoesNotExist):
                messages.warning(request, f"Copy '{accession}' not found.")

        context['accession'] = accession
        return render(request, self.template_name, context)

    def post(self, request):
        loan_id = request.POST.get('loan_id')
        if not loan_id:
            messages.error(request, "No loan specified.")
            return redirect('staff_return')

        loan = get_object_or_404(BorrowRecord, pk=loan_id, return_date__isnull=True)
        message, fine_amount = receive_return(loan, request.user)
        messages.success(request, message)
        return redirect('staff_return')


class StaffActiveLoansView(StaffReadMixin, ListView):
    """Librarian/Admin view: all active loans with search and filters."""
    model = BorrowRecord
    template_name = 'circulation/staff_active_loans.html'
    context_object_name = 'loans'
    paginate_by = 15

    def get_queryset(self):
        qs = BorrowRecord.objects.filter(
            return_date__isnull=True
        ).select_related('student', 'copy__book', 'issued_by')

        q = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '')

        if q:
            qs = qs.filter(
                Q(student__full_name__icontains=q) |
                Q(copy__book__title__icontains=q) |
                Q(student__matric_number__icontains=q)
            )

        from datetime import date, timedelta
        from core.services import get_int
        reminder_days = get_int('reminder_days_before_due')
        today = date.today()

        if status_filter == 'overdue':
            qs = qs.filter(due_date__lt=today)
        elif status_filter == 'due_soon':
            qs = qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=reminder_days))

        return qs.order_by('due_date')


class StaffOverdueView(StaffReadMixin, ListView):
    """Librarian/Admin view: overdue loans sorted by days overdue."""
    model = BorrowRecord
    template_name = 'circulation/staff_overdue.html'
    context_object_name = 'loans'
    paginate_by = 15

    def get_queryset(self):
        from datetime import date
        return BorrowRecord.objects.filter(
            return_date__isnull=True,
            due_date__lt=date.today()
        ).select_related('student', 'copy__book').order_by('due_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from decimal import Decimal
        loans = context['loans']
        context['total_estimated'] = sum(
            (l.estimated_fine for l in loans), Decimal('0.00')
        )
        context['overdue_count'] = self.get_queryset().count()
        return context


class StudentLoansView(StudentRequiredMixin, TemplateView):
    """Student My Loans page (Section 7.2) with current and history tabs."""
    template_name = 'circulation/student_loans.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user

        context['current_loans'] = BorrowRecord.objects.filter(
            student=student, return_date__isnull=True
        ).select_related('copy__book').order_by('due_date')

        context['loan_history'] = BorrowRecord.objects.filter(
            student=student, return_date__isnull=False
        ).select_related('copy__book').prefetch_related('fines').order_by('-return_date')[:30]

        context['max_loans'] = get_int('max_loans_per_student')
        return context

