"""
Circulation URLs for UniLibrary Management System.
Implements Issue, Return, Active Loans, Overdue, and Student My Loans (Sections 7.2 & 7.3).
"""

from django.urls import path
from circulation.views import (
    StaffIssueView,
    StaffReturnView,
    StaffActiveLoansView,
    StaffOverdueView,
    StudentLoansView,
)

urlpatterns = [
    # Staff Circulation Desk
    path("staff/issue/", StaffIssueView.as_view(), name="staff_issue"),
    path("staff/return/", StaffReturnView.as_view(), name="staff_return"),
    path("staff/loans/", StaffActiveLoansView.as_view(), name="staff_loans"),
    path("staff/overdue/", StaffOverdueView.as_view(), name="staff_overdue"),

    # Student Loans
    path("student/loans/", StudentLoansView.as_view(), name="student_loans"),
]

