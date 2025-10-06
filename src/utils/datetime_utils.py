"""
Datetime utilities for modern Python datetime handling.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime - replaces deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """Get current UTC timestamp."""
    return utc_now().timestamp()


def utc_isoformat() -> str:
    """Get current UTC datetime as ISO format string."""
    return utc_now().isoformat()
