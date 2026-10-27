"""
Core views for public landing, error handling, and automation scheduler.
Settings, System Logs, and Backup & Restore views have been removed per project simplification.
"""

from datetime import date
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.management import call_command

from accounts.permissions import AdminRequiredMixin


class HomeView(TemplateView):
    """
    Renders the public library home page with collection highlights,
    circulation desk hours, search entry, and student access links.
    """
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from catalogue.models import Book
            context["latest_books"] = Book.objects.select_related("category").prefetch_related("copies").order_by("-id")[:6]
        except Exception:
            context["latest_books"] = []
        return context


class AdminDailyJobView(AdminRequiredMixin, View):
    """
    Administrator Daily Automation Job page.
    Allows manually triggering the daily check command.
    """
    template_name = "core/admin_daily_job.html"

    def get(self, request):
        context = {
            'today': date.today(),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        sim_date = request.POST.get('simulation_date', '').strip()
        kwargs = {}

        if sim_date:
            kwargs['date'] = sim_date

        try:
            call_command('run_daily_job', **kwargs)
            messages.success(request, f"Daily automation job ran successfully{' for date ' + sim_date if sim_date else ''}.")
        except Exception as e:
            messages.error(request, f"Failed to run daily job: {str(e)}")

        return redirect('admin_daily_job')


# ==============================================================================
# Custom Error Handlers
# ==============================================================================

def custom_403_view(request, exception=None):
    """Custom friendly 403 Forbidden error page."""
    return render(request, "403.html", {
        "error_message": str(exception) if exception else "You do not have permission to access this page."
    }, status=403)


def custom_404_view(request, exception=None):
    """Custom friendly 404 Not Found error page."""
    return render(request, "404.html", status=404)


def custom_500_view(request):
    """Custom friendly 500 Internal Server Error page."""
    return render(request, "500.html", status=500)
