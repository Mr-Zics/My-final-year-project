"""
Django management command: run_daily_check.
Alias for run_daily_job per Step 3 / Step 5 specifications.
"""

from .run_daily_job import Command as RunDailyJobCommand


class Command(RunDailyJobCommand):
    help = "Alias for run_daily_job: runs automated daily library checks."
