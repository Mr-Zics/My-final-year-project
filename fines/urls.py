"""
Fine management URLs for UniLibrary Management System.
Implements Student My Fines and Staff Fine payment recording.
Waiver action and page removed per project simplification.
"""

from django.urls import path
from fines.views import (
    StudentFinesView,
    StaffFinesListView,
    StaffRecordPaymentView,
)

urlpatterns = [
    # Student fine ledger
    path("student/fines/", StudentFinesView.as_view(), name="student_fines"),

    # Staff fine desk
    path("staff/fines/", StaffFinesListView.as_view(), name="staff_fines"),
    path("staff/fines/<int:pk>/pay/", StaffRecordPaymentView.as_view(), name="staff_fine_pay"),
]
