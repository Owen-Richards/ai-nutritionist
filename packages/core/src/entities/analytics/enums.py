"""Analytics enums module.

Core enumerations for analytics domain.
"""

from enum import Enum


class EventType(str, Enum):
    """Core event taxonomy from GO_TO_PRODUCTION.md F1."""
    
    # Meal planning events
    PLAN_GENERATED = "plan_generated"
    MEAL_LOGGED = "meal_logged"
    
    # Engagement events
    NUDGE_SENT = "nudge_sent"
    NUDGE_CLICKED = "nudge_clicked"
    
    # Community events
    CREW_JOINED = "crew_joined"
    REFLECTION_SUBMITTED = "reflection_submitted"
    
    # Monetization events
    PAYWALL_VIEWED = "paywall_viewed"
    SUBSCRIBE_STARTED = "subscribe_started"
    SUBSCRIBE_ACTIVATED = "subscribe_activated"
    CHURNED = "churned"
    
    # Additional core events
    USER_REGISTERED = "user_registered"
    ONBOARDING_COMPLETED = "onboarding_completed"
    WIDGET_VIEWED = "widget_viewed"
    CALENDAR_SYNCED = "calendar_synced"
    GROCERY_EXPORTED = "grocery_exported"
    STRATEGY_REPORT_SCHEDULED = "strategy_report_scheduled"
    RECOVERY_PLAN_CREATED = "recovery_plan_created"
    PROGRESS_SUMMARY_PUBLISHED = "progress_summary_published"
    MESSAGE_INGESTED = "message_ingested"
    WEARABLE_SYNCED = "wearable_synced"
    INVENTORY_STATE_RECORDED = "inventory_state_recorded"


class ConsentType(str, Enum):
    """User consent types for data processing."""
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    PERSONALIZATION = "personalization"
    RESEARCH = "research"


class PIILevel(str, Enum):
    """PII classification levels."""
    NONE = "none"           # No PII
    PSEUDONYMIZED = "pseudo" # Hashed/anonymized identifiers
    SENSITIVE = "sensitive"  # Direct PII that requires consent
