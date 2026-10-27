"""
Account and User Management Views for UniLibrary.
Implements Section 3, Section 7.1, Section 7.4, and Section 12.
"""

import secrets
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import FormView, CreateView, UpdateView, ListView, TemplateView, View, DetailView
from django.contrib.auth import login, logout
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.core.exceptions import PermissionDenied

from core.services import log_action
from .models import User
from .forms import LoginForm, StudentRegistrationForm, AdminUserAddForm, AdminUserEditForm
from .permissions import (
    StudentRequiredMixin,
    LibrarianRequiredMixin,
    AdminRequiredMixin,
    StaffReadMixin,
    get_role_redirect_url
)


class LoginView(FormView):
    """
    Renders the UniLibrary sign-in page (Screen 1 in UI reference)
    and processes user authentication with role-based redirection.
    """
    template_name = 'accounts/login.html'
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(get_role_redirect_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.user
        login(self.request, user)

        if not form.cleaned_data.get('remember_me'):
            self.request.session.set_expiry(0)  # Expires when browser closes
        else:
            self.request.session.set_expiry(7200)  # 2 hours per specification

        log_action(user, 'LOGIN', f"User {user.email} logged in ({user.role})")
        messages.success(self.request, f"Welcome, {user.full_name}!")

        next_url = self.request.GET.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(get_role_redirect_url(user))

    def form_invalid(self, form):
        identifier = self.request.POST.get('identifier', 'Unknown')
        log_action(None, 'FAILED_LOGIN', f"Failed login attempt for identifier '{identifier}'")
        return super().form_invalid(form)


class LogoutView(View):
    """
    Handles user logout. Required to be a POST request per Section 3.
    """
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            log_action(request.user, 'LOGOUT', f"User {request.user.email} logged out")
            logout(request)
            messages.info(request, "You have been successfully logged out.")
        return redirect('login')

    def get(self, request, *args, **kwargs):
        # Graceful fallback for GET requests
        return self.post(request, *args, **kwargs)


class StudentRegisterView(CreateView):
    """
    Public student self-registration view.
    Immediately creates active borrower accounts and logs them in.
    """
    template_name = 'accounts/register.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('student_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(get_role_redirect_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        log_action(user, 'REGISTER', f"New student account registered: {user.full_name} ({user.matric_number})")
        messages.success(self.request, f"Registration successful! Welcome to UniLibrary, {user.full_name}.")
        return redirect('student_dashboard')


# ==============================================================================
# Role-based Landing Pages
# ==============================================================================

class StudentDashboardView(StudentRequiredMixin, TemplateView):
    """Student portal landing page (Section 7.2 & Screen 2)."""
    template_name = 'student/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user
        from datetime import date
        from decimal import Decimal
        from django.db.models import Sum
        from circulation.models import BorrowRecord
        from reservations.models import Reservation
        from fines.models import Fine
        from notifications.models import Notification
        from core.services import get_int

        max_loans = get_int('max_loans_per_student')
        reminder_days = get_int('reminder_days_before_due')

        active_loans = BorrowRecord.objects.filter(
            student=student, return_date__isnull=True
        ).select_related('copy__book').order_by('due_date')

        due_soon_count = sum(1 for l in active_loans if 0 <= l.days_remaining <= reminder_days and not l.is_overdue)
        overdue_loans_count = sum(1 for l in active_loans if l.is_overdue)

        active_reservations = Reservation.objects.filter(
            student=student,
            status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
        ).select_related('book', 'copy').order_by('reservation_date')

        unpaid_fines = Fine.objects.filter(
            borrow_record__student=student,
            status=Fine.Status.UNPAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        recent_notifications = Notification.objects.filter(
            user=student,
            channel=Notification.Channel.INAPP
        ).order_by('-date_sent')[:3]

        unread_notifs_count = Notification.objects.filter(
            user=student,
            channel=Notification.Channel.INAPP,
            is_read=False
        ).count()

        context.update({
            'active_loans': active_loans,
            'active_loans_count': active_loans.count(),
            'max_loans': max_loans,
            'due_soon_count': due_soon_count,
            'overdue_loans_count': overdue_loans_count,
            'active_reservations': active_reservations,
            'active_reservations_count': active_reservations.count(),
            'unpaid_fines': unpaid_fines,
            'recent_notifications': recent_notifications,
            'unread_notifs_count': unread_notifs_count,
        })
        return context


class StaffDashboardView(LibrarianRequiredMixin, TemplateView):
    """Librarian circulation desk landing page (Section 7.3 & Screen 9)."""
    template_name = 'staff/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date
        from decimal import Decimal
        from django.db.models import Sum
        from circulation.models import BorrowRecord
        from reservations.models import Reservation
        from fines.models import Fine
        from catalogue.models import Copy

        today = date.today()

        context.update({
            'books_out_count': BorrowRecord.objects.filter(return_date__isnull=True).count(),
            'overdue_loans_count': BorrowRecord.objects.filter(return_date__isnull=True, due_date__lt=today).count(),
            'waiting_reservations_count': Reservation.objects.filter(status=Reservation.Status.WAITING).count(),
            'ready_holds_count': Reservation.objects.filter(status=Reservation.Status.READY).count(),
            'unpaid_fines_total': Fine.objects.filter(status=Fine.Status.UNPAID).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'available_copies_count': Copy.objects.filter(status='AVAILABLE').count(),
            'total_copies_count': Copy.objects.count(),
            'reserved_copies_count': Copy.objects.filter(status='RESERVED').count(),
            'withdrawn_copies_count': Copy.objects.filter(status='WITHDRAWN').count(),
            'withdrawn_copies': Copy.objects.filter(status='WITHDRAWN').select_related('book__category'),
            'collect_soon': Reservation.objects.filter(
                status=Reservation.Status.READY
            ).select_related('student', 'book', 'copy').order_by('expires_at')[:5],
            'most_overdue': BorrowRecord.objects.filter(
                return_date__isnull=True,
                due_date__lt=today
            ).select_related('student', 'copy__book').order_by('due_date')[:5],
        })
        return context


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Administrator portal landing page (Section 7.4)."""
    template_name = 'core/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date
        from decimal import Decimal
        from django.db.models import Sum
        from accounts.models import User
        from catalogue.models import Book, Copy
        from circulation.models import BorrowRecord
        from fines.models import Fine

        today = date.today()

        context.update({
            'total_students': User.objects.filter(role=User.Role.STUDENT).count(),
            'total_librarians': User.objects.filter(role=User.Role.LIBRARIAN).count(),
            'total_admins': User.objects.filter(role=User.Role.ADMINISTRATOR).count(),
            'total_books': Book.objects.count(),
            'total_copies': Copy.objects.count(),
            'available_copies': Copy.objects.filter(status='AVAILABLE').count(),
            'active_loans': BorrowRecord.objects.filter(return_date__isnull=True).count(),
            'overdue_loans': BorrowRecord.objects.filter(return_date__isnull=True, due_date__lt=today).count(),
            'unpaid_fines': Fine.objects.filter(status=Fine.Status.UNPAID).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
            'paid_fines': Fine.objects.filter(status=Fine.Status.PAID).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'),
        })
        return context


# ==============================================================================
# Administrator User Management (Section 7.4)
# ==============================================================================

class AdminUserListView(AdminRequiredMixin, ListView):
    """
    Administrator view to list, search, and filter all registered users.
    """
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 15

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_registered')
        query = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()
        status = self.request.GET.get('status', '').strip()

        if query:
            qs = qs.filter(
                Q(full_name__icontains=query) |
                Q(email__icontains=query) |
                Q(matric_number__icontains=query)
            )

        if role:
            qs = qs.filter(role=role)

        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context['selected_role'] = self.request.GET.get('role', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['roles'] = User.Role.choices
        return context


class AdminUserCreateView(AdminRequiredMixin, CreateView):
    """
    Administrator creates a new user account with temporary credentials.
    """
    model = User
    form_class = AdminUserAddForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('admin_user_list')

    def form_valid(self, form):
        user = form.save()
        log_action(self.request.user, 'USER_CREATE', f"Admin created user {user.email} with role {user.role}")
        messages.success(self.request, f"User '{user.full_name}' was created successfully.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_title'] = "Add New User"
        return context


class AdminUserUpdateView(AdminRequiredMixin, UpdateView):
    """
    Administrator edits an existing user's details and active status.
    """
    model = User
    form_class = AdminUserEditForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('admin_user_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['requesting_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        log_action(self.request.user, 'USER_EDIT', f"Admin updated user {user.email}")
        messages.success(self.request, f"User '{user.full_name}' was updated successfully.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_title'] = f"Edit User: {self.object.full_name}"
        context['is_edit'] = True
        return context


class AdminUserResetPasswordView(AdminRequiredMixin, View):
    """
    Administrator resets a user's password and generates a temporary password shown once on screen.
    """
    template_name = 'accounts/reset_password.html'

    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {'target_user': target_user})

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        # Generate temporary password meeting policy (min 8 chars, mixed)
        chars = string.ascii_letters + string.digits + "!@#"
        temp_password = "Temp@" + "".join(secrets.choice(chars) for _ in range(6))

        target_user.set_password(temp_password)
        target_user.save()

        log_action(request.user, 'PASSWORD_RESET', f"Admin reset password for user {target_user.email}")
        messages.success(request, f"Password reset successfully for {target_user.full_name}.")

        return render(request, self.template_name, {
            'target_user': target_user,
            'temp_password': temp_password
        })


class AdminUserToggleStatusView(AdminRequiredMixin, View):
    """
    Activates or deactivates a user account with safeguards (T27).
    """
    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        # Safeguard 1: Cannot deactivate oneself
        if target_user.pk == request.user.pk:
            messages.error(request, "You cannot deactivate your own administrator account.")
            return redirect('admin_user_list')

        # Safeguard 2: Cannot deactivate the last remaining administrator (T27)
        if target_user.role == User.Role.ADMINISTRATOR and target_user.is_active:
            other_active_admins = User.objects.filter(
                role=User.Role.ADMINISTRATOR,
                is_active=True
            ).exclude(pk=target_user.pk).count()

            if other_active_admins == 0:
                messages.error(request, "Cannot deactivate the last remaining administrator.")
                return redirect('admin_user_list')

        target_user.is_active = not target_user.is_active
        target_user.save()

        state = "activated" if target_user.is_active else "deactivated"
        log_action(request.user, 'USER_STATUS_CHANGE', f"Admin {state} user {target_user.email}")
        messages.success(request, f"User '{target_user.full_name}' was successfully {state}.")
        return redirect('admin_user_list')


# ==============================================================================
# Staff Student Directory (Section 7.3)
# ==============================================================================

class StaffStudentListView(StaffReadMixin, ListView):
    """
    Librarian / Admin searchable student directory (Section 7.3).
    Shows student name, matric, active loans count, unpaid fines, and account status.
    """
    model = User
    template_name = 'accounts/staff_student_list.html'
    context_object_name = 'students'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.STUDENT).order_by('full_name')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(email__icontains=q) |
                Q(matric_number__icontains=q)
            )

        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from circulation.services import get_unpaid_fines_total
        from circulation.models import BorrowRecord

        students_with_stats = []
        for s in context['students']:
            active_count = BorrowRecord.objects.filter(student=s, return_date__isnull=True).count()
            unpaid_total = get_unpaid_fines_total(s)
            students_with_stats.append({
                'student': s,
                'active_loans': active_count,
                'unpaid_fines': unpaid_total,
            })

        context['students_with_stats'] = students_with_stats
        context['q'] = self.request.GET.get('q', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class StaffStudentDetailView(StaffReadMixin, DetailView):
    """
    Librarian / Admin detail page for a single student (Section 7.3).
    Displays student's loans, reservations, and fine payment history.
    """
    model = User
    template_name = 'accounts/staff_student_detail.html'
    context_object_name = 'student'

    def get_queryset(self):
        return User.objects.filter(role=User.Role.STUDENT)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        from circulation.models import BorrowRecord
        from reservations.models import Reservation
        from fines.models import Fine
        from circulation.services import check_borrow_eligibility, get_unpaid_fines_total

        context['active_loans'] = BorrowRecord.objects.filter(
            student=student, return_date__isnull=True
        ).select_related('copy__book').order_by('due_date')

        context['past_loans'] = BorrowRecord.objects.filter(
            student=student, return_date__isnull=False
        ).select_related('copy__book').order_by('-return_date')[:15]

        context['reservations'] = Reservation.objects.filter(
            student=student
        ).select_related('book', 'copy').order_by('-reservation_date')[:15]

        context['fines'] = Fine.objects.filter(
            borrow_record__student=student
        ).select_related('borrow_record__copy__book', 'recorded_by').order_by('-date_created')

        ok, reason = check_borrow_eligibility(student)
        context['eligible'] = ok
        context['ineligibility_reason'] = reason
        context['unpaid_fines_total'] = get_unpaid_fines_total(student)

        return context


# ==============================================================================
# Student Profile (Section 7.2)
# ==============================================================================

class StudentProfileView(StudentRequiredMixin, View):
    """
    Student profile page (Section 7.2): read-only particulars & change password form.
    """
    template_name = 'accounts/student_profile.html'

    def get(self, request):
        from django.contrib.auth.forms import PasswordChangeForm
        form = PasswordChangeForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        from django.contrib.auth.forms import PasswordChangeForm
        from django.contrib.auth import update_session_auth_hash
        form = PasswordChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep logged in
            log_action(user, 'PASSWORD_CHANGE', "Student changed account password")
            messages.success(request, "Your password was changed successfully.")
            return redirect('student_profile')
        else:
            messages.error(request, "Please correct the errors in the password form.")

        return render(request, self.template_name, {'form': form})

