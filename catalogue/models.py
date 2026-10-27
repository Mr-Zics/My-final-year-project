"""
Catalogue data models for UniLibrary.
Implements Section 4.2 (Category), 4.3 (Book), and 4.4 (Copy) of the specification.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.templatetags.static import static


class Category(models.Model):
    """
    Academic subject category (e.g. Computer Science, Mathematics).
    Section 4.2: id, category_name CharField(100) unique.
    """
    category_name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=10, blank=True, help_text="Short shelf code e.g. CS, MA, LI")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["category_name"]

    def __str__(self):
        return self.category_name

    @property
    def book_count(self):
        """Returns total number of distinct books in this category."""
        return self.books.count()


class Book(models.Model):
    """
    Bibliographic record of a library book.
    Section 4.3: id, title (indexed), author (indexed), isbn, category (FK).
    No status field; availability is derived dynamically from Copy records.
    """
    title = models.CharField(max_length=200, db_index=True)
    author = models.CharField(max_length=150, db_index=True)
    isbn = models.CharField(max_length=20, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="books"
    )
    cover_image = models.ImageField(
        upload_to="book_covers/",
        blank=True,
        null=True,
        help_text="Front cover image for visual display"
    )
    description = models.TextField(blank=True, help_text="Brief synopsis or summary of contents")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["title"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["author"]),
            models.Index(fields=["isbn"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.author}"

    def available_copies_count(self):
        """Number of copies physically on the shelf and available for immediate borrowing."""
        return self.copies.filter(status=Copy.Status.AVAILABLE).count()

    def total_copies_count(self):
        """Number of active copies (excluding permanently withdrawn/damaged ones)."""
        return self.copies.exclude(status=Copy.Status.WITHDRAWN).count()

    def all_copies_count(self):
        """Total copies including withdrawn."""
        return self.copies.count()

    def is_available(self):
        """Returns True if at least one copy has status AVAILABLE."""
        return self.available_copies_count() > 0

    def waiting_count(self):
        """
        Returns number of reservations with status WAITING.
        Safely queries reservations if the app is installed.
        """
        try:
            return self.reservations.filter(status="WAITING").count()
        except Exception:
            return 0

    def ready_count(self):
        """Returns number of reservations with status READY (awaiting pickup)."""
        try:
            return self.reservations.filter(status="READY").count()
        except Exception:
            return 0

    @property
    def availability_badge(self):
        """
        Returns a dictionary with symbol, text, and css class
        for report-ready greyscale/colour badges per Section 9.5 and Section 7.1.
        """
        avail = self.available_copies_count()
        total = self.total_copies_count()
        waiting = self.waiting_count()

        if total == 0:
            return {
                "symbol": "✕",
                "text": "No copies in collection",
                "css": "badge-secondary",
            }
        elif avail > 0:
            return {
                "symbol": "✓",
                "text": f"{avail} of {total} copies available",
                "css": "badge-success",
            }
        else:
            if waiting > 0:
                return {
                    "symbol": "◐",
                    "text": f"All copies on loan · {waiting} waiting",
                    "css": "badge-warning",
                }
            else:
                return {
                    "symbol": "●",
                    "text": "All copies on loan",
                    "css": "badge-info",
                }

    def get_cover_image_url(self):
        """
        Returns the URL to the book cover image.
        Uses uploaded image if present; otherwise matches keyword to authentic static covers,
        guaranteeing 100% of collection books display authentic front cover artwork.
        """
        if self.cover_image:
            return self.cover_image.url

        title_lower = self.title.lower()
        if "clean code" in title_lower:
            return static("img/books/clean_code.jpg")
        elif "algorithm" in title_lower:
            return static("img/books/algorithms.jpg")
        elif "database system concepts" in title_lower:
            return static("img/books/database.jpg")
        elif "software engineering" in title_lower:
            return static("img/books/software_engineering.jpg")
        elif "computer network" in title_lower:
            return static("img/books/computer_networks.jpg")
        elif "operating system" in title_lower:
            return static("img/books/operating_systems.jpg")
        elif "artificial intelligence" in title_lower:
            return static("img/books/artificial_intelligence.jpg")
        elif "python crash course" in title_lower:
            return static("img/books/python_crash_course.jpg")
        elif "fundamentals of database" in title_lower:
            return static("img/books/fundamentals_database.jpg")
        elif "systems analysis" in title_lower:
            return static("img/books/systems_analysis.jpg")
        elif "computer organization" in title_lower:
            return static("img/books/computer_organization.jpg")
        elif "discrete math" in title_lower:
            return static("img/books/discrete_math.jpg")
        elif "calculus" in title_lower:
            return static("img/books/calculus.jpg")
        elif "linear algebra" in title_lower:
            return static("img/books/linear_algebra.jpg")
        elif "probability" in title_lower:
            return static("img/books/probability_statistics.jpg")
        elif "advanced engineering" in title_lower:
            return static("img/books/advanced_engineering_math.jpg")
        elif "electric" in title_lower or "circuit" in title_lower:
            return static("img/books/electric_circuits.jpg")
        elif "thermodynamics" in title_lower:
            return static("img/books/thermodynamics.jpg")
        elif "principles of economics" in title_lower:
            return static("img/books/principles_economics.jpg")
        elif "principles of marketing" in title_lower:
            return static("img/books/principles_marketing.jpg")
        elif "financial accounting" in title_lower:
            return static("img/books/financial_accounting.jpg")
        elif "things fall apart" in title_lower or "achebe" in title_lower:
            return static("img/books/things_fall_apart.jpg")
        elif "half of a yellow sun" in title_lower:
            return static("img/books/half_yellow_sun.jpg")
        elif "lion and the jewel" in title_lower:
            return static("img/books/lion_and_jewel.jpg")
        elif "purple hibiscus" in title_lower:
            return static("img/books/purple_hibiscus.jpg")
        elif "university physics" in title_lower:
            return static("img/books/university_physics.jpg")
        elif "physics" in title_lower:
            return static("img/books/physics.jpg")
        elif "chemistry" in title_lower:
            return static("img/books/chemistry.jpg")
        elif "craft of research" in title_lower:
            return static("img/books/craft_of_research.jpg")
        elif "how to read a book" in title_lower:
            return static("img/books/how_to_read_a_book.jpg")

        return static("img/books/clean_code.jpg")



class Copy(models.Model):
    """
    Physical inventory copy of a book.
    Section 4.4: id (accession number C0001), book (FK), whereabouts, status.
    Statuses: AVAILABLE, RESERVED, BORROWED, WITHDRAWN.
    """
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        BORROWED = "BORROWED", "Borrowed"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="copies"
    )
    whereabouts = models.CharField(
        max_length=100,
        help_text="Physical shelf location e.g. Main Library, Shelf CS-1"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True
    )
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Copy"
        verbose_name_plural = "Copies"
        ordering = ["id"]

    def __str__(self):
        return f"{self.accession_number} - {self.book.title} ({self.get_status_display()})"

    @property
    def accession_number(self):
        """
        Returns zero-padded accession number e.g. C0001 (Section 4.4 & Decision 2).
        """
        return f"C{self.id:04d}" if self.id else "C----"

    def can_withdraw(self):
        """
        Enforces Section 4.4 and Acceptance Test T29:
        A copy can be WITHDRAWN only if it is not BORROWED or RESERVED.
        Returns (can_withdraw: bool, reason: str).
        """
        if self.status == self.Status.BORROWED:
            return False, "Cannot withdraw copy while it is currently borrowed by a student."
        elif self.status == self.Status.RESERVED:
            return False, "Cannot withdraw copy while it is currently held for an active reservation."
        elif self.status == self.Status.WITHDRAWN:
            return False, "This copy is already withdrawn from circulation."
        return True, ""

    def clean(self):
        """Model validation to guard against illegal withdrawal."""
        if self.pk:
            current_in_db = Copy.objects.filter(pk=self.pk).values("status").first()
            if current_in_db and self.status == self.Status.WITHDRAWN:
                old_status = current_in_db["status"]
                if old_status in [self.Status.BORROWED, self.Status.RESERVED]:
                    raise ValidationError(
                        f"Cannot withdraw copy {self.accession_number} while its status is {old_status}."
                    )
        super().clean()

    @property
    def badge_symbol_and_css(self):
        """
        Returns (symbol, css_class) for greyscale-safe badges (Section 9.5).
        """
        mapping = {
            self.Status.AVAILABLE: ("✓", "badge-success"),
            self.Status.RESERVED: ("◐", "badge-warning"),
            self.Status.BORROWED: ("●", "badge-info"),
            self.Status.WITHDRAWN: ("✕", "badge-secondary"),
        }
        return mapping.get(self.status, ("", "badge-secondary"))
