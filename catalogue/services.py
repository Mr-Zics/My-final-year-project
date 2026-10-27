"""
Catalogue service layer for UniLibrary.
Implements business rules for books, accession copies, and categories per Sections 4, 6, and 14.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from core.services import log_action
from .models import Category, Book, Copy


@transaction.atomic
def create_book(title, author, isbn, category, num_copies=1, location="Main Library", cover_image=None, description="", user=None):
    """
    Creates a new book record and its initial physical accession copies.
    
    Args:
        title (str): Book title
        author (str): Author(s)
        isbn (str): ISBN or identifier
        category (Category): Assigned Category
        num_copies (int): Number of initial copies to create (default 1)
        location (str): Physical shelf location
        cover_image: Optional image file
        description (str): Optional synopsis
        user: The staff user creating the record
    
    Returns:
        Book: The newly created Book instance
    """
    if num_copies < 0:
        raise ValidationError("Number of copies cannot be negative.")

    book = Book.objects.create(
        title=title.strip(),
        author=author.strip(),
        isbn=isbn.strip(),
        category=category,
        cover_image=cover_image,
        description=description.strip()
    )

    created_copies = []
    if num_copies > 0:
        clean_location = location.strip() or f"Main Library, Shelf {category.code or 'GEN'}-1"
        for _ in range(num_copies):
            copy = Copy.objects.create(
                book=book,
                whereabouts=clean_location,
                status=Copy.Status.AVAILABLE
            )
            created_copies.append(copy)

    log_action(
        user=user,
        action="BOOK_CREATED",
        detail=f"Added book '{book.title}' (ISBN: {book.isbn}) with {len(created_copies)} initial copies."
    )
    return book


@transaction.atomic
def update_book(book, title, author, isbn, category, description="", cover_image=None, user=None):
    """Updates book metadata and records the audit log."""
    book.title = title.strip()
    book.author = author.strip()
    book.isbn = isbn.strip()
    book.category = category
    book.description = description.strip()
    if cover_image:
        book.cover_image = cover_image
    book.save()

    log_action(
        user=user,
        action="BOOK_UPDATED",
        detail=f"Updated details for book '{book.title}' (ID: {book.id})."
    )
    return book


@transaction.atomic
def add_copies_to_book(book, quantity, location, user=None):
    """
    Adds physical inventory copies to an existing book.
    
    Args:
        book (Book): Target Book instance
        quantity (int): Number of copies to add (>= 1)
        location (str): Physical shelf location
        user: Staff user performing the addition
    """
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")

    clean_location = location.strip() or "Main Library"
    new_copies = []
    for _ in range(quantity):
        copy = Copy.objects.create(
            book=book,
            whereabouts=clean_location,
            status=Copy.Status.AVAILABLE
        )
        new_copies.append(copy)

    accession_range = f"{new_copies[0].accession_number} to {new_copies[-1].accession_number}" if len(new_copies) > 1 else new_copies[0].accession_number
    log_action(
        user=user,
        action="COPIES_ADDED",
        detail=f"Added {quantity} copies ({accession_range}) to '{book.title}' at '{clean_location}'."
    )
    return new_copies


@transaction.atomic
def update_copy_location(copy, new_location, user=None):
    """Updates shelf location of an accession copy."""
    clean_location = new_location.strip()
    if not clean_location:
        raise ValidationError("Shelf location cannot be blank.")

    old_location = copy.whereabouts
    copy.whereabouts = clean_location
    copy.save(update_fields=["whereabouts"])

    log_action(
        user=user,
        action="COPY_RELOCATED",
        detail=f"Relocated copy {copy.accession_number} from '{old_location}' to '{clean_location}'."
    )
    return copy


@transaction.atomic
def withdraw_copy(copy, user=None):
    """
    Withdraws a copy from active circulation (e.g. damaged or lost).
    
    Enforces Section 4.4 & Acceptance Test T29:
    A copy can be WITHDRAWN only if it is not BORROWED or RESERVED.
    """
    can_withdraw, reason = copy.can_withdraw()
    if not can_withdraw:
        raise ValidationError(reason)

    copy.status = Copy.Status.WITHDRAWN
    copy.save(update_fields=["status"])

    log_action(
        user=user,
        action="COPY_WITHDRAWN",
        detail=f"Withdrew copy {copy.accession_number} of '{copy.book.title}' from circulation."
    )
    return copy


@transaction.atomic
def create_category(category_name, code="", user=None):
    """Creates a new category with uniqueness enforcement."""
    clean_name = category_name.strip()
    if not clean_name:
        raise ValidationError("Category name cannot be blank.")

    if Category.objects.filter(category_name__iexact=clean_name).exists():
        raise ValidationError(f"A category named '{clean_name}' already exists.")

    category = Category.objects.create(
        category_name=clean_name,
        code=code.strip().upper()
    )
    log_action(
        user=user,
        action="CATEGORY_CREATED",
        detail=f"Created category '{category.category_name}' (Code: {category.code})."
    )
    return category


@transaction.atomic
def update_category(category, category_name, code="", user=None):
    """Renames or updates a category."""
    clean_name = category_name.strip()
    if not clean_name:
        raise ValidationError("Category name cannot be blank.")

    if Category.objects.filter(category_name__iexact=clean_name).exclude(pk=category.pk).exists():
        raise ValidationError(f"A category named '{clean_name}' already exists.")

    old_name = category.category_name
    category.category_name = clean_name
    if code:
        category.code = code.strip().upper()
    category.save()

    log_action(
        user=user,
        action="CATEGORY_UPDATED",
        detail=f"Renamed category from '{old_name}' to '{category.category_name}'."
    )
    return category


@transaction.atomic
def delete_category(category, user=None):
    """
    Deletes a category if no books are assigned to it.
    Enforces Section 7.3: Deleting is not allowed when books exist.
    """
    if category.books.exists():
        raise ValidationError(
            f"Cannot delete category '{category.category_name}' because it contains {category.books.count()} books. "
            "Please reassign or delete the books first."
        )

    cat_name = category.category_name
    category.delete()

    log_action(
        user=user,
        action="CATEGORY_DELETED",
        detail=f"Deleted category '{cat_name}'."
    )
    return True
