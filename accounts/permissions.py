"""
Role-based permission mixins and helpers for UniLibrary.
Implements Section 3 of the Build Specification.
"""

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from .models import User


def get_role_redirect_url(user):
    """
    Returns the role-appropriate post-login landing page.
    Student -> /student/
    Librarian -> /staff/
    Administrator -> /manage/
    """
    if not user or not user.is_authenticated:
        return 'login'
    if user.role == User.Role.STUDENT:
        return 'student_dashboard'
    elif user.role == User.Role.LIBRARIAN:
        return 'staff_dashboard'
    elif user.role == User.Role.ADMINISTRATOR:
        return 'admin_dashboard'
    return 'home'


class BaseRoleRequiredMixin(AccessMixin):
    """
    Base mixin ensuring:
    1. Unauthenticated users are redirected to login.
    2. Authenticated users with the wrong role get a 403 PermissionDenied error.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_active:
            raise PermissionDenied("Your account is deactivated. Please contact the library.")

        if request.user.role not in self.allowed_roles:
            raise PermissionDenied("You do not have permission to access this page.")

        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(BaseRoleRequiredMixin):
    """Restricts access exclusively to Students."""
    allowed_roles = [User.Role.STUDENT]


class LibrarianRequiredMixin(BaseRoleRequiredMixin):
    """Restricts access to Librarians with full read/write capabilities."""
    allowed_roles = [User.Role.LIBRARIAN]


class AdminRequiredMixin(BaseRoleRequiredMixin):
    """Restricts access exclusively to Administrators."""
    allowed_roles = [User.Role.ADMINISTRATOR]


class StaffReadMixin(AccessMixin):
    """
    Librarian or Administrator may view (GET); only Librarian may perform actions (POST).
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_active:
            raise PermissionDenied("Your account is deactivated. Please contact the library.")

        # Both Librarian and Administrator may view (GET, HEAD, OPTIONS)
        if request.user.role not in [User.Role.LIBRARIAN, User.Role.ADMINISTRATOR]:
            raise PermissionDenied("You do not have staff permission to view this page.")

        # Only Librarian may perform mutating actions (POST, PUT, DELETE)
        if request.method not in ['GET', 'HEAD', 'OPTIONS']:
            if request.user.role != User.Role.LIBRARIAN:
                raise PermissionDenied("Only librarians can perform circulation and catalogue modifications.")

        return super().dispatch(request, *args, **kwargs)
