"""
Notification URLs for UniLibrary Management System.
Implements Student Notification Center (Section 7.2).
"""

from django.urls import path
from notifications.views import (
    StudentNotificationListView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
)

urlpatterns = [
    path("student/notifications/", StudentNotificationListView.as_view(), name="student_notifications"),
    path("student/notifications/<int:pk>/read/", MarkNotificationReadView.as_view(), name="notification_mark_read"),
    path("student/notifications/mark-all-read/", MarkAllNotificationsReadView.as_view(), name="notification_mark_all_read"),
]
