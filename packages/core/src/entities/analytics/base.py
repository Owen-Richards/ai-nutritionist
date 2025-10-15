"""Base analytics entities.

Core analytics classes and enums.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


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


class EventContext(BaseModel):
    """Context information for events."""
    session_id: Optional[UUID] = None
    device_id: Optional[str] = None
    platform: Optional[str] = None  # ios, android, web
    app_version: Optional[str] = None
    experiment_ids: Optional[List[str]] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None  # Will be hashed for privacy
    geo_country: Optional[str] = None
    geo_region: Optional[str] = None
    local_timezone: Optional[str] = None
    season: Optional[str] = None
    weather_summary: Optional[str] = None
    
    class Config:
        extra = "allow"


class BaseEvent(BaseModel):
    """Base analytics event with privacy controls."""
    
    # Core identifiers
    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # User identification (privacy-aware)
    user_id: Optional[UUID] = None
    anonymous_id: Optional[str] = None  # For non-authenticated users
    
    # Privacy and consent
    pii_level: PIILevel = PIILevel.NONE
    consent_flags: Dict[ConsentType, bool] = Field(default_factory=dict)
    
    # Event context
    context: Optional[EventContext] = None
    
    # Event properties (specific to each event type)
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('timestamp')
    @classmethod
    def timestamp_must_be_utc(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    
    def to_warehouse_format(self) -> Dict[str, Any]:
        """Convert to warehouse-friendly format with PII separation."""
        base_data = {
            "event_id": str(self.event_id),
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": str(self.user_id) if self.user_id else None,
            "anonymous_id": self.anonymous_id,
            "pii_level": self.pii_level.value,
            "consent_flags": self.consent_flags,
            "properties": self.properties
        }
        
        # Add context if present (excluding PII)
        if self.context:
            context_data = self.context.dict(exclude={'ip_address', 'user_agent'})
            base_data["context"] = context_data
            
        return base_data
