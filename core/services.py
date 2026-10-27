"""
Core services for UniLibrary Management System.
All system policies are read directly as constants from settings.py.
SystemLog and Setting database models have been removed per project simplification.
"""

from decimal import Decimal
from django.conf import settings


# ==============================================================================
# System Logging (Safe no-op since SystemLog table was removed)
# ==============================================================================

def log_action(user, action, detail):
    """
    Kept as a safe no-op so that existing calls across services do not fail.
    The SystemLog model has been removed to keep the database at 8 core tables.
    """
    return None


# ==============================================================================
# Policy Constants Retrieval Helpers (Read from settings.py)
# ==============================================================================

def get_setting(key):
    """
    Retrieves a policy constant from settings.py by key name (case-insensitive).
    """
    attr_name = key.upper()
    return str(getattr(settings, attr_name, '0'))


def get_int(key):
    """
    Retrieves a policy constant as an integer from settings.py.
    """
    attr_name = key.upper()
    val = getattr(settings, attr_name, 0)
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def get_decimal(key):
    """
    Retrieves a policy constant as a Decimal from settings.py (e.g. FINE_PER_DAY).
    """
    attr_name = key.upper()
    val = getattr(settings, attr_name, Decimal('0.00'))
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal('0.00')


def seed_default_settings():
    """
    No-op fallback for backwards compatibility with setup scripts.
    """
    return 0, 0

