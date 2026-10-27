# Project Decisions Log

This document records architectural, technical, and implementation decisions made during the development of the University Library Management System with Automated Book Reservation and Overdue Notifications.

---

## 1. Specification Decisions (Section 15)

1. **SystemLog Table**: A dedicated `SystemLog` table is created in `core` to record administrative, circulation, fine, user, and daily-job events, supporting the administrator's "View System Logs" requirement.
2. **Accession Number**: The accession number displayed to staff (`C0001`) is derived directly from the `Copy` primary key using zero-padding (`f"C{self.id:04d}"`); no separate database column is needed.
3. **Active Loan Reservation Restriction**: A student cannot place a reservation for any book of which they currently have an active, unreturned loan.
4. **Fine Payments**: Fine payments must be paid in full; partial fine payments are not supported.
5. **Staff Access Boundaries**: Administrators have read-only access to librarian circulation and catalogue lists; only librarians can perform circulation actions (issue, receive returns, record payments, authorize waivers).
6. **Estimated Overdue Fines**: Estimated fines for active overdue loans are computed dynamically in Python for display and reports (`days_overdue * fine_per_day`); fine rows are stored in the database only when the copy is returned late.
7. **Student Registration**: Students self-register via the public registration form; their accounts become active immediately upon registration.
8. **Relative Seed Data**: All dates in the seed data are computed relative to day $T$ (the day the seed command is run), ensuring demo scenarios and overdue statuses remain valid anytime the examiner evaluates the system.

---

## 2. Technical & Setup Decisions

9. **Database Driver**: The primary MySQL driver is `mysqlclient` (2.3.0), connected to MySQL 8.0 on Windows using `utf8mb4` encoding and `utf8mb4_unicode_ci` collation. `PyMySQL` is retained in the virtual environment as a documented fallback.
10. **Environment Configuration**: Configuration is loaded from `.env` using `python-decouple`. Secrets are excluded from version control via `.gitignore`.
11. **CSS & Offline Assets**: In compliance with the offline Nigerian university requirement, no external CDNs or remote Google fonts are used. Bootstrap 5.3 CSS is vendored locally in `static/vendor/bootstrap.min.css`, and custom styles are defined in `static/css/site.css` using CSS custom properties matching Section 9.
12. **Time Zone & Currency**: Time zone is configured to `Africa/Lagos` (`WAT`), and the system currency is Nigerian Naira (`₦`), formatted using Django humanize filters.
13. **Local Book Covers & Visual Assets**: High-resolution front cover images for collection books are stored locally in `static/img/books/` and an academic vector emblem is provided in `static/img/logo.svg`. This ensures a dynamic, visually engaging user interface for examiner demonstrations while maintaining 100% offline functionality.
14. **Flexible Authentication**: The login form accepts either the user's primary email address or the student matriculation number (`USERNAME_FIELD = 'email'`), matching Screen 1 of the UI specification.

---

## 3. Phase 2 (Catalogue) Decisions

15. **Derived Book Availability**: The `Book` model contains no physical `status` column. Availability is calculated dynamically from related `Copy` records (`available_copies_count()`, `is_available()`, `availability_badge`). This ensures complete data integrity and prevents desynchronization between inventory copies and bibliographic catalog records.
16. **Accession Number Formatting**: Copy accession numbers (`C0001`, `C0002`, etc.) are computed properties on the `Copy` model formatted with zero-padding from the primary key (`f"C{self.id:04d}"`). This eliminates redundant columns while conforming to academic shelf marking practices.
17. **Copy Withdrawal Protection (T29)**: Withdrawal of physical copies is strictly guarded across all tiers (model validation `clean()`, service function `withdraw_copy()`, view confirmation checks, and UI button states). A copy cannot be withdrawn while its status is `BORROWED` or `RESERVED`.
18. **Category Deletion Guard**: In accordance with Section 7.3, subject categories cannot be deleted if any books are currently assigned to them.
19. **Hybrid Cover Presentation**: The `Book` model supports both optional `ImageField` file uploads for newly catalogued titles and static cover keyword matching fallback (`get_cover_image_url()`). Cover presentation uses CSS `object-fit: contain` with dedicated card containers to guarantee front covers, titles, and author details are 100% visible with zero cropping.

