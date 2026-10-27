"""
Custom User Model for UniLibrary Management System.
Implements Section 3 and Section 4.1 of the Build Specification.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    """
    Custom user manager for User model where email is the unique identifier
    for authentication instead of username.
    """
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set.")
        if not full_name:
            raise ValueError("The Full Name field must be set.")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMINISTRATOR)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with role-based access for Administrator, Librarian, and Student.
    Email is used as the unique login credential.
    """
    class Role(models.TextChoices):
        ADMINISTRATOR = 'ADMINISTRATOR', 'Administrator'
        LIBRARIAN = 'LIBRARIAN', 'Librarian'
        STUDENT = 'STUDENT', 'Student'

    full_name = models.CharField(max_length=100, help_text="User's official full name")
    email = models.EmailField(max_length=100, unique=True, help_text="Unique login identifier")
    matric_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Student matriculation number (required for students, null for staff/admin)"
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Role determining permissions: STUDENT, LIBRARIAN, or ADMINISTRATOR"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls if the account can log in. Deactivated accounts are barred from login."
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the Django admin site."
    )
    date_registered = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when the user account was registered"
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'Users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_registered']

    def __str__(self):
        if self.matric_number:
            return f"{self.full_name} ({self.matric_number})"
        return f"{self.full_name} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_librarian(self):
        return self.role == self.Role.LIBRARIAN

    @property
    def is_administrator(self):
        return self.role == self.Role.ADMINISTRATOR

    @property
    def initials(self):
        """Returns uppercase initials of user's name (e.g. 'Isaac Umoh' -> 'IU')."""
        if not self.full_name:
            return "U"
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.full_name[:2].upper()

    def clean(self):
        super().clean()
        if self.role == self.Role.STUDENT and not self.matric_number:
            from django.core.exceptions import ValidationError
            raise ValidationError({'matric_number': 'Matriculation number is required for students.'})
