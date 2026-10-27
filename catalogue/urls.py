"""
URL patterns for UniLibrary Catalogue module.
Implements public search, book detail views, and librarian management per Section 7.
"""

from django.urls import path
from .views import (
    CatalogueListView,
    BookDetailView,
    StaffBookListView,
    StaffBookCreateView,
    StaffBookUpdateView,
    StaffBookCopiesView,
    StaffCopyRelocateView,
    StaffCopyWithdrawView,
    StaffCategoryListView,
    StaffCategoryUpdateView,
    StaffCategoryDeleteView,
)

urlpatterns = [
    # Public & Student Catalogue Routes (Section 7.1)
    path("catalogue/", CatalogueListView.as_view(), name="catalogue_list"),
    path("catalogue/book/<int:pk>/", BookDetailView.as_view(), name="book_detail"),
    path("catalogue/book/<int:pk>/view/", BookDetailView.as_view(), name="catalogue_detail"),

    # Staff / Librarian Collection Management Routes (Section 7.3)
    path("staff/books/", StaffBookListView.as_view(), name="staff_book_list"),
    path("staff/books/add/", StaffBookCreateView.as_view(), name="staff_book_add"),
    path("staff/books/<int:pk>/edit/", StaffBookUpdateView.as_view(), name="staff_book_edit"),
    path("staff/books/<int:pk>/copies/", StaffBookCopiesView.as_view(), name="staff_book_copies"),
    path("staff/copies/<int:pk>/relocate/", StaffCopyRelocateView.as_view(), name="staff_copy_relocate"),
    path("staff/copies/<int:pk>/withdraw/", StaffCopyWithdrawView.as_view(), name="staff_copy_withdraw"),

    # Staff Category Management Routes (Section 7.3)
    path("staff/categories/", StaffCategoryListView.as_view(), name="staff_category_list"),
    path("staff/categories/<int:pk>/edit/", StaffCategoryUpdateView.as_view(), name="staff_category_edit"),
    path("staff/categories/<int:pk>/delete/", StaffCategoryDeleteView.as_view(), name="staff_category_delete"),
]