---

## 4. Phase 3 & 4 (Circulation & Reservations) Decisions

20. **Circulation Issue Workflow**: Book checkout uses a two-step verification workflow. In step 1, the accession number (`C0001`) is looked up. In step 2, the student's identifier (email or matriculation number) is verified against active borrowing quota (max 3), overdue loans, and unpaid fines (> ₦500). If the copy is marked `RESERVED`, only the student who holds the active `READY` reservation can be issued the book.
21. **Reservation Queue Mechanics**: Reservations use strict First-Come, First-Served queue ordering by creation timestamp. A student cannot reserve a book if copies are currently available on shelf or if they already hold an active loan or reservation for that title.
22. **Hold Ready Window**: When a reserved copy is returned, the oldest waiting reservation is transitioned to `READY` status, assigning that physical copy and setting a 48-hour pickup window (`expires_at = now + 48 hours`).

---

## 5. Phase 5 & 6 (Fines & Daily Automation) Decisions

23. **Fine Incurrence Policy**: Fines are formally generated upon book return if returned after the due date. Estimated fines for currently overdue unreturned books are calculated on-the-fly (`days_overdue * fine_per_day`) to show live liability without prematurely recording unpaid fine rows.
24. **Fine Waiver Auditing**: Any fine waiver requires a non-empty administrative justification (`reason`), records the librarian's user ID, and logs an entry to `SystemLog`.
25. **Daily Automation Command**: `python manage.py run_daily_job` handles:
    - Canceling expired `READY` reservations past their 48-hour deadline and promoting the next queued student.
    - Sending reminder notifications 2 days prior to loan due date.
    - Sending overdue notices every 3 days up to a maximum of 3 notices per loan.
    All executions are audited in `SystemLog` with counts of actions taken.

---

## 6. Phase 7, 8, & 9 (Reports, Admin, & UI Design) Decisions

26. **Report Architecture & Exports**: Reports are structured with clean presentation, server-side parameter filtering, CSV export via streaming responses (`?export=csv`), and print-optimized styles (`?print=1`).
27. **Complete Audit Trail**: `SystemLog` records category, action name, description, actor user, IP address, and timestamp. Administrative dashboards provide filtering and chronological inspection.
28. **Modern Academic Dashboards**: Dashboards for all three roles (Student, Staff, Admin) avoid empty states, providing high-visibility KPI indicator cards, direct actionable tables (active loans, collect-soon holds, most-overdue loans), and quick-action shortcuts.
29. **Email Dispatch & Delivery Fault Tolerance**: Email delivery uses Django's `send_mail` with mode switching between `console` (default, zero network dependency) and `smtp` (production/Gmail) via `EMAIL_MODE` in `.env`. Emails are dispatched to the student's registered email on three specific life-cycle triggers: `RESERVATION_READY`, `DUE_SOON`, and `OVERDUE`. Delivery errors (e.g. SMTP timeout, bad credentials, offline) are non-fatal, logged to `SystemLog` with `EMAIL_FAILED`, while in-app notifications remain fully intact.
30. **Duplicate Reservation Prevention & Concurrency Safety**: A student cannot place multiple active reservations for the same book title. Enforced via a triple-layer guard: (1) UI-level button disabling and spinner on form submit, (2) service-layer pre-checks for active loans and active reservations (`READY` or `WAITING`), and (3) database-level conditional `UniqueConstraint` on `(student, book)` where `status IN ('WAITING', 'READY')`. Additionally, notification and email dispatch in reservation and copy allocation transactions is executed via `transaction.on_commit` to prevent holding database locks during external network I/O.
31. **Maximum Active Reservations Quota (Fair Access Policy)**: To prevent hoarding of copies and waitlist saturation, a configurable limit (`max_reservations_per_student`, default `4`) governs active reservations (`WAITING` + `READY`) per student. Enforced in `reserve_book` service, displayed in student portals with quota progress indicators (`Active (x/4)`), and blocks new reservations when the limit is reached until existing holds are collected or cancelled. Configurable dynamically by librarians in System Settings.





