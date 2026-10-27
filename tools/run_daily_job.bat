@echo off
REM UniLibrary Daily Automation Job Batch Script
REM Executes hold expiry, due date reminders, and overdue notices via Django management command

cd /d "%~dp0\.."
call .\venv\Scripts\activate.bat
python manage.py run_daily_job
pause
