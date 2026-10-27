"""
Notification views for UniLibrary Management System.
Implements Student In-App Notifications (Section 7.2).
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView
from django.contrib import messages
from accounts.permissions import StudentRequiredMixin
from notifications.models import Notification


class StudentNotificationListView(StudentRequiredMixin, ListView):
    """
    Student notification center (Section 7.2).
    Displays in-app notifications sorted by newest first with unread markers.
    """
    model = Notification
    template_name = 'notifications/student_notifications.html'
    context_object_name = 'notifications'
    paginate_by = 25

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            channel=Notification.Channel.INAPP
        ).order_by('-date_sent')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user,
            channel=Notification.Channel.INAPP,
            is_read=False
        ).count()
        return context


class MarkNotificationReadView(StudentRequiredMixin, View):
    """Marks a single notification as read."""
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save()
        return redirect('student_notifications')


class MarkAllNotificationsReadView(StudentRequiredMixin, View):
    """Marks all user's notifications as read."""
    def post(self, request):
        Notification.objects.filter(
            user=request.user,
            channel=Notification.Channel.INAPP,
            is_read=False
        ).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('student_notifications')
