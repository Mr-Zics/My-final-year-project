"""
Forms for UniLibrary Catalogue module.
Supports public search, librarian book editing, copy inventory, and category management.
"""

from django import forms
from .models import Category, Book, Copy


class CatalogueSearchForm(forms.Form):
    """Filter form for public catalogue browsing (Section 7.1)."""
    AVAILABILITY_CHOICES = [
        ("all", "All Books"),
        ("available", "Available Now"),
        ("on_loan", "All Copies on Loan"),
    ]

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Search title, author, or ISBN...",
            "aria-label": "Search catalogue"
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={"class": "form-select", "aria-label": "Filter by category"})
    )
    availability = forms.ChoiceField(
        choices=AVAILABILITY_CHOICES,
        required=False,
        initial="all",
        widget=forms.Select(attrs={"class": "form-select", "aria-label": "Filter by availability"})
    )


class BookAddForm(forms.ModelForm):
    """
    Form used by librarians to register a new book in the catalogue.
    Includes initial copies and shelf location fields per Section 7.3.
    """
    num_copies = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Initial Copies",
        help_text="Number of accession copies to create immediately",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1})
    )
    location = forms.CharField(
        max_length=100,
        required=False,
        label="Physical Shelf Location",
        help_text="e.g. Main Library, Shelf CS-1",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Main Library, Shelf CS-1"})
    )

    class Meta:
        model = Book
        fields = ["title", "author", "isbn", "category", "description", "cover_image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Introduction to Algorithms"}),
            "author": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Thomas H. Cormen et al."}),
            "isbn": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 9780262033848"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Brief description..."}),
            "cover_image": forms.FileInput(attrs={"class": "form-control"}),
        }


class BookEditForm(forms.ModelForm):
    """Form to edit book metadata without touching copies."""
    class Meta:
        model = Book
        fields = ["title", "author", "isbn", "category", "description", "cover_image"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "author": forms.TextInput(attrs={"class": "form-control"}),
            "isbn": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "cover_image": forms.FileInput(attrs={"class": "form-control"}),
        }


class AddCopiesForm(forms.Form):
    """Form for adding extra physical accession copies to an existing book (Section 7.3)."""
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Quantity",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1})
    )
    location = forms.CharField(
        max_length=100,
        required=True,
        label="Shelf Location",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Main Library, Shelf CS-2"})
    )


class EditCopyLocationForm(forms.ModelForm):
    """Quick edit form for relocating a single physical accession copy."""
    class Meta:
        model = Copy
        fields = ["whereabouts"]
        widgets = {
            "whereabouts": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Main Library, Shelf CS-1"})
        }


class CategoryForm(forms.ModelForm):
    """Form to add or rename a subject category (Section 7.3)."""
    class Meta:
        model = Category
        fields = ["category_name", "code"]
        widgets = {
            "category_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Computer Science"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CS"}),
        }
