# University Library Management System
**Web-Based Library Management System with Automated Book Reservation and Overdue Notifications**  
*Final-Year BSc Computer Science Project &middot; Physical Academic University Library*

---

## 1. System Overview
This project replaces traditional paper-based library register books with an automated web management system designed for physical university libraries in Nigeria. Key features include:
- First-Come, First-Served **Automated Reservation Queue** with a 48-hour pickup window.
- **Automated Notifications** for due-date reminders, overdue notices, and hold availability (in-app and email).
- **Controlled Fine Management** with daily overdue calculations, borrowing blocks, offline payment recording, and authorized waivers.
- **Lightweight, Offline-First UI** with locally vendored Bootstrap 5.3 CSS, zero external CDNs or remote web fonts, and full greyscale readability for academic report figures.

---

## 2. Technology Stack
- **Backend**: Python 3.12+ / Django 5.x (Model-View-Template pattern)
- **Database**: MySQL Community Server 8.0 (InnoDB engine, `utf8mb4` encoding)
- **Database Driver**: `mysqlclient` (primary), with `PyMySQL` as documented fallback
- **Frontend**: Django Templates, HTML5, CSS3 (`site.css`), local Bootstrap 5.3 CSS
- **Configuration**: `python-decouple` reading from `.env`
- **Timezone**: `Africa/Lagos` (`WAT`)
- **Currency**: Nigerian Naira (`₦`)

---

## 3. Setup Instructions on Windows

### Step 1: Open PowerShell or Command Prompt
Navigate to the project root directory:
```powershell
cd "c:\Users\Windows\Desktop\PROJECT WORK"
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
# Or in Command Prompt (cmd.exe):
# venv\Scripts\activate.bat
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` and configure your MySQL settings:
```powershell
Copy-Item .env.example .env
```
Ensure your `.env` contains:
```ini
DEBUG=True
SECRET_KEY=django-insecure-university-library-project-key-2026
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=library_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Email Backend Configuration
EMAIL_MODE=console
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

### Step 5: Verify MySQL Database
Ensure the `MySQL80` Windows service is running, and run the database initialization script:
```powershell
python tools/init_db.py
```

### Step 6: Run Django System Checks
```powershell
python manage.py check
```

### Step 7: Start Development Server
```powershell
python manage.py runserver
```
Open your browser and navigate to:
**http://127.0.0.1:8000/**

---

## 4. Email Configuration & Live Gmail SMTP Setup

The system delivers real-time notifications to registered user email addresses for three critical library events:
1. **`RESERVATION_READY`**: Sent when a reserved book is held and ready for pickup at the circulation desk.
2. **`DUE_SOON`**: Reminder sent 2 days before a borrowed book's due date.
3. **`OVERDUE`**: Notice sent when a loan exceeds its due date and incurs daily fines.

### Step 1: Create a Gmail App Password
Google requires an **App Password** (not your regular personal password) for SMTP access:
1. Log in to your Google Account and navigate to **Security** ([https://myaccount.google.com/security](https://myaccount.google.com/security)).
2. Under "How you sign in to Google", ensure **2-Step Verification** is turned ON.
3. In the search box at the top, type **App passwords** (or go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)).
4. Enter an app name (e.g. `UniLibrary`) and click **Create**.
5. Copy the generated **16-character password** (e.g., `abcd efgh ijkl mnop`).

### Step 2: Configure Live SMTP in `.env`
Open your `.env` file and set `EMAIL_MODE=smtp` with your credentials:
```ini
EMAIL_MODE=smtp
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_character_app_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

### Step 3: Switch Back to Console Mode (Offline / Local Dev)
To run completely offline without an internet connection or credentials, change `EMAIL_MODE` in `.env`:
```ini
EMAIL_MODE=console
```
In `console` mode, all outgoing emails are rendered directly in the terminal console where the server or daily job is running.

### Safe Failure Handling
If email delivery fails due to a network outage or invalid credentials, the system **does not crash**:
- The in-app notification is permanently preserved in the student's notification center.
- The failure details are recorded in the `SystemLog` table (`action = 'EMAIL_FAILED'`) for administrator review under **Admin Portal &rarr; System Audit Logs**.


