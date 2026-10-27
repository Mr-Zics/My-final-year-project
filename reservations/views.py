"""
Reservation views for UniLibrary Management System.
Implements Student Reservation Queue (Section 7.2) and Staff Reservation Desk (Section 7.3).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.db.models import Q

from accounts.permissions import StudentRequiredMixin, StaffReadMixin, LibrarianRequiredMixin
from catalogue.models import Book
from reservations.models import Reservation
from reservations.services import reserve_book, cancel_reservation


class ReserveBookView(StudentRequiredMixin, View):
    """
    Student places a reservation for a book (Section 6.2).
    POST /books/<int:pk>/reserve/
    """
    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        success, message, reservation = reserve_book(request.user, book)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('book_detail', pk=book.pk)


class StudentReservationListView(StudentRequiredMixin, TemplateView):
    """
    Student My Reservations page (Section 7.2).
    Shows active reservations with queue positions or pickup deadlines,
    plus history of fulfilled, expired, or cancelled reservations.
    """
    template_name = 'reservations/student_reservations.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user

        context['active_reservations'] = Reservation.objects.filter(
            student=student,
            status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
        ).select_related('book', 'copy').order_by('reservation_date')

        context['reservation_history'] = Reservation.objects.filter(
            student=student,
            status__in=[Reservation.Status.FULFILLED, Reservation.Status.CANCELLED, Reservation.Status.EXPIRED]
        ).select_related('book', 'copy').order_by('-reservation_date')[:30]

        from core.services import get_int
        context['max_reservations'] = get_int('max_reservations_per_student') or 4

        return context


class StudentCancelReservationView(StudentRequiredMixin, View):
    """
    Student cancels their own active reservation (Section 6.6).
    POST /student/reservations/<int:pk>/cancel/
    """
    def post(self, request, pk):
        reservation = get_object_or_404(
            Reservation,
            pk=pk,
            student=request.user,
            status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
        )
        success, message = cancel_reservation(reservation, request.user)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('student_reservations')


class StaffReservationQueueView(StaffReadMixin, ListView):
    """
    Librarian / Admin Reservation Queue management (Section 7.3).
    Filter by status and book title; grouped view option by book.
    """
    model = Reservation
    template_name = 'reservations/staff_queue.html'
    context_object_name = 'reservations'
    paginate_by = 20

    def get_queryset(self):
        qs = Reservation.objects.select_related('student', 'book', 'copy')

        status_filter = self.request.GET.get('status', '')
        q = self.request.GET.get('q', '').strip()

        if status_filter:
            qs = qs.filter(status=status_filter)
        else:
            # By default, show active queues (WAITING and READY)
            qs = qs.filter(status__in=[Reservation.Status.WAITING, Reservation.Status.READY])

        if q:
            qs = qs.filter(
                Q(book__title__icontains=q) |
                Q(student__full_name__icontains=q) |
                Q(student__matric_number__icontains=q)
            )

        return qs.order_by('reservation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Reservation.Status.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class StaffCancelReservationView(LibrarianRequiredMixin, View):
    """
    Librarian cancels any active reservation (Section 6.6 & Section 3).
    POST /staff/reservations/<int:pk>/cancel/
    """
    def post(self, request, pk):
        reservation = get_object_or_404(
            Reservation,
            pk=pk,
            status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
        )
        success, message = cancel_reservation(reservation, request.user)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return redirect('staff_reservation_queue')
