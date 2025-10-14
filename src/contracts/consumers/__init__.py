"""
Consumer contracts package.
"""

from .mobile_app_consumer import MobileAppConsumer
from .analytics_consumer import AnalyticsServiceConsumer
from .notification_consumer import NotificationServiceConsumer

__all__ = [
    "MobileAppConsumer",
    "AnalyticsServiceConsumer",
    "NotificationServiceConsumer"
]