---

## 5. Helper Tools
- **Convert Screenshots to Greyscale**:
  ```powershell
  python tools/to_grayscale.py "path\to\screenshots"
  ```
  Converts all screenshots into black and white for report figures per Section 9.6.

- **Run Daily Automation Job**:
  ```bat
  tools\run_daily_job.bat
  ```

---

## 6. Project Phases & Deliverables Status (Phases 0 — 10 Complete)

| Phase | Module / Focus | Status | Key Features Delivered |
|---|---|:---:|---|
| **Phase 0** | Project Setup & Design System | ✅ Completed | MySQL 8.0 `utf8mb4`, `.env`, offline Bootstrap 5.3, Academic Navy/Gold CSS |
| **Phase 1** | Accounts & Authentication | ✅ Completed | Custom User model, Role RBAC (Student, Librarian, Admin), Matriculation login, Student Registration with password visibility toggle |
| **Phase 2** | Book Catalogue & Inventory | ✅ Completed | 30 Books across 8 Categories, 68 Copies, Accession Numbers (`C0001`), Search/Filter, Stock badges, Book details, Add/Edit/Withdraw copies |
| **Phase 3** | Circulation & Loans | ✅ Completed | 2-step Staff Issue (`C0001` + Student Matric), Return processing, Loan Renewal rules (T14, T15, T17), Loan limits, Overdue calculation |
| **Phase 4** | Book Reservations | ✅ Completed | First-Come-First-Served Queue, 48-hour pickup window, Hold ready state, 1-click issue, Student self-service reservation |
| **Phase 5** | Overdue Fines Management | ✅ Completed | Daily fine calculation (₦100/day default), ₦500 block threshold, Full payment recording, Staff authorized waivers with reason logging |
| **Phase 6** | Notifications & Daily Automation | ✅ Completed | In-app notification center, unread counters, `run_daily_job` management command (reminders, overdue notices, 48h hold expiry), Windows `.bat` scheduler |
| **Phase 7** | Reports & Analytics | ✅ Completed | 5 Official academic reports (Overdue, Fines, Circulation Activity, Reservations, Payment Log), CSV export, clean Print preview |
| **Phase 8** | System Administration | ✅ Completed | System settings editor, Audit trail logs with actor/action/IP, Manual daily job trigger, Database backup export & restore |
| **Phase 9** | Dashboards & Navigation | ✅ Completed | Redesigned modern academic dashboards for Student, Staff/Librarian, and Administrator with live metric KPI cards, action shortcut tables, and role-based sidebars |
| **Phase 10** | Demo Seeding & Verification | ✅ Completed | Complete realistic demo scenarios (A1-G1 active loans, H1-H4 fines, R1a-R7 reservations, audit logs, notifications), 41 automated tests passing |

---

## 7. Demo Accounts & Evaluation Credentials

All demo accounts use password: `Student@2026`, `Librarian@2026`, or `Admin@2026`.

