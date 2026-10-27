"""
Acceptance and unit tests for UniLibrary Catalogue module.
Covers Section 12 Acceptance Test T29, search, filters, category guards, and role permissions.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from accounts.models import User
from catalogue.models import Category, Book, Copy
from catalogue.services import (
    create_book,
    add_copies_to_book,
    withdraw_copy,
    delete_category,
)


class CatalogueTestCase(TestCase):
    """Test suite covering Phase 2 requirements and Acceptance Test T29."""

    def setUp(self):
        self.client = Client()

        # Users
        self.admin = User.objects.create_superuser(
            email="admin@demo.edu.ng",
            password="AdminPassword123",
            full_name="Adaeze Admin"
        )
        self.librarian = User.objects.create_user(
            email="librarian@demo.edu.ng",
            password="LibrarianPassword123",
            full_name="Emmanuel Librarian",
            role=User.Role.LIBRARIAN
        )
        self.student = User.objects.create_user(
            email="student@demo.edu.ng",
            password="StudentPassword123",
            full_name="Amina Student",
            matric_number="2022/CSC/001",
            role=User.Role.STUDENT
        )

        # Categories
        self.cat_cs = Category.objects.create(category_name="Computer Science", code="CS")
        self.cat_ma = Category.objects.create(category_name="Mathematics", code="MA")
        self.cat_empty = Category.objects.create(category_name="General Studies", code="GS")

        # Books and Copies
        self.book1 = create_book(
            title="Introduction to Algorithms",
            author="Thomas H. Cormen, Charles E. Leiserson",
            isbn="9780262033848",
            category=self.cat_cs,
            num_copies=2,
            location="Main Library, Shelf CS-1",
            user=self.librarian
        )
        self.book2 = create_book(
            title="Discrete Mathematics and Its Applications",
            author="Kenneth H. Rosen",
            isbn="9781259676512",
            category=self.cat_ma,
            num_copies=1,
            location="Main Library, Shelf MA-1",
            user=self.librarian
        )

    # -------------------------------------------------------------------------
    # 1. Model & Helper Tests
    # -------------------------------------------------------------------------
    def test_accession_number_formatting(self):
        """Verify accession numbers are zero-padded C0001 per Section 4.4."""
        copy1 = self.book1.copies.first()
        self.assertEqual(copy1.accession_number, f"C{copy1.id:04d}")

    def test_book_availability_helpers(self):
        """Verify dynamic calculation of book availability without static status column."""
        self.assertEqual(self.book1.available_copies_count(), 2)
        self.assertEqual(self.book1.total_copies_count(), 2)
        self.assertTrue(self.book1.is_available())

        # Change one copy to BORROWED
        copy1 = self.book1.copies.first()
        copy1.status = Copy.Status.BORROWED
        copy1.save()

        self.assertEqual(self.book1.available_copies_count(), 1)
        self.assertEqual(self.book1.total_copies_count(), 2)
        self.assertTrue(self.book1.is_available())

        # Change second copy to RESERVED
        copy2 = self.book1.copies.last()
        copy2.status = Copy.Status.RESERVED
        copy2.save()

        self.assertEqual(self.book1.available_copies_count(), 0)
        self.assertFalse(self.book1.is_available())

    # -------------------------------------------------------------------------
    # 2. Acceptance Test T29: Withdraw a borrowed copy -> Refused
    # -------------------------------------------------------------------------
    def test_T29_withdraw_borrowed_or_reserved_copy_refused(self):
        """
        T29: Verify that a copy cannot be withdrawn if its status is BORROWED or RESERVED,
        and that withdrawing an AVAILABLE copy succeeds.
        """
        copies = list(self.book1.copies.all())
        copy_borrowed = copies[0]
        copy_reserved = copies[1]

        # 1. Borrowed copy withdrawal refusal
        copy_borrowed.status = Copy.Status.BORROWED
        copy_borrowed.save()

        can_withdraw, reason = copy_borrowed.can_withdraw()
        self.assertFalse(can_withdraw)
        self.assertIn("borrowed", reason.lower())

        with self.assertRaises(ValidationError):
            withdraw_copy(copy_borrowed, user=self.librarian)

        # Verify status did not change in DB
        copy_borrowed.refresh_from_db()
        self.assertEqual(copy_borrowed.status, Copy.Status.BORROWED)

        # 2. Reserved copy withdrawal refusal
        copy_reserved.status = Copy.Status.RESERVED
        copy_reserved.save()

        can_withdraw, reason = copy_reserved.can_withdraw()
        self.assertFalse(can_withdraw)
        self.assertIn("reservation", reason.lower())

        with self.assertRaises(ValidationError):
            withdraw_copy(copy_reserved, user=self.librarian)

        copy_reserved.refresh_from_db()
        self.assertEqual(copy_reserved.status, Copy.Status.RESERVED)

        # 3. Available copy withdrawal success
        copy_avail = self.book2.copies.first()
        self.assertEqual(copy_avail.status, Copy.Status.AVAILABLE)

        withdrawn_copy = withdraw_copy(copy_avail, user=self.librarian)
        self.assertEqual(withdrawn_copy.status, Copy.Status.WITHDRAWN)
        copy_avail.refresh_from_db()
        self.assertEqual(copy_avail.status, Copy.Status.WITHDRAWN)

        # Total active copies excludes withdrawn
        self.assertEqual(self.book2.total_copies_count(), 0)

    # -------------------------------------------------------------------------
    # 3. Category Deletion Guard (Section 7.3)
    # -------------------------------------------------------------------------
    def test_category_deletion_blocked_when_books_assigned(self):
        """Verify category deletion is blocked if books are assigned."""
        with self.assertRaises(ValidationError):
            delete_category(self.cat_cs, user=self.librarian)

        # Empty category deletion succeeds
        result = delete_category(self.cat_empty, user=self.librarian)
        self.assertTrue(result)
        self.assertFalse(Category.objects.filter(pk=self.cat_empty.pk).exists())

    # -------------------------------------------------------------------------
    # 4. Search and Filter Tests (Public Catalogue)
    # -------------------------------------------------------------------------
    def test_catalogue_search_by_title(self):
        """Verify search by partial title."""
        response = self.client.get(reverse("catalogue_list"), {"q": "Algorithms"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduction to Algorithms")
        self.assertNotContains(response, "Discrete Mathematics")

    def test_catalogue_search_by_author(self):
        """Verify search by author name."""
        response = self.client.get(reverse("catalogue_list"), {"q": "Rosen"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Discrete Mathematics")
        self.assertNotContains(response, "Introduction to Algorithms")

    def test_catalogue_search_by_isbn(self):
        """Verify search by ISBN."""
        response = self.client.get(reverse("catalogue_list"), {"q": "9780262033848"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduction to Algorithms")

    def test_catalogue_filter_by_category(self):
        """Verify filtering books by Category ID."""
        response = self.client.get(reverse("catalogue_list"), {"category": self.cat_ma.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Discrete Mathematics")
        self.assertNotContains(response, "Introduction to Algorithms")

    def test_catalogue_filter_by_availability(self):
        """Verify availability filtering."""
        # Set all copies of book1 to BORROWED
        for copy in self.book1.copies.all():
            copy.status = Copy.Status.BORROWED
            copy.save()

        # Available only -> should only show book2
        response_avail = self.client.get(reverse("catalogue_list"), {"availability": "available"})
        self.assertContains(response_avail, "Discrete Mathematics")
        self.assertNotContains(response_avail, "Introduction to Algorithms")

        # On loan only -> should only show book1
        response_on_loan = self.client.get(reverse("catalogue_list"), {"availability": "on_loan"})
        self.assertContains(response_on_loan, "Introduction to Algorithms")
        self.assertNotContains(response_on_loan, "Discrete Mathematics")

    # -------------------------------------------------------------------------
    # 5. Detail & Permissions Tests
    # -------------------------------------------------------------------------
    def test_public_book_detail_view(self):
        """Verify public access to book details page."""
        response = self.client.get(reverse("book_detail", kwargs={"pk": self.book1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Introduction to Algorithms")
        self.assertContains(response, "Main Library, Shelf CS-1")
        self.assertContains(response, "Log in with your university student matric account")

    def test_student_cannot_access_staff_book_management(self):
        """Verify student receives 403 when attempting to access staff books list."""
        self.client.force_login(self.student)
        response = self.client.get(reverse("staff_book_list"))
        self.assertEqual(response.status_code, 403)

    def test_admin_read_only_staff_read_mixin(self):
        """
        Verify Administrator can GET staff book list, but cannot POST to add book
        (Librarian-only mutation per Section 3).
        """
        self.client.force_login(self.admin)
        get_response = self.client.get(reverse("staff_book_list"))
        self.assertEqual(get_response.status_code, 200)

        # Attempt to add book as Admin -> 403
        post_response = self.client.post(reverse("staff_book_add"), {
            "title": "Unauthorized Book",
            "author": "Test Author",
            "isbn": "9781111111111",
            "category": self.cat_cs.id,
            "num_copies": 1
        })
        self.assertEqual(post_response.status_code, 403)

    def test_librarian_can_add_book_and_copies(self):
        """Verify Librarian can create a book and extra physical copies."""
        self.client.force_login(self.librarian)
        post_response = self.client.post(reverse("staff_book_add"), {
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "author": "Robert C. Martin",
            "isbn": "9780132350884",
            "category": self.cat_cs.id,
            "num_copies": 3,
            "location": "Main Library, Shelf CS-3"
        })
        self.assertEqual(post_response.status_code, 302)

        created_book = Book.objects.filter(isbn="9780132350884").first()
        self.assertIsNotNone(created_book)
        self.assertEqual(created_book.copies.count(), 3)
        self.assertEqual(created_book.copies.first().whereabouts, "Main Library, Shelf CS-3")
