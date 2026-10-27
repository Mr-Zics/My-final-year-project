"""
Authentication and User Management forms for UniLibrary.
Implements Section 3, Section 7.1, and Section 7.4.
"""

from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import User


class LoginForm(forms.Form):
    """
    Form for user login. Supports email or matric number as identifier.
    Matches Screen 1 of the UI specification.
    """
    identifier = forms.CharField(
        label="Email or Matric Number",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your email or matric number',
            'id': 'login-identifier',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password',
            'id': 'login-password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        label="Remember me",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'login-remember'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        identifier = (cleaned_data.get('identifier') or '').strip()
        password = cleaned_data.get('password')

        if identifier and password:
            # Check if identifier is matric number
            target_user = None
            if '@' not in identifier:
                target_user = User.objects.filter(matric_number__iexact=identifier).first()
            if not target_user:
                target_user = User.objects.filter(email__iexact=identifier).first()

            if target_user:
                if not target_user.check_password(password):
                    raise ValidationError("Invalid email/matric number or password.")
                if not target_user.is_active:
                    raise ValidationError("Your account is deactivated. Please contact the library.")
                self.user = target_user
            else:
                raise ValidationError("Invalid email/matric number or password.")

        return cleaned_data


class StudentRegistrationForm(forms.ModelForm):
    """
    Public student self-registration form.
    Creates active student borrower accounts immediately.
    """
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum 8 characters',
            'id': 'reg-password'
        }),
        min_length=8,
        help_text="Minimum 8 characters."
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'id': 'reg-confirm-password'
        })
    )

    class Meta:
        model = User
        fields = ['full_name', 'matric_number', 'email']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Chibuike Umeokonkwo',
                'id': 'reg-full-name'
            }),
            'matric_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2022/123456',
                'id': 'reg-matric'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'chibuike.umeokonkwo@uni.edu.ng',
                'id': 'reg-email'
            }),
        }

    def clean_matric_number(self):
        matric = (self.cleaned_data.get('matric_number') or '').strip().upper()
        if not matric:
            raise ValidationError("Matriculation number is required for student registration.")
        if User.objects.filter(matric_number__iexact=matric).exists():
            raise ValidationError("A student with this matriculation number is already registered.")
        return matric

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match. Please re-enter.")
        return cleaned_data

    def _post_clean(self):
        # Preserve submitted matric_number on instance to avoid model clean falsely flagging it as empty
        raw_matric = (self.data.get('matric_number') or '').strip().upper()
        if raw_matric:
            self.instance.matric_number = raw_matric
        super()._post_clean()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.is_active = True
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class AdminUserAddForm(forms.ModelForm):
    """
    Administrator form to create new users of any role with a temporary password.
    """
    password = forms.CharField(
        label="Temporary Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Temporary password (min 8 chars)',
            'id': 'admin-add-password'
        }),
        min_length=8
    )

    class Meta:
        model = User
        fields = ['full_name', 'email', 'matric_number', 'role', 'is_active']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'matric_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        matric = (cleaned_data.get('matric_number') or '').strip()

        if role == User.Role.STUDENT and not matric:
            self.add_error('matric_number', "Matriculation number is required for students.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class AdminUserEditForm(forms.ModelForm):
    """
    Administrator form to edit an existing user.
    Enforces rules:
    - Cannot deactivate or change the role of the last remaining administrator.
    - Cannot deactivate or demote one's own account.
    """
    class Meta:
        model = User
        fields = ['full_name', 'email', 'matric_number', 'role', 'is_active']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'matric_number': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        self.requesting_user = requesting_user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        user = self.instance
        role = cleaned_data.get('role')
        is_active = cleaned_data.get('is_active')
        matric = (cleaned_data.get('matric_number') or '').strip()

        if role == User.Role.STUDENT and not matric:
            self.add_error('matric_number', "Matriculation number is required for students.")

        # Guard: Cannot deactivate or demote the last remaining administrator
        if user.role == User.Role.ADMINISTRATOR:
            other_active_admins = User.objects.filter(
                role=User.Role.ADMINISTRATOR,
                is_active=True
            ).exclude(pk=user.pk).count()

            if other_active_admins == 0:
                if is_active is False:
                    raise ValidationError("Cannot deactivate the last remaining administrator.")
                if role != User.Role.ADMINISTRATOR:
                    raise ValidationError("Cannot change the role of the last remaining administrator.")

        # Guard: Cannot deactivate or demote oneself
        if self.requesting_user and self.requesting_user.pk == user.pk:
            if is_active is False:
                raise ValidationError("You cannot deactivate your own account.")
            if role != User.Role.ADMINISTRATOR:
                raise ValidationError("You cannot remove your own administrator role.")

        return cleaned_data
