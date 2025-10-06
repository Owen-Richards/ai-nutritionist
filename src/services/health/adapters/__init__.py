"""Wearable and health platform adapters."""

from .base import WearableAdapter, SyncResult
from .apple_health import AppleHealthAdapter
from .garmin import GarminAdapter
from .strava import StravaAdapter

__all__ = [
    "WearableAdapter",
    "SyncResult",
    "AppleHealthAdapter",
    "GarminAdapter",
    "StravaAdapter",
]
