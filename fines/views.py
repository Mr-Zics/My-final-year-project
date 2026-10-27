"""
Fine management views for UniLibrary Management System.
Implements Student My Fines and Staff Fine Management with payment recording.
Fine waivers have been removed per project simplification.
"""

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.db.models import Sum, Q

from accounts.permissions import StudentRequiredMixin, StaffReadMixin, LibrarianRequiredMixin
from fines.models import Fine
from fines.services import record_payment


class StudentFinesView(StudentRequiredMixin, TemplateView):
    """
    Student My Fines page.
    Shows outstanding unpaid balance and history of all fines (Unpaid or Paid).
    """
    template_name = 'fines/student_fines.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user

        fines_qs = Fine.objects.filter(
            borrow_record__student=student
        ).select_related('borrow_record__copy__book', 'recorded_by').order_by('-date_created')

        unpaid_total = fines_qs.filter(
            status=Fine.Status.UNPAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        context.update({
            'fines': fines_qs,
            'unpaid_total': unpaid_total,
        })
        return context


class StaffFinesListView(StaffReadMixin, ListView):
    """
    Staff Fine Records list.
    Tabs for Unpaid, Paid, All. Search by student name/matric/receipt.
    """
    model = Fine
    template_name = 'fines/staff_fines.html'
    context_object_name = 'fines'
    paginate_by = 20

    def get_queryset(self):
        qs = Fine.objects.select_related(
            'borrow_record__student',
            'borrow_record__copy__book',
            'recorded_by'
        )

        status_tab = self.request.GET.get('tab', 'unpaid')
        q = self.request.GET.get('q', '').strip()

        if status_tab == 'unpaid':
            qs = qs.filter(status=Fine.Status.UNPAID)
        elif status_tab == 'paid':
            qs = qs.filter(status=Fine.Status.PAID)
        # 'all' shows all statuses (Unpaid & Paid)

        if q:
            qs = qs.filter(
                Q(borrow_record__student__full_name__icontains=q) |
                Q(borrow_record__student__matric_number__icontains=q) |
                Q(borrow_record__copy__book__title__icontains=q) |
                Q(payment_reference__icontains=q)
            )

        return qs.order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_tab'] = self.request.GET.get('tab', 'unpaid')
        context['search_query'] = self.request.GET.get('q', '')

        # Unpaid and collected fine stats
        context['total_unpaid'] = Fine.objects.filter(
            status=Fine.Status.UNPAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        context['total_collected'] = Fine.objects.filter(
            status=Fine.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return context


class StaffRecordPaymentView(LibrarianRequiredMixin, View):
    """
    Librarian records full offline fine payment.
    POST /staff/fines/<int:pk>/pay/
    Sets amount, payment date, and receipt reference; status becomes PAID.
    """
    def post(self, request, pk):
        fine = get_object_or_404(Fine, pk=pk, status=Fine.Status.UNPAID)
        reference = request.POST.get('reference', '').strip()

        if not reference:
            messages.error(request, "A payment reference (receipt number) is required.")
            return redirect(f"{request.META.get('HTTP_REFERER', 'staff_fines')}")

        success, message = record_payment(fine, request.user, reference)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('staff_fines')
