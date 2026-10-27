"""
Management command to seed the database with demo data (Section 11).
Seeds users, categories, books, copies, settings, active loans, returned loans with fines,
history loans, reservations queue, notifications, and system audit logs.

Usage:
    python manage.py seed_demo_data           # Create demo data (skip if exists)
    python manage.py seed_demo_data --reset    # Delete and recreate all demo data
"""

import sys
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from catalogue.models import Category, Book, Copy
from circulation.models import BorrowRecord
from reservations.models import Reservation
from fines.models import Fine
from notifications.models import Notification
from core.services import log_action


class Command(BaseCommand):
    help = 'Seeds the database with full realistic demo data scenarios (Section 11).'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if sys.platform == 'win32':
            self.stdout = self.create_utf8_stream(self.stdout)
            self.stderr = self.create_utf8_stream(self.stderr)

    @staticmethod
    def create_utf8_stream(original):
        try:
            stream = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True
            )
            if hasattr(original, 'style_func'):
                stream.style_func = original.style_func
            return stream
        except Exception:
            return original

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all demo data and recreate it from scratch.',
        )

    def _write(self, msg, style=None):
        try:
            if style:
                self.stdout.write(style(msg))
            else:
                self.stdout.write(msg + '\n')
        except (UnicodeEncodeError, AttributeError):
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            try:
                if style:
                    self.stdout.write(style(safe_msg))
                else:
                    self.stdout.write(safe_msg + '\n')
            except Exception:
                print(safe_msg)

    def handle(self, *args, **options):
        self._write('\n=== UniLibrary Full Demo Data Seeder (Phase 10) ===')
        self._write('=' * 65)

        if options['reset']:
            self._write('\n[!] Resetting all demo data...')
            self._reset_data()

        # Check if data already exists
        if User.objects.filter(email='admin@uni.edu.ng').exists() and not options['reset']:
            self._write('\n[!] Demo data already exists. Use --reset to recreate.')
            self._print_login_table()
            return

        now = timezone.now()
        T = now.date()
        self._write(f'\nSeed Day (T): {T.strftime("%Y-%m-%d")}')

        # 1. System Settings are configured directly as constants in settings.py

        # 2. Users
        self._write('\n--- 2. Seeding Users ---')
        users = self._seed_users(now)
        self._write(f'   [OK] {len(users)} users created')

        # 3. Categories
        self._write('\n--- 3. Seeding Categories ---')
        categories = self._seed_categories()
        self._write(f'   [OK] {len(categories)} categories created')

        # 4. Books and Copies
        self._write('\n--- 4. Seeding Books and Copies ---')
        books, copy_count = self._seed_books_and_copies(categories)
        self._write(f'   [OK] {len(books)} books, {copy_count} copies created')

        # 5. Set Initial Withdrawn status (Book#11 copy 2)
        self._write('\n--- 5. Initial Copy Statuses ---')
        self._set_initial_statuses(books)

        # 6. Active Loans (A1 to G1)
        self._write('\n--- 6. Seeding Active Loans Scenarios (A1 - G1) ---')
        active_loans = self._seed_active_loans(users, books, T)
        self._write(f'   [OK] {len(active_loans)} active loans created')

        # 7. Returned Loans with Fines (H1 - H4)
        self._write('\n--- 7. Seeding Returned Loans with Fines (H1 - H4) ---')
        self._seed_returned_fines(users, books, T)

        # 8. On-Time Returned Loans History (12 loans)
        self._write('\n--- 8. Seeding On-Time Returned History Loans ---')
        self._seed_history_loans(users, books, T)

        # 9. Reservations Scenarios (R1a - R7)
        self._write('\n--- 9. Seeding Reservations Scenarios (R1a - R7) ---')
        r3_copy = self._seed_reservations(users, books, active_loans, now, T)

        # 10. Notifications
        self._write('\n--- 10. Seeding Realistic Notification Records ---')
        self._seed_notifications(users, books, active_loans, now, T)

        # 11. System Audit Logs table has been removed per project simplification

        self._write('\n' + '=' * 65)
        self._write('[OK] Demo data seeded successfully!\n')
        self._print_login_table()
        self._print_copy_status_check()

    def _reset_data(self):
        from django.db import connection
        models_to_reset = [
            Notification,
            Fine,
            BorrowRecord,
            Reservation,
            Copy,
            Book,
            Category,
            User,
        ]
        with connection.cursor() as cursor:
            if connection.vendor == 'mysql':
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                for model in models_to_reset:
                    cursor.execute(f"TRUNCATE TABLE `{model._meta.db_table}`;")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            elif connection.vendor == 'sqlite':
                for model in models_to_reset:
                    model.objects.all().delete()
                try:
                    table_names_str = "', '".join([m._meta.db_table for m in models_to_reset])
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name IN ('{table_names_str}');")
                except Exception:
                    pass
            else:
                for model in models_to_reset:
                    model.objects.all().delete()
        self._write('   [OK] All demo data deleted and primary key auto-increment counters reset.')

    def _seed_users(self, now):
        users_data = [
            ('Adaeze Okonkwo', 'admin@uni.edu.ng', None, 'ADMINISTRATOR', True, 400),
            ('Emmanuel Udoh', 'emmanuel.udoh@uni.edu.ng', None, 'LIBRARIAN', True, 350),
            ('Funke Adeyemi', 'funke.adeyemi@uni.edu.ng', None, 'LIBRARIAN', True, 300),
            ('Amina Bello', 'amina.bello@uni.edu.ng', '2022/100001', 'STUDENT', True, 380),
            ('Chinedu Okafor', 'chinedu.okafor@uni.edu.ng', '2022/100002', 'STUDENT', True, 370),
            ('Blessing Etim', 'blessing.etim@uni.edu.ng', '2022/100003', 'STUDENT', True, 360),
            ('Ibrahim Musa', 'ibrahim.musa@uni.edu.ng', '2022/100004', 'STUDENT', True, 340),
            ('Ngozi Nwosu', 'ngozi.nwosu@uni.edu.ng', '2023/100005', 'STUDENT', True, 200),
            ('Tunde Bakare', 'tunde.bakare@uni.edu.ng', '2023/100006', 'STUDENT', True, 190),
            ('Esther Akpan', 'esther.akpan@uni.edu.ng', '2023/100007', 'STUDENT', True, 180),
            ('Samuel Ibe', 'samuel.ibe@uni.edu.ng', '2021/100008', 'STUDENT', True, 150),
            ('Fatima Yusuf', 'fatima.yusuf@uni.edu.ng', '2021/100009', 'STUDENT', True, 130),
            ('Daniel Effiong', 'daniel.effiong@uni.edu.ng', '2024/100010', 'STUDENT', True, 90),
            ('Grace Obi', 'grace.obi@uni.edu.ng', '2024/100011', 'STUDENT', True, 80),
            ('Victor Eke', 'victor.eke@uni.edu.ng', '2024/100012', 'STUDENT', True, 70),
            ('Peter Ogar', 'peter.ogar@uni.edu.ng', '2020/100013', 'STUDENT', False, 400),
        ]

        passwords = {
            'ADMINISTRATOR': 'Admin@2026',
            'LIBRARIAN': 'Librarian@2026',
            'STUDENT': 'Student@2026',
        }

        created = {}
        for full_name, email, matric, role, is_active, days_ago in users_data:
            user = User(
                full_name=full_name,
                email=email,
                matric_number=matric,
                role=role,
                is_active=is_active,
            )
            user.set_password(passwords[role])
            user.save()

            reg_date = now - timedelta(days=days_ago)
            User.objects.filter(pk=user.pk).update(date_registered=reg_date)
            created[email] = user

        return created

    def _seed_categories(self):
        categories_data = [
            ('Computer Science', 'CS'),
            ('Mathematics', 'MA'),
            ('Engineering', 'EN'),
            ('Economics and Business', 'EB'),
            ('Literature', 'LI'),
            ('Physics', 'PH'),
            ('Chemistry', 'CH'),
            ('General Studies', 'GS'),
        ]
        created = {}
        for name, code in categories_data:
            cat = Category.objects.create(category_name=name)
            created[code] = cat
        return created

    def _seed_books_and_copies(self, categories):
        books_data = [
            ('Introduction to Algorithms', 'Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein', 'CS', 2),
            ('Database System Concepts', 'Abraham Silberschatz, Henry F. Korth, S. Sudarshan', 'CS', 3),
            ('Software Engineering', 'Ian Sommerville', 'CS', 3),
            ('Computer Networks', 'Andrew S. Tanenbaum, David J. Wetherall', 'CS', 2),
            ('Operating System Concepts', 'Abraham Silberschatz, Peter B. Galvin, Greg Gagne', 'CS', 3),
            ('Artificial Intelligence: A Modern Approach', 'Stuart Russell, Peter Norvig', 'CS', 2),
            ('Clean Code', 'Robert C. Martin', 'CS', 2),
            ('Python Crash Course', 'Eric Matthes', 'CS', 3),
            ('Fundamentals of Database Systems', 'Ramez Elmasri, Shamkant B. Navathe', 'CS', 2),
            ('Systems Analysis and Design', 'Alan Dennis, Barbara Haley Wixom, Roberta M. Roth', 'CS', 2),
            ('Computer Organization and Architecture', 'William Stallings', 'CS', 2),
            ('Discrete Mathematics and Its Applications', 'Kenneth H. Rosen', 'MA', 3),
            ('Calculus', 'James Stewart', 'MA', 3),
            ('Linear Algebra and Its Applications', 'David C. Lay', 'MA', 2),
            ('Probability and Statistics for Engineers and Scientists', 'Ronald E. Walpole et al.', 'MA', 2),
            ('Advanced Engineering Mathematics', 'K. A. Stroud', 'EN', 2),
            ('Fundamentals of Electric Circuits', 'Charles K. Alexander, Matthew N. O. Sadiku', 'EN', 2),
            ('Thermodynamics: An Engineering Approach', 'Yunus A. Cengel, Michael A. Boles', 'EN', 2),
            ('Principles of Economics', 'N. Gregory Mankiw', 'EB', 3),
            ('Principles of Marketing', 'Philip Kotler, Gary Armstrong', 'EB', 2),
            ('Financial Accounting', 'Jerry J. Weygandt et al.', 'EB', 2),
            ('Things Fall Apart', 'Chinua Achebe', 'LI', 3),
            ('Half of a Yellow Sun', 'Chimamanda Ngozi Adichie', 'LI', 2),
            ('The Lion and the Jewel', 'Wole Soyinka', 'LI', 2),
            ('Purple Hibiscus', 'Chimamanda Ngozi Adichie', 'LI', 2),
            ('University Physics', 'Hugh D. Young, Roger A. Freedman', 'PH', 2),
            ('Fundamentals of Physics', 'David Halliday, Robert Resnick, Jearl Walker', 'PH', 2),
            ('Chemistry: The Central Science', 'Theodore L. Brown et al.', 'CH', 2),
            ('The Craft of Research', 'Wayne C. Booth, Gregory G. Colomb, Joseph M. Williams', 'GS', 2),
            ('How to Read a Book', 'Mortimer J. Adler, Charles Van Doren', 'GS', 2),
        ]

        shelf_cycle = {}
        created_books = []
        total_copies = 0

        for i, (title, author, cat_code, num_copies) in enumerate(books_data, 1):
            isbn = f'978000000{i:04d}0'
            book = Book.objects.create(
                title=title,
                author=author,
                isbn=isbn,
                category=categories[cat_code],
            )
            created_books.append(book)

            for c in range(num_copies):
                shelf_num = shelf_cycle.get(cat_code, 0) % 3 + 1
                shelf_cycle[cat_code] = shelf_cycle.get(cat_code, 0) + 1
                whereabouts = f'Main Library, Shelf {cat_code}-{shelf_num}'
                Copy.objects.create(
                    book=book,
                    whereabouts=whereabouts,
                    status='AVAILABLE',
                )
                total_copies += 1

        return created_books, total_copies

    def _set_initial_statuses(self, books):
        book_11 = books[10]
        copies_11 = list(book_11.copies.order_by('id'))
        if len(copies_11) >= 2:
            copy_2 = copies_11[1]
            copy_2.status = 'WITHDRAWN'
            copy_2.save()

    def _seed_active_loans(self, users, books, T):
        emmanuel = users['emmanuel.udoh@uni.edu.ng']
        funke = users['funke.adeyemi@uni.edu.ng']

        # Get copies by book index (1-based)
        def get_copy(book_idx, copy_num):
            book = books[book_idx - 1]
            copies = list(book.copies.order_by('id'))
            return copies[copy_num - 1]

        active_loans_data = [
            ('A1', 'amina.bello@uni.edu.ng', 2, 1, T - timedelta(days=4), T + timedelta(days=3), 0, emmanuel),
            ('A2', 'amina.bello@uni.edu.ng', 8, 1, T - timedelta(days=5), T + timedelta(days=2), 0, funke),
            ('A3', 'amina.bello@uni.edu.ng', 22, 1, T - timedelta(days=2), T + timedelta(days=5), 0, emmanuel),
            ('B1', 'chinedu.okafor@uni.edu.ng', 1, 1, T - timedelta(days=11), T - timedelta(days=4), 0, funke),
            ('B2', 'chinedu.okafor@uni.edu.ng', 5, 1, T - timedelta(days=3), T + timedelta(days=4), 0, emmanuel),
            ('C1', 'blessing.etim@uni.edu.ng', 1, 2, T - timedelta(days=13), T - timedelta(days=6), 0, funke),
            ('D1', 'ibrahim.musa@uni.edu.ng', 3, 1, T - timedelta(days=9), T + timedelta(days=5), 1, emmanuel),
            ('E1', 'esther.akpan@uni.edu.ng', 7, 1, T - timedelta(days=3), T + timedelta(days=4), 0, funke),
            ('F1', 'daniel.effiong@uni.edu.ng', 4, 1, T - timedelta(days=1), T + timedelta(days=6), 0, emmanuel),
            ('F2', 'grace.obi@uni.edu.ng', 4, 2, T - timedelta(days=2), T + timedelta(days=5), 0, funke),
            ('G1', 'samuel.ibe@uni.edu.ng', 19, 1, T - timedelta(days=23), T - timedelta(days=16), 0, emmanuel),
        ]

        created_loans = {}
        for code, student_email, book_idx, copy_num, b_date, d_date, renewals, staff in active_loans_data:
            copy = get_copy(book_idx, copy_num)
            copy.status = 'BORROWED'
            copy.save()

            loan = BorrowRecord.objects.create(
                student=users[student_email],
                copy=copy,
                issued_by=staff,
                borrow_date=b_date,
                due_date=d_date,
            )
            created_loans[code] = loan

        return created_loans

    def _seed_returned_fines(self, users, books, T):
        emmanuel = users['emmanuel.udoh@uni.edu.ng']
        funke = users['funke.adeyemi@uni.edu.ng']

        def get_copy(book_idx, copy_num):
            book = books[book_idx - 1]
            return list(book.copies.order_by('id'))[copy_num - 1]

        # H1: Chinedu Book#8 copy 2, unpaid 400 (4 days late * 100)
        c_h1 = get_copy(8, 2)
        l_h1 = BorrowRecord.objects.create(
            student=users['chinedu.okafor@uni.edu.ng'],
            copy=c_h1,
            issued_by=emmanuel,
            borrow_date=T - timedelta(days=45),
            due_date=T - timedelta(days=38),
            return_date=T - timedelta(days=34),
        )
        Fine.objects.create(
            borrow_record=l_h1,
            amount=Decimal('400.00'),
            status=Fine.Status.UNPAID,
            date_created=T - timedelta(days=34),
        )

        # H2: Fatima Book#13 copy 1, unpaid 600 (BLOCKED, 6 days late * 100)
        c_h2 = get_copy(13, 1)
        l_h2 = BorrowRecord.objects.create(
            student=users['fatima.yusuf@uni.edu.ng'],
            copy=c_h2,
            issued_by=funke,
            borrow_date=T - timedelta(days=50),
            due_date=T - timedelta(days=43),
            return_date=T - timedelta(days=37),
        )
        Fine.objects.create(
            borrow_record=l_h2,
            amount=Decimal('600.00'),
            status=Fine.Status.UNPAID,
            date_created=T - timedelta(days=37),
        )

        # H3: Tunde Book#12 copy 1, paid 300 (3 days late * 100)
        c_h3 = get_copy(12, 1)
        l_h3 = BorrowRecord.objects.create(
            student=users['tunde.bakare@uni.edu.ng'],
            copy=c_h3,
            issued_by=emmanuel,
            borrow_date=T - timedelta(days=44),
            due_date=T - timedelta(days=37),
            return_date=T - timedelta(days=34),
        )
        Fine.objects.create(
            borrow_record=l_h3,
            amount=Decimal('300.00'),
            status=Fine.Status.PAID,
            date_created=T - timedelta(days=34),
            date_paid=T - timedelta(days=33),
            recorded_by=emmanuel,
            payment_reference='RCPT-0001',
        )

        # H4: Ngozi Book#23 copy 1, waived 400 (4 days late * 100)
        c_h4 = get_copy(23, 1)
        l_h4 = BorrowRecord.objects.create(
            student=users['ngozi.nwosu@uni.edu.ng'],
            copy=c_h4,
            issued_by=funke,
            borrow_date=T - timedelta(days=36),
            due_date=T - timedelta(days=29),
            return_date=T - timedelta(days=25),
        )
        Fine.objects.create(
            borrow_record=l_h4,
            amount=Decimal('400.00'),
            status=Fine.Status.PAID,
            date_created=T - timedelta(days=25),
            date_paid=T - timedelta(days=24),
            recorded_by=funke,
            payment_reference='RCPT-0002',
        )

    def _seed_history_loans(self, users, books, T):
        emmanuel = users['emmanuel.udoh@uni.edu.ng']
        funke = users['funke.adeyemi@uni.edu.ng']

        def get_copy(book_idx, copy_num):
            book = books[book_idx - 1]
            return list(book.copies.order_by('id'))[copy_num - 1]

        on_time_loans = [
            ('amina.bello@uni.edu.ng', 7, 2, 80),
            ('esther.akpan@uni.edu.ng', 2, 2, 75),
            ('ibrahim.musa@uni.edu.ng', 9, 1, 70),
            ('grace.obi@uni.edu.ng', 12, 2, 65),
            ('victor.eke@uni.edu.ng', 15, 1, 60),
            ('daniel.effiong@uni.edu.ng', 6, 1, 55),
            ('blessing.etim@uni.edu.ng', 19, 2, 50),
            ('samuel.ibe@uni.edu.ng', 22, 2, 45),
            ('tunde.bakare@uni.edu.ng', 30, 1, 40),
            ('fatima.yusuf@uni.edu.ng', 25, 1, 38),
            ('ngozi.nwosu@uni.edu.ng', 10, 1, 35),
            ('victor.eke@uni.edu.ng', 29, 1, 32),
        ]

        for i, (student_email, book_idx, copy_num, days_ago) in enumerate(on_time_loans):
            copy = get_copy(book_idx, copy_num)
            b_date = T - timedelta(days=days_ago)
            d_date = b_date + timedelta(days=7)
            r_date = b_date + timedelta(days=5)  # returned 2 days before due date
            staff = emmanuel if i % 2 == 0 else funke

            BorrowRecord.objects.create(
                student=users[student_email],
                copy=copy,
                issued_by=staff,
                borrow_date=b_date,
                due_date=d_date,
                return_date=r_date,
            )

    def _seed_reservations(self, users, books, active_loans, now, T):
        def get_copy(book_idx, copy_num):
            book = books[book_idx - 1]
            return list(book.copies.order_by('id'))[copy_num - 1]

        # R1a: Samuel Ibe Book#1 WAITING reserved T-8
        r1a = Reservation.objects.create(
            student=users['samuel.ibe@uni.edu.ng'],
            book=books[0],
            status=Reservation.Status.WAITING,
        )
        Reservation.objects.filter(pk=r1a.pk).update(reservation_date=now - timedelta(days=8))

        # R1b: Victor Eke Book#1 WAITING reserved T-5
        r1b = Reservation.objects.create(
            student=users['victor.eke@uni.edu.ng'],
            book=books[0],
            status=Reservation.Status.WAITING,
        )
        Reservation.objects.filter(pk=r1b.pk).update(reservation_date=now - timedelta(days=5))

        # R1c: Grace Obi Book#1 WAITING reserved T-2
        r1c = Reservation.objects.create(
            student=users['grace.obi@uni.edu.ng'],
            book=books[0],
            status=Reservation.Status.WAITING,
        )
        Reservation.objects.filter(pk=r1c.pk).update(reservation_date=now - timedelta(days=2))

        # R2: Victor Eke Book#4 WAITING reserved T-1
        r2 = Reservation.objects.create(
            student=users['victor.eke@uni.edu.ng'],
            book=books[3],
            status=Reservation.Status.WAITING,
        )
        Reservation.objects.filter(pk=r2.pk).update(reservation_date=now - timedelta(days=1))

        # R3: Esther Akpan Book#6 READY, copy = Book#6 copy 1, expires_at = now + 30h
        c_r3 = get_copy(6, 1)
        c_r3.status = 'RESERVED'
        c_r3.save()
        r3 = Reservation.objects.create(
            student=users['esther.akpan@uni.edu.ng'],
            book=books[5],
            copy=c_r3,
            status=Reservation.Status.READY,
            notified_at=now - timedelta(days=1),
            expires_at=now + timedelta(hours=30),
        )
        Reservation.objects.filter(pk=r3.pk).update(reservation_date=now - timedelta(days=1))

        # R4: Daniel Effiong Book#14 READY, copy = Book#14 copy 1, expires_at = now + 3h
        c_r4 = get_copy(14, 1)
        c_r4.status = 'RESERVED'
        c_r4.save()
        r4 = Reservation.objects.create(
            student=users['daniel.effiong@uni.edu.ng'],
            book=books[13],
            copy=c_r4,
            status=Reservation.Status.READY,
            notified_at=now - timedelta(hours=5),
            expires_at=now + timedelta(hours=3),
        )
        Reservation.objects.filter(pk=r4.pk).update(reservation_date=now - timedelta(days=1))

        # R5: Amina Bello Book#22 FULFILLED (links to loan A3)
        c_r5 = get_copy(22, 1)
        r5 = Reservation.objects.create(
            student=users['amina.bello@uni.edu.ng'],
            book=books[21],
            copy=c_r5,
            status=Reservation.Status.FULFILLED,
            notified_at=now - timedelta(days=5),
            expires_at=now - timedelta(days=3),
        )
        Reservation.objects.filter(pk=r5.pk).update(reservation_date=now - timedelta(days=6))
        loan_a3 = active_loans.get('A3')
        if loan_a3:
            loan_a3.reservation = r5
            loan_a3.save()

        # R6: Tunde Bakare Book#5 CANCELLED
        r6 = Reservation.objects.create(
            student=users['tunde.bakare@uni.edu.ng'],
            book=books[4],
            status=Reservation.Status.CANCELLED,
        )
        Reservation.objects.filter(pk=r6.pk).update(reservation_date=now - timedelta(days=10))

        # R7: Blessing Etim Book#11 EXPIRED
        r7 = Reservation.objects.create(
            student=users['blessing.etim@uni.edu.ng'],
            book=books[10],
            status=Reservation.Status.EXPIRED,
            notified_at=now - timedelta(days=12),
            expires_at=now - timedelta(days=10),
        )
        Reservation.objects.filter(pk=r7.pk).update(reservation_date=now - timedelta(days=12))
        return c_r3

    def _seed_notifications(self, users, books, active_loans, now, T):
        notifs = [
            ('esther.akpan@uni.edu.ng', 'RESERVATION_READY', '"Artificial Intelligence: A Modern Approach" is ready, collect before expiry', 1, False, True),
            ('daniel.effiong@uni.edu.ng', 'RESERVATION_READY', '"Linear Algebra and Its Applications" is ready for pickup', 0, False, True),
            ('amina.bello@uni.edu.ng', 'RESERVATION_READY', 'Your hold on "Things Fall Apart" is ready for pickup at the circulation desk', 5, True, True),
            ('chinedu.okafor@uni.edu.ng', 'OVERDUE', '"Introduction to Algorithms" is 3 days overdue. Return to the desk immediately.', 3, False, True),
            ('samuel.ibe@uni.edu.ng', 'OVERDUE', '"Principles of Economics" overdue notice 1: return book immediately.', 10, True, True),
            ('samuel.ibe@uni.edu.ng', 'OVERDUE', '"Principles of Economics" overdue notice 2: overdue fines accruing.', 5, False, True),
            ('blessing.etim@uni.edu.ng', 'RESERVATION_EXPIRED', 'Your reservation for "Computer Organization and Architecture" expired uncollected.', 10, True, False),
            ('victor.eke@uni.edu.ng', 'RESERVATION_CONFIRMED', 'You are number 2 in the queue for "Introduction to Algorithms".', 5, True, False),
            ('grace.obi@uni.edu.ng', 'RESERVATION_CONFIRMED', 'You are number 3 in the queue for "Introduction to Algorithms".', 2, False, False),
            ('tunde.bakare@uni.edu.ng', 'RESERVATION_CONFIRMED', 'You joined the queue for "Operating System Concepts".', 10, True, False),
        ]

        for email, n_type, msg, days_ago, is_read, make_email in notifs:
            user = users[email]
            sent_time = now - timedelta(days=days_ago)

            Notification.objects.create(
                user=user,
                type=n_type,
                channel=Notification.Channel.INAPP,
                message=msg,
                is_read=is_read,
                date_sent=sent_time,
            )

            if make_email:
                Notification.objects.create(
                    user=user,
                    type=n_type,
                    channel=Notification.Channel.EMAIL,
                    message=msg,
                    is_read=is_read,
                    date_sent=sent_time,
                )

    def _seed_system_logs(self, users, now, T, r3_copy=None):
        pass

    def _print_login_table(self):
        self._write('\n--- Demo Login Credentials ---')
        self._write('-' * 80)
        self._write(f'{"Role":<15} {"Name":<25} {"Email":<35} {"Password"}')
        self._write('-' * 80)

        demo_accounts = [
            ('ADMINISTRATOR', 'Adaeze Okonkwo', 'admin@uni.edu.ng', 'Admin@2026'),
            ('LIBRARIAN', 'Emmanuel Udoh', 'emmanuel.udoh@uni.edu.ng', 'Librarian@2026'),
            ('LIBRARIAN', 'Funke Adeyemi', 'funke.adeyemi@uni.edu.ng', 'Librarian@2026'),
            ('STUDENT', 'Amina Bello', 'amina.bello@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Chinedu Okafor', 'chinedu.okafor@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Blessing Etim', 'blessing.etim@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Ibrahim Musa', 'ibrahim.musa@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Ngozi Nwosu', 'ngozi.nwosu@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Tunde Bakare', 'tunde.bakare@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Esther Akpan', 'esther.akpan@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Samuel Ibe', 'samuel.ibe@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Fatima Yusuf', 'fatima.yusuf@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Daniel Effiong', 'daniel.effiong@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Grace Obi', 'grace.obi@uni.edu.ng', 'Student@2026'),
            ('STUDENT', 'Victor Eke', 'victor.eke@uni.edu.ng', 'Student@2026'),
            ('STUDENT [OFF]', 'Peter Ogar', 'peter.ogar@uni.edu.ng', 'Student@2026'),
        ]

        for role, name, email, password in demo_accounts:
            self._write(f'{role:<15} {name:<25} {email:<35} {password}')

        self._write('-' * 80)

    def _print_copy_status_check(self):
        self._write('\n--- Copy Status Verification ---')
        statuses = {}
        for copy in Copy.objects.all():
            statuses[copy.status] = statuses.get(copy.status, 0) + 1

        total = sum(statuses.values())
        for status, count in sorted(statuses.items()):
            self._write(f'   {status:<12} {count}')
        self._write(f'   {"TOTAL":<12} {total}')

        # Verify against Section 11.4 copy status check:
        # BORROWED = 11, RESERVED = 2, WITHDRAWN = 1, AVAILABLE = 56
        self._write('\nExpected vs Actual Inventory Breakdown:')
        self._write(f'   BORROWED : {statuses.get("BORROWED", 0)} (Expected: 11)')
        self._write(f'   RESERVED : {statuses.get("RESERVED", 0)} (Expected: 2)')
        self._write(f'   WITHDRAWN: {statuses.get("WITHDRAWN", 0)} (Expected: 1)')
        self._write(f'   AVAILABLE: {statuses.get("AVAILABLE", 0)} (Expected: 56)')
        self._write('')
