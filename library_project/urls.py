"""
URL configuration for library_project.

Web-Based Library Management System with Automated Book Reservation
and Overdue Notifications.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.views import (
    HomeView,
    AdminDailyJobView,
    custom_403_view,
    custom_404_view,
    custom_500_view,
)
from core.reports import (
    ReportsHubView,
    OverdueReportView,
    BorrowingActivityReportView,
)
from accounts.views import (
    LoginView,
    StudentDashboardView,
    StaffDashboardView,
    AdminDashboardView,
    AdminUserListView,
    AdminUserCreateView,
    AdminUserUpdateView,
    AdminUserResetPasswordView,
    AdminUserToggleStatusView,
    StaffStudentListView,
    StaffStudentDetailView,
    StudentProfileView,
)

urlpatterns = [
    # Developer Django admin site (not linked from navigation per Section 10)
    path("django-admin/", admin.site.urls),

    # Public Home page
    path("", HomeView.as_view(), name="home"),

    # Accounts Authentication (Login, Logout, Register)
    path("accounts/", include("accounts.urls")),
    path("login/", LoginView.as_view(), name="login_shortcut"),

    # Role-Based Landing Pages (Section 3)
    path("student/", StudentDashboardView.as_view(), name="student_dashboard"),
    path("student/profile/", StudentProfileView.as_view(), name="student_profile"),
    path("staff/", StaffDashboardView.as_view(), name="staff_dashboard"),
    path("manage/", AdminDashboardView.as_view(), name="admin_dashboard"),

    # Staff Student Directory (Section 7.3)
    path("staff/students/", StaffStudentListView.as_view(), name="staff_student_list"),
    path("staff/students/<int:pk>/", StaffStudentDetailView.as_view(), name="staff_student_detail"),

    # Administrator User Management (Section 7.4)
    path("manage/users/", AdminUserListView.as_view(), name="admin_user_list"),
    path("manage/users/add/", AdminUserCreateView.as_view(), name="admin_user_add"),
    path("manage/users/<int:pk>/edit/", AdminUserUpdateView.as_view(), name="admin_user_edit"),
    path("manage/users/<int:pk>/reset-password/", AdminUserResetPasswordView.as_view(), name="admin_user_reset_password"),
    path("manage/users/<int:pk>/toggle-status/", AdminUserToggleStatusView.as_view(), name="admin_user_toggle_status"),

    # Administrator Scheduled Automation Job
    path("manage/job/", AdminDailyJobView.as_view(), name="admin_daily_job"),

    # Accountability Reports (Exactly 2 reports: Overdue Books & Borrowing Activity)
    path("staff/reports/", ReportsHubView.as_view(), name="reports_hub"),
    path("manage/reports/", ReportsHubView.as_view(), name="admin_reports_hub"),
    path("staff/reports/overdue/", OverdueReportView.as_view(), name="report_overdue"),
    path("staff/reports/activity/", BorrowingActivityReportView.as_view(), name="report_activity"),

    # Module URLs
    path("", include("catalogue.urls")),
    path("", include("circulation.urls")),
    path("", include("reservations.urls")),
    path("", include("fines.urls")),
    path("", include("notifications.urls")),
]

# Media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom Error Handlers (Section 7.5)
handler403 = 'core.views.custom_403_view'
handler404 = 'core.views.custom_404_view'
handler500 = 'core.views.custom_500_view'
