"""
Tests for accounts app.
Implements Phase 1 Acceptance Tests from Specification Section 12:
- T01: Student registers with valid details
- T02: Registration with duplicate email or matric number
- T03: Login with correct and incorrect credentials / deactivated account
- T04: Student opens a librarian URL (403)
- T05: Anonymous user opens a student URL (redirect to login)
- T27: Administrator cannot deactivate the last administrator
"""

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User



class AccountsPhase1Tests(TestCase):
    """
    Test suite verifying authentication, registration, role-based access,
    and administrator safeguards for Phase 1.
    """
    def setUp(self):
        self.client = Client()
        self.student_password = "Student@2026"
        self.librarian_password = "Librarian@2026"
        self.admin_password = "Admin@2026"

        # Create baseline active users
        self.student = User.objects.create_user(
            email="amina.bello@demo.edu.ng",
            full_name="Amina Bello",
            matric_number="2022/CSC/001",
            password=self.student_password,
            role=User.Role.STUDENT,
            is_active=True
        )

        self.librarian = User.objects.create_user(
            email="emmanuel.udoh@demo.edu.ng",
            full_name="Emmanuel Udoh",
            password=self.librarian_password,
            role=User.Role.LIBRARIAN,
            is_active=True
        )

        self.admin = User.objects.create_superuser(
            email="admin@demo.edu.ng",
            full_name="Adaeze Okonkwo",
            password=self.admin_password
        )

    def test_T01_student_registers_with_valid_details(self):
        """
        T01: Student registers with valid details.
        Expected: Account created with role STUDENT, logged in, redirected to dashboard.
        """
        response = self.client.post(reverse('register'), {
            'full_name': 'Chinedu Okafor',
            'matric_number': '2022/CSC/002',
            'email': 'chinedu.okafor@demo.edu.ng',
            'password': 'Password@123',
            'confirm_password': 'Password@123',
        }, follow=True)

        self.assertRedirects(response, reverse('student_dashboard'))
        self.assertTrue(User.objects.filter(email='chinedu.okafor@demo.edu.ng').exists())
        
        user = User.objects.get(email='chinedu.okafor@demo.edu.ng')
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertEqual(user.matric_number, '2022/CSC/002')
        self.assertTrue(user.is_active)
        # Verify student is logged in
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_T02_registration_duplicate_email_or_matric(self):
        """
        T02: Registration with duplicate email or matric number.
        Expected: Rejected with validation error message; no duplicate created.
        """
        # Attempt 1: Duplicate email
        resp_dup_email = self.client.post(reverse('register'), {
            'full_name': 'Another Amina',
            'matric_number': '2022/CSC/099',
            'email': 'amina.bello@demo.edu.ng',  # Duplicate email
            'password': 'Password@123',
            'confirm_password': 'Password@123',
        })
        self.assertEqual(resp_dup_email.status_code, 200)
        self.assertFormError(resp_dup_email.context['form'], 'email', 'An account with this email address is already registered.')

        # Attempt 2: Duplicate matric number
        resp_dup_matric = self.client.post(reverse('register'), {
            'full_name': 'Different Student',
            'matric_number': '2022/CSC/001',  # Duplicate matric
            'email': 'different.student@demo.edu.ng',
            'password': 'Password@123',
            'confirm_password': 'Password@123',
        })
        self.assertEqual(resp_dup_matric.status_code, 200)
        self.assertFormError(resp_dup_matric.context['form'], 'matric_number', 'A student with this matriculation number is already registered.')

    def test_T03_login_correct_incorrect_and_deactivated(self):
        """
        T03: Login with correct and incorrect credentials, and deactivated account.
        Expected: Success redirects to role landing; incorrect shows error; deactivated refused.
        """
        # Case A: Correct Student login with email
        resp_login_student = self.client.post(reverse('login'), {
            'identifier': 'amina.bello@demo.edu.ng',
            'password': self.student_password,
        }, follow=True)
        self.assertRedirects(resp_login_student, reverse('student_dashboard'))
        self.client.logout()

        # Case B: Correct Student login with matric number
        resp_login_matric = self.client.post(reverse('login'), {
            'identifier': '2022/CSC/001',
            'password': self.student_password,
        }, follow=True)
        self.assertRedirects(resp_login_matric, reverse('student_dashboard'))
        self.client.logout()

        # Case C: Correct Librarian login
        resp_login_lib = self.client.post(reverse('login'), {
            'identifier': 'emmanuel.udoh@demo.edu.ng',
            'password': self.librarian_password,
        }, follow=True)
        self.assertRedirects(resp_login_lib, reverse('staff_dashboard'))
        self.client.logout()

        # Case D: Incorrect password
        resp_wrong_pw = self.client.post(reverse('login'), {
            'identifier': 'amina.bello@demo.edu.ng',
            'password': 'WrongPassword123',
        })
        self.assertEqual(resp_wrong_pw.status_code, 200)
        self.assertContains(resp_wrong_pw, "Invalid email/matric number or password")

        # Case E: Deactivated account refused
        deactivated_user = User.objects.create_user(
            email="peter.ogar@demo.edu.ng",
            full_name="Peter Ogar",
            matric_number="2020/CSC/045",
            password="Password@123",
            role=User.Role.STUDENT,
            is_active=False  # Deactivated
        )
        resp_deactivated = self.client.post(reverse('login'), {
            'identifier': 'peter.ogar@demo.edu.ng',
            'password': 'Password@123',
        })
        self.assertEqual(resp_deactivated.status_code, 200)
        self.assertContains(resp_deactivated, "Your account is deactivated. Please contact the library.")

    def test_T04_student_cannot_access_librarian_url(self):
        """
        T04: Student opens a librarian URL.
        Expected: HTTP 403 Forbidden.
        """
        self.client.login(username=self.student.email, password=self.student_password)
        response = self.client.get(reverse('staff_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_T05_anonymous_user_redirected_to_login(self):
        """
        T05: Anonymous user opens a student or staff URL.
        Expected: Redirected to login page.
        """
        student_url = reverse('student_dashboard')
        response = self.client.get(student_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

        staff_url = reverse('staff_dashboard')
        response_staff = self.client.get(staff_url)
        self.assertEqual(response_staff.status_code, 302)
        self.assertTrue(response_staff.url.startswith(reverse('login')))

    def test_T27_administrator_cannot_deactivate_last_administrator(self):
        """
        T27: Administrator cannot deactivate the last remaining administrator.
        Expected: Action refused with error message; admin remains active.
        """
        # Ensure only 1 active administrator exists
        User.objects.filter(role=User.Role.ADMINISTRATOR).exclude(pk=self.admin.pk).delete()
        self.assertEqual(User.objects.filter(role=User.Role.ADMINISTRATOR, is_active=True).count(), 1)

        # Log in as the administrator
        self.client.login(username=self.admin.email, password=self.admin_password)

        # Attempt to deactivate via toggle status
        resp_toggle = self.client.post(reverse('admin_user_toggle_status', kwargs={'pk': self.admin.pk}), follow=True)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active, "The last administrator must remain active.")

        # Attempt to deactivate via user edit form
        resp_edit = self.client.post(reverse('admin_user_edit', kwargs={'pk': self.admin.pk}), {
            'full_name': self.admin.full_name,
            'email': self.admin.email,
            'role': User.Role.ADMINISTRATOR,
            'is_active': False,  # Attempting to deactivate
        })
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active, "The last administrator must not be deactivated via edit form.")
