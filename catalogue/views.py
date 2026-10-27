"""
Catalogue views for UniLibrary.
Implements public search, book detail views, and staff collection management per Sections 7.1 and 7.3.
"""

from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Count
from accounts.permissions import StaffReadMixin, LibrarianRequiredMixin
from .models import Category, Book, Copy
from .forms import (
    CatalogueSearchForm,
    BookAddForm,
    BookEditForm,
    AddCopiesForm,
    EditCopyLocationForm,
    CategoryForm,
)
from .services import (
    create_book,
    update_book,
    add_copies_to_book,
    update_copy_location,
    withdraw_copy,
    create_category,
    update_category,
    delete_category,
)


class CatalogueListView(ListView):
    """
    Public catalogue search & filter page.
    Card grid layout (12 per page) with real-time availability badges (Section 7.1 & Screen 3).
    """
    model = Book
    template_name = "catalogue/catalogue_list.html"
    context_object_name = "books"
    paginate_by = 12

    def get_queryset(self):
        queryset = Book.objects.select_related("category").prefetch_related("copies").order_by("title")
        form = CatalogueSearchForm(self.request.GET)

        if form.is_valid():
            q = form.cleaned_data.get("q")
            category = form.cleaned_data.get("category")
            availability = form.cleaned_data.get("availability")

            if q:
                queryset = queryset.filter(
                    Q(title__icontains=q) |
                    Q(author__icontains=q) |
                    Q(isbn__icontains=q)
                )

            if category:
                queryset = queryset.filter(category=category)

            if availability == "available":
                # Filter books with at least one AVAILABLE copy
                queryset = queryset.filter(copies__status=Copy.Status.AVAILABLE).distinct()
            elif availability == "on_loan":
                # Filter books where all copies are not available (e.g. BORROWED, RESERVED)
                available_book_ids = Copy.objects.filter(status=Copy.Status.AVAILABLE).values_list("book_id", flat=True)
                queryset = queryset.exclude(id__in=available_book_ids).filter(copies__isnull=False).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = CatalogueSearchForm(self.request.GET)
        context["categories"] = Category.objects.annotate(num_books=Count("books")).order_by("category_name")
        context["total_results"] = self.get_queryset().count()

        # Build clean querystring for pagination links
        params = self.request.GET.copy()
        if "page" in params:
            del params["page"]
        context["query_string"] = params.urlencode()
        return context


class BookDetailView(DetailView):
    """
    Public and student book details page (Section 7.1 & Screen 4).
    Displays bibliographic details, availability summary, copies list, and reservation panel.
    """
    model = Book
    template_name = "catalogue/book_detail.html"
    context_object_name = "book"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object
        copies = book.copies.all().order_by("id")
        context["copies"] = copies
        context["available_count"] = book.available_copies_count()
        context["total_count"] = book.total_copies_count()
        context["waiting_count"] = book.waiting_count()
        context["ready_count"] = book.ready_count()

        # Context for reservation panel
        user = self.request.user
        context["is_student"] = user.is_authenticated and getattr(user, "role", "") == "STUDENT"
        context["has_active_reservation"] = False
        context["has_active_loan"] = False

        if context["is_student"]:
            try:
                # Check active reservation
                from reservations.models import Reservation
                active_res = Reservation.objects.filter(
                    student=user,
                    book=book,
                    status__in=["WAITING", "READY"]
                ).first()
                if active_res:
                    context["has_active_reservation"] = True
                    context["user_reservation"] = active_res
            except Exception:
                pass

            try:
                # Check active loan
                from circulation.models import BorrowRecord
                active_loan = BorrowRecord.objects.filter(
                    student=user,
                    copy__book=book,
                    return_date__isnull=True
                ).exists()
                context["has_active_loan"] = active_loan
            except Exception:
                pass

            try:
                # Check active reservations count against limit
                from core.services import get_int
                from reservations.models import Reservation
                max_res = get_int('max_reservations_per_student') or 4
                active_count = Reservation.objects.filter(
                    student=user,
                    status__in=[Reservation.Status.WAITING, Reservation.Status.READY]
                ).count()
                context["max_reservations_limit"] = max_res
                context["active_reservations_count"] = active_count
                context["max_reservations_reached"] = (active_count >= max_res)
            except Exception:
                context["max_reservations_reached"] = False

        return context


