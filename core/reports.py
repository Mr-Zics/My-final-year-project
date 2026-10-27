"""
Accountability Reports for UniLibrary Management System.
Provides on-screen inspection, CSV export, and print view (?print=1)
for Librarian and Administrator roles.

Keeps exactly TWO reports per project simplification:
1. Overdue Books Report
2. Borrowing Activity Report
"""

import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Count

from accounts.permissions import StaffReadMixin
from circulation.models import BorrowRecord
from catalogue.models import Book


class ReportsHubView(StaffReadMixin, TemplateView):
    """Reports hub listing the two official accountability reports."""
    template_name = 'core/reports/hub.html'


class OverdueReportView(StaffReadMixin, View):
    """Report 1: Overdue Books."""
    def get(self, request):
        today = date.today()
        loans = BorrowRecord.objects.filter(
            return_date__isnull=True,
            due_date__lt=today
        ).select_related('student', 'copy__book').order_by('due_date')

        total_estimated = sum((l.estimated_fine for l in loans), Decimal('0.00'))

        if request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="overdue_report_{today}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Student Name', 'Matric Number', 'Book Title', 'Accession', 'Due Date (DD/MM/YYYY)', 'Days Overdue', 'Estimated Fine (NGN)'])
            for l in loans:
                writer.writerow([
                    l.student.full_name,
                    l.student.matric_number or 'N/A',
                    l.copy.book.title,
                    l.copy.accession_number,
                    l.due_date.strftime('%d/%m/%Y'),
                    l.days_overdue,
                    l.estimated_fine,
                ])
            writer.writerow(['TOTALS', '', '', '', '', len(loans), total_estimated])
            return response

        context = {
            'report_title': 'Overdue Books Accountability Report',
            'loans': loans,
            'total_count': loans.count(),
            'total_estimated': total_estimated,
            'is_print': request.GET.get('print') == '1',
            'generated_at': datetime.now(),
        }
        return render(request, 'core/reports/report_overdue.html', context)


class BorrowingActivityReportView(StaffReadMixin, View):
    """Report 2: Borrowing Activity."""
    def get(self, request):
        today = date.today()
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=30)

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                end_date = today
        else:
            end_date = today

        loans = BorrowRecord.objects.filter(
            borrow_date__gte=start_date,
            borrow_date__lte=end_date,
        ).select_related('student', 'copy__book', 'issued_by').order_by('-borrow_date')

        total_issued = loans.count()
        total_returned = loans.filter(return_date__isnull=False).count()

        # Top 10 most borrowed books in period
        top_books = Book.objects.filter(
            copies__borrow_records__borrow_date__gte=start_date,
            copies__borrow_records__borrow_date__lte=end_date
        ).annotate(borrow_count=Count('copies__borrow_records')).order_by('-borrow_count')[:10]

        if request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="borrowing_activity_{start_date}_to_{end_date}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Date Borrowed (DD/MM/YYYY)', 'Student Name', 'Book Title', 'Issued By', 'Due Date (DD/MM/YYYY)', 'Return Date (DD/MM/YYYY)'])
            for l in loans:
                writer.writerow([
                    l.borrow_date.strftime('%d/%m/%Y'),
                    l.student.full_name,
                    l.copy.book.title,
                    l.issued_by.full_name if l.issued_by else 'Staff',
                    l.due_date.strftime('%d/%m/%Y'),
                    l.return_date.strftime('%d/%m/%Y') if l.return_date else 'Active',
                ])
            writer.writerow(['TOTALS', f'Issued: {total_issued}', f'Returned: {total_returned}', '', '', ''])
            return response

        context = {
            'report_title': 'Borrowing & Circulation Activity Report',
            'loans': loans,
            'start_date': start_date,
            'end_date': end_date,
            'total_issued': total_issued,
            'total_returned': total_returned,
            'top_books': top_books,
            'is_print': request.GET.get('print') == '1',
            'generated_at': datetime.now(),
        }
        return render(request, 'core/reports/report_activity.html', context)
