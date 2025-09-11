"""
Messaging Domain Package

This package contains all messaging and communication services:
- sms.py: Unified messaging service (ConsolidatedMessagingService)
- notifications.py: AWS messaging integration (AWSMessagingService)
- templates.py: Nutrition messaging patterns (NutritionMessagingService)
- analytics.py: Multi-user messaging analytics (MultiUserMessagingHandler)
"""

from .sms import ConsolidatedMessagingService as SMSCommunicationService
from .notifications import AWSMessagingService as NotificationService
from .templates import NutritionMessagingService as TemplateService
from .analytics import MultiUserMessagingHandler as AnalyticsService

__all__ = [
    'SMSCommunicationService',
    'NotificationService',
    'TemplateService', 
    'AnalyticsService'
]
