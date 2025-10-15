"""
Event-driven architecture components for the AI Nutritionist application.

This module provides a complete event system including:
- Base event classes with metadata
- Event bus/dispatcher for routing events
- Event handlers registration system
- Async event processing capabilities
- Event sourcing for audit trails
- Dead letter queue for failed events
"""

from .base import Event, DomainEvent, EventMetadata, EventType
from .bus import EventBus, AsyncEventBus
from .dispatcher import EventDispatcher
from .handlers import EventHandler, AsyncEventHandler
from .store import EventStore, EventStoreError, InMemoryStorageBackend
from .sourcing import EventSourcing, EventSourcedAggregate
from .dead_letter import DeadLetterQueue, FailedEvent, FailureReason
from .events import (
    UserRegistered,
    MealPlanCreated,
    NutritionGoalSet,
    MealLogged,
    PaymentProcessed,
    HealthDataSynced,
    CoachingSessionCompleted,
    WeeklyReportGenerated,
)

__all__ = [
    # Base classes
    "Event",
    "DomainEvent", 
    "EventMetadata",
    "EventType",
    
    # Core components
    "EventBus",
    "AsyncEventBus",
    "EventDispatcher",
    "EventHandler",
    "AsyncEventHandler",
    "EventStore",
    "EventStoreError",
    "InMemoryStorageBackend",
    "EventSourcing",
    "EventSourcedAggregate",
    "DeadLetterQueue",
    "FailedEvent",
    "FailureReason",
    
    # Domain events
    "UserRegistered",
    "MealPlanCreated",
    "NutritionGoalSet",
    "MealLogged",
    "PaymentProcessed",
    "HealthDataSynced",
    "CoachingSessionCompleted",
    "WeeklyReportGenerated",
]