# =====================================================================
# STAFF / LIBRARIAN CATALOGUE MANAGEMENT (Section 7.3)
# =====================================================================

class StaffBookListView(StaffReadMixin, ListView):
    """
    Librarian and Administrator book management list.
    Table: Title, Author, Category, Total Copies, Available Copies, Actions.
    """
    model = Book
    template_name = "catalogue/staff_book_list.html"
    context_object_name = "books"
    paginate_by = 15

    def get_queryset(self):
        queryset = Book.objects.select_related("category").prefetch_related("copies").order_by("title")
        q = self.request.GET.get("q", "").strip()
        cat_id = self.request.GET.get("category", "").strip()

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(author__icontains=q) |
                Q(isbn__icontains=q)
            )
        if cat_id:
            queryset = queryset.filter(category_id=cat_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all().order_by("category_name")
        context["selected_category"] = self.request.GET.get("category", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["total_books"] = Book.objects.count()
        context["total_copies"] = Copy.objects.count()
        context["available_copies"] = Copy.objects.filter(status=Copy.Status.AVAILABLE).count()

        params = self.request.GET.copy()
        if "page" in params:
            del params["page"]
        context["query_string"] = params.urlencode()
        return context


class StaffBookCreateView(LibrarianRequiredMixin, View):
    """
    Adds a new book and creates its initial physical accession copies (Section 7.3).
    """
    template_name = "catalogue/staff_book_form.html"

    def get(self, request):
        form = BookAddForm()
        return render(request, self.template_name, {
            "form": form,
            "page_title": "Add New Book",
            "is_edit": False
        })

    def post(self, request):
        form = BookAddForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                book = create_book(
                    title=form.cleaned_data["title"],
                    author=form.cleaned_data["author"],
                    isbn=form.cleaned_data["isbn"],
                    category=form.cleaned_data["category"],
                    num_copies=form.cleaned_data["num_copies"],
                    location=form.cleaned_data["location"],
                    cover_image=form.cleaned_data.get("cover_image"),
                    description=form.cleaned_data.get("description", ""),
                    user=request.user
                )
                messages.success(
                    request,
                    f"Book '{book.title}' added successfully with {form.cleaned_data['num_copies']} accession copy(ies)."
                )
                return redirect("staff_book_copies", pk=book.pk)
            except ValidationError as e:
                form.add_error(None, e.message if hasattr(e, "message") else str(e))
        return render(request, self.template_name, {
            "form": form,
            "page_title": "Add New Book",
            "is_edit": False
        })


class StaffBookUpdateView(LibrarianRequiredMixin, View):
    """Updates bibliographic details for an existing book."""
    template_name = "catalogue/staff_book_form.html"

    def get(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        form = BookEditForm(instance=book)
        return render(request, self.template_name, {
            "form": form,
            "book": book,
            "page_title": f"Edit Book: {book.title}",
            "is_edit": True
        })

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        form = BookEditForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            try:
                update_book(
                    book=book,
                    title=form.cleaned_data["title"],
                    author=form.cleaned_data["author"],
                    isbn=form.cleaned_data["isbn"],
                    category=form.cleaned_data["category"],
                    description=form.cleaned_data.get("description", ""),
                    cover_image=form.cleaned_data.get("cover_image"),
                    user=request.user
                )
                messages.success(request, f"Updated details for '{book.title}'.")
                return redirect("staff_book_list")
            except ValidationError as e:
                form.add_error(None, e.message if hasattr(e, "message") else str(e))
        return render(request, self.template_name, {
            "form": form,
            "book": book,
            "page_title": f"Edit Book: {book.title}",
            "is_edit": True
        })


class StaffBookCopiesView(StaffReadMixin, View):
    """
    Manages physical inventory copies for a book (Section 7.3 & Screen 13).
    Displays table of copies, accession numbers, statuses, and provides forms to add/relocate copies.
    """
    template_name = "catalogue/staff_book_copies.html"

    def get(self, request, pk):
        book = get_object_or_404(Book.objects.select_related("category"), pk=pk)
        copies = book.copies.all().order_by("id")
        add_form = AddCopiesForm(initial={
            "quantity": 1,
            "location": f"Main Library, Shelf {book.category.code or 'GEN'}-1"
        })
        return render(request, self.template_name, {
            "book": book,
            "copies": copies,
            "add_form": add_form,
        })

    def post(self, request, pk):
        """Adds new copies to the book."""
        book = get_object_or_404(Book, pk=pk)
        add_form = AddCopiesForm(request.POST)
        if add_form.is_valid():
            try:
                copies = add_copies_to_book(
                    book=book,
                    quantity=add_form.cleaned_data["quantity"],
                    location=add_form.cleaned_data["location"],
                    user=request.user
                )
                messages.success(
                    request,
                    f"Successfully created {len(copies)} new copy(ies) for '{book.title}'."
                )
                return redirect("staff_book_copies", pk=book.pk)
            except ValidationError as e:
                messages.error(request, e.message if hasattr(e, "message") else str(e))
        copies = book.copies.all().order_by("id")
        return render(request, self.template_name, {
            "book": book,
            "copies": copies,
            "add_form": add_form,
        })


class StaffCopyRelocateView(LibrarianRequiredMixin, View):
    """Updates the shelf location of a copy."""
    def post(self, request, pk):
        copy = get_object_or_404(Copy, pk=pk)
        new_location = request.POST.get("location", "").strip()
        if new_location:
            try:
                update_copy_location(copy, new_location, user=request.user)
                messages.success(request, f"Updated location of copy {copy.accession_number} to '{new_location}'.")
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Shelf location cannot be blank.")
        return redirect("staff_book_copies", pk=copy.book_id)


class StaffCopyWithdrawView(LibrarianRequiredMixin, View):
    """
    Withdraws a physical copy from circulation.
    Enforces Section 4.4 and Acceptance Test T29:
    Blocked if copy is BORROWED or RESERVED.
    """
    template_name = "catalogue/staff_copy_withdraw_confirm.html"

    def get(self, request, pk):
        copy = get_object_or_404(Copy.objects.select_related("book"), pk=pk)
        can_withdraw, reason = copy.can_withdraw()
        return render(request, self.template_name, {
            "copy": copy,
            "can_withdraw": can_withdraw,
            "reason": reason,
        })

    def post(self, request, pk):
        copy = get_object_or_404(Copy, pk=pk)
        try:
            withdraw_copy(copy, user=request.user)
            messages.success(
                request,
                f"Copy {copy.accession_number} of '{copy.book.title}' has been withdrawn from circulation."
            )
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        return redirect("staff_book_copies", pk=copy.book_id)


class StaffCategoryListView(StaffReadMixin, View):
    """
    Category management page (Section 7.3).
    Lists categories with book counts; allows adding and renaming.
    """
    template_name = "catalogue/staff_category_list.html"

    def get(self, request):
        categories = Category.objects.annotate(num_books=Count("books")).order_by("category_name")
        form = CategoryForm()
        return render(request, self.template_name, {
            "categories": categories,
            "form": form,
        })

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                cat = create_category(
                    category_name=form.cleaned_data["category_name"],
                    code=form.cleaned_data["code"],
                    user=request.user
                )
                messages.success(request, f"Category '{cat.category_name}' created.")
                return redirect("staff_category_list")
            except ValidationError as e:
                messages.error(request, e.message if hasattr(e, "message") else str(e))
        categories = Category.objects.annotate(num_books=Count("books")).order_by("category_name")
        return render(request, self.template_name, {
            "categories": categories,
            "form": form,
        })


class StaffCategoryUpdateView(LibrarianRequiredMixin, View):
    """Renames or updates category shelf code."""
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            try:
                update_category(
                    category=category,
                    category_name=form.cleaned_data["category_name"],
                    code=form.cleaned_data["code"],
                    user=request.user
                )
                messages.success(request, f"Updated category '{category.category_name}'.")
            except ValidationError as e:
                messages.error(request, e.message if hasattr(e, "message") else str(e))
        else:
            messages.error(request, "Invalid category details.")
        return redirect("staff_category_list")


class StaffCategoryDeleteView(LibrarianRequiredMixin, View):
    """
    Deletes a category if no books are assigned.
    Enforces Section 7.3: Deletion blocked if books exist.
    """
    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        try:
            delete_category(category, user=request.user)
            messages.success(request, f"Category '{category.category_name}' deleted.")
        except ValidationError as e:
            messages.error(request, e.message if hasattr(e, "message") else str(e))
        return redirect("staff_category_list")
