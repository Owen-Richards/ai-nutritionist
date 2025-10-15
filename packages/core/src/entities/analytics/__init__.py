"""Analytics domain entities.

Core analytics entities for event tracking, user profiling, and consent management.
"""

from .base import BaseEvent, EventContext
from .events import (
    PlanGeneratedEvent,
    MealLoggedEvent, 
    NudgeSentEvent,
    NudgeClickedEvent,
    CrewJoinedEvent,
    ReflectionSubmittedEvent,
    PaywallViewedEvent,
    SubscribeStartedEvent,
    SubscribeActivatedEvent,
    ChurnedEvent,
    StrategyReportScheduledEvent,
    RecoveryPlanCreatedEvent,
    ProgressSummaryPublishedEvent,
    MessageIngestedEvent,
    WearableSyncEvent,
    InventoryStateRecordedEvent
)
from .enums import EventType, ConsentType, PIILevel
from .user import UserConsent, UserProfile, UserPII

__all__ = [
    # Base classes
    "BaseEvent",
    "EventContext",
    
    # Enums
    "EventType", 
    "ConsentType",
    "PIILevel",
    
    # User models
    "UserConsent",
    "UserProfile", 
    "UserPII",
    
    # Event models
    "PlanGeneratedEvent",
    "MealLoggedEvent",
    "NudgeSentEvent", 
    "NudgeClickedEvent",
    "CrewJoinedEvent",
    "ReflectionSubmittedEvent",
    "PaywallViewedEvent",
    "SubscribeStartedEvent",
    "SubscribeActivatedEvent", 
    "ChurnedEvent",
    "StrategyReportScheduledEvent",
    "RecoveryPlanCreatedEvent",
    "ProgressSummaryPublishedEvent",
    "MessageIngestedEvent",
    "WearableSyncEvent",
    "InventoryStateRecordedEvent",
]