| Role | Name | Email | Student ID / Matric | Password | Notes / Scenarios |
|---|---|---|---|---|---|
| **Administrator** | Adaeze Okonkwo | `admin@uni.edu.ng` | N/A | `Admin@2026` | Full system settings, audit logs, backup/restore, job trigger |
| **Librarian** | Emmanuel Udoh | `emmanuel.udoh@uni.edu.ng` | N/A | `Librarian@2026` | Circulation desk, issue, return, queue management, fines |
| **Librarian** | Funke Adeyemi | `funke.adeyemi@uni.edu.ng` | N/A | `Librarian@2026` | Cataloguing, copy withdrawal, payment receipt, waivers |
| **Student** | Amina Bello | `amina.bello@uni.edu.ng` | `2022/100001` | `Student@2026` | Loan due in 3 days; can renew (T14) |
| **Student** | Chinedu Okafor | `chinedu.okafor@uni.edu.ng` | `2022/100002` | `Student@2026` | Overdue by 4 days; estimated fine ₦200; blocked from renew |
| **Student** | Blessing Etim | `blessing.etim@uni.edu.ng` | `2022/100003` | `Student@2026` | Overdue by 12 days; estimated fine ₦600; blocked (> ₦500 limit) |
| **Student** | Ibrahim Musa | `ibrahim.musa@uni.edu.ng` | `2022/100004` | `Student@2026` | At max quota (3 books borrowed: Clean Code, Algo, Intro DB) |
| **Student** | Ngozi Nwosu | `ngozi.nwosu@uni.edu.ng` | `2023/100005` | `Student@2026` | Active loan renewed once; renewal limit reached (T15) |
| **Student** | Tunde Bakare | `tunde.bakare@uni.edu.ng` | `2023/100006` | `Student@2026` | Unpaid fine ₦600 from late return; blocked from borrowing |
| **Student** | Esther Akpan | `esther.akpan@uni.edu.ng` | `2023/100007` | `Student@2026` | Reservation READY for pickup (copy reserved, expires in 30h) |
| **Student** | Samuel Ibe | `samuel.ibe@uni.edu.ng` | `2021/100008` | `Student@2026` | Reservation WAITING in position 1 for Artificial Intelligence |
| **Student** | Fatima Yusuf | `fatima.yusuf@uni.edu.ng` | `2021/100009` | `Student@2026` | Reservation WAITING in position 2 for Artificial Intelligence |
| **Student** | Daniel Effiong | `daniel.effiong@uni.edu.ng` | `2024/100010` | `Student@2026` | Clean account; 0 loans; ready to borrow or reserve |
| **Student** | Grace Obi | `grace.obi@uni.edu.ng` | `2024/100011` | `Student@2026` | Paid fine ₦300 history; clean account |
| **Student** | Victor Eke | `victor.eke@uni.edu.ng` | `2024/100012` | `Student@2026` | Waived fine ₦450 history; clean account |
| **Student (Inactive)** | Peter Ogar | `peter.ogar@uni.edu.ng` | `2020/100013` | `Student@2026` | Account deactivated (`is_active=False`); login blocked (T03) |

---

## 8. Running Automated Tests

The comprehensive automated test suite covers all 30 formal specification test cases (T01 through T30) across 41 test methods:

```powershell
# Run the entire test suite:
.\venv\Scripts\python.exe manage.py test

# Or run by specific module:
.\venv\Scripts\python.exe manage.py test accounts.tests
.\venv\Scripts\python.exe manage.py test catalogue.tests
.\venv\Scripts\python.exe manage.py test circulation.tests
.\venv\Scripts\python.exe manage.py test reservations.tests
.\venv\Scripts\python.exe manage.py test fines.tests
.\venv\Scripts\python.exe manage.py test core.tests
```

---

## 9. Database Reset & Seeding

To return the database to the pristine Phase 10 demo state at any time:

```powershell
.\venv\Scripts\python.exe manage.py seed_demo_data --reset
```

---

## 10. Key System URLs

- **Home Page**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Book Catalogue**: [http://127.0.0.1:8000/catalogue/](http://127.0.0.1:8000/catalogue/)
- **Student Dashboard**: [http://127.0.0.1:8000/student/](http://127.0.0.1:8000/student/)
- **Staff / Circulation Desk Hub**: [http://127.0.0.1:8000/staff/](http://127.0.0.1:8000/staff/)
- **Admin Control Center**: [http://127.0.0.1:8000/manage/](http://127.0.0.1:8000/manage/)
- **Official Reports Hub**: [http://127.0.0.1:8000/staff/reports/](http://127.0.0.1:8000/staff/reports/)
- **System Audit Logs**: [http://127.0.0.1:8000/manage/logs/](http://127.0.0.1:8000/manage/logs/)
- **System Settings**: [http://127.0.0.1:8000/manage/settings/](http://127.0.0.1:8000/manage/settings/)
- **Database Backup & Restore**: [http://127.0.0.1:8000/manage/backup/](http://127.0.0.1:8000/manage/backup/)
- **Django Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)


