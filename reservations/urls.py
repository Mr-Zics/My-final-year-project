"""
Reservation URLs for UniLibrary Management System.
Implements Student reservations and Staff Queue management (Sections 7.1, 7.2, 7.3).
"""

from django.urls import path
from reservations.views import (
    ReserveBookView,
    StudentReservationListView,
    StudentCancelReservationView,
    StaffReservationQueueView,
    StaffCancelReservationView,
)

urlpatterns = [
    # Book reservation action (Section 7.1)
    path("books/<int:pk>/reserve/", ReserveBookView.as_view(), name="reserve_book"),

    # Student reservation portal (Section 7.2)
    path("student/reservations/", StudentReservationListView.as_view(), name="student_reservations"),
    path("student/reservations/<int:pk>/cancel/", StudentCancelReservationView.as_view(), name="student_cancel_reservation"),

    # Staff reservation desk (Section 7.3)
    path("staff/reservations/", StaffReservationQueueView.as_view(), name="staff_reservation_queue"),
    path("staff/reservations/<int:pk>/cancel/", StaffCancelReservationView.as_view(), name="staff_cancel_reservation"),
]
