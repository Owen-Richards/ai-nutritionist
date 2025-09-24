"""Analytics and event tracking models for Track F.

Comprehensive event taxonomy with privacy-aware schema design.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


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
    
    @validator('timestamp')
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


# Specific event models with typed properties

class PlanGeneratedEvent(BaseEvent):
    """Event: User generates a meal plan."""
    event_type: EventType = EventType.PLAN_GENERATED
    
    def __init__(
        self, 
        user_id: UUID,
        plan_id: UUID,
        ruleset: str,
        est_cost_cents: int,
        duration_ms: int,
        dietary_preferences: Optional[List[str]] = None,
        budget_constraint: Optional[float] = None,
        time_constraint_min: Optional[int] = None,
        **kwargs
    ):
        properties = {
            "plan_id": str(plan_id),
            "ruleset": ruleset,
            "est_cost_cents": est_cost_cents,
            "duration_ms": duration_ms,
            "dietary_preferences": dietary_preferences or [],
            "budget_constraint": budget_constraint,
            "time_constraint_min": time_constraint_min
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class MealLoggedEvent(BaseEvent):
    """Event: User logs meal consumption."""
    event_type: EventType = EventType.MEAL_LOGGED
    
    def __init__(
        self,
        user_id: UUID,
        meal_id: UUID,
        status: str,  # eaten, skipped, partial
        source: str,  # sms, app, widget
        mood_score: Optional[int] = None,
        energy_score: Optional[int] = None,
        satiety_score: Optional[int] = None,
        skip_reason: Optional[str] = None,
        **kwargs
    ):
        properties = {
            "meal_id": str(meal_id),
            "status": status,
            "source": source,
            "mood_score": mood_score,
            "energy_score": energy_score,
            "satiety_score": satiety_score,
            "skip_reason": skip_reason
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class NudgeSentEvent(BaseEvent):
    """Event: SMS/push nudge sent to user."""
    event_type: EventType = EventType.NUDGE_SENT
    
    def __init__(
        self,
        user_id: UUID,
        template_id: str,
        channel: str,  # sms, push, email
        experiment_id: Optional[str] = None,
        crew_id: Optional[UUID] = None,
        personalization_score: Optional[float] = None,
        **kwargs
    ):
        properties = {
            "template_id": template_id,
            "channel": channel,
            "experiment_id": experiment_id,
            "crew_id": str(crew_id) if crew_id else None,
            "personalization_score": personalization_score
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class NudgeClickedEvent(BaseEvent):
    """Event: User clicks on nudge/notification."""
    event_type: EventType = EventType.NUDGE_CLICKED
    
    def __init__(
        self,
        user_id: UUID,
        nudge_id: str,
        template_id: str,
        channel: str,
        time_to_click_seconds: int,
        destination: Optional[str] = None,
        **kwargs
    ):
        properties = {
            "nudge_id": nudge_id,
            "template_id": template_id,
            "channel": channel,
            "time_to_click_seconds": time_to_click_seconds,
            "destination": destination
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class CrewJoinedEvent(BaseEvent):
    """Event: User joins a crew/community."""
    event_type: EventType = EventType.CREW_JOINED
    
    def __init__(
        self,
        user_id: UUID,
        crew_id: UUID,
        crew_type: str,
        invite_source: Optional[str] = None,
        crew_size: Optional[int] = None,
        **kwargs
    ):
        properties = {
            "crew_id": str(crew_id),
            "crew_type": crew_type,
            "invite_source": invite_source,
            "crew_size": crew_size
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class ReflectionSubmittedEvent(BaseEvent):
    """Event: User submits reflection/feedback."""
    event_type: EventType = EventType.REFLECTION_SUBMITTED
    
    def __init__(
        self,
        user_id: UUID,
        reflection_id: UUID,
        crew_id: Optional[UUID] = None,
        content_length: int = 0,
        sentiment_score: Optional[float] = None,
        contains_pii: bool = False,
        **kwargs
    ):
        properties = {
            "reflection_id": str(reflection_id),
            "crew_id": str(crew_id) if crew_id else None,
            "content_length": content_length,
            "sentiment_score": sentiment_score,
            "contains_pii": contains_pii
        }
        pii_level = PIILevel.SENSITIVE if contains_pii else PIILevel.NONE
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=pii_level,
            **kwargs
        )


class PaywallViewedEvent(BaseEvent):
    """Event: User views paywall/upgrade prompt."""
    event_type: EventType = EventType.PAYWALL_VIEWED
    
    def __init__(
        self,
        user_id: UUID,
        price_usd: float,
        variant: str,
        source: str,  # feature_gate, usage_limit, trial_expired
        trigger_feature: Optional[str] = None,
        experiment_id: Optional[str] = None,
        **kwargs
    ):
        properties = {
            "price_usd": price_usd,
            "variant": variant,
            "source": source,
            "trigger_feature": trigger_feature,
            "experiment_id": experiment_id
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class SubscribeStartedEvent(BaseEvent):
    """Event: User starts subscription flow."""
    event_type: EventType = EventType.SUBSCRIBE_STARTED
    
    def __init__(
        self,
        user_id: UUID,
        tier: str,
        interval: str,  # monthly, yearly
        price_usd: float,
        source: str,
        experiment_id: Optional[str] = None,
        **kwargs
    ):
        properties = {
            "tier": tier,
            "interval": interval,
            "price_usd": price_usd,
            "source": source,
            "experiment_id": experiment_id
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class SubscribeActivatedEvent(BaseEvent):
    """Event: User successfully activates subscription."""
    event_type: EventType = EventType.SUBSCRIBE_ACTIVATED
    
    def __init__(
        self,
        user_id: UUID,
        tier: str,
        price_usd: float,
        coupon: Optional[str] = None,
        experiment_id: Optional[str] = None,
        time_to_activate_seconds: Optional[int] = None,
        **kwargs
    ):
        properties = {
            "tier": tier,
            "price_usd": price_usd,
            "coupon": coupon,
            "experiment_id": experiment_id,
            "time_to_activate_seconds": time_to_activate_seconds
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


class ChurnedEvent(BaseEvent):
    """Event: User churns (cancels subscription or becomes inactive)."""
    event_type: EventType = EventType.CHURNED
    
    def __init__(
        self,
        user_id: UUID,
        churn_type: str,  # voluntary, involuntary, trial_expired
        previous_tier: str,
        days_subscribed: Optional[int] = None,
        reason: Optional[str] = None,
        ltv_usd: Optional[float] = None,
        **kwargs
    ):
        properties = {
            "churn_type": churn_type,
            "previous_tier": previous_tier,
            "days_subscribed": days_subscribed,
            "reason": reason,
            "ltv_usd": ltv_usd
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs
        )


# User profile and consent models

class UserConsent(BaseModel):
    """User consent preferences for data processing."""
    user_id: UUID
    consent_type: ConsentType
    granted: bool
    granted_at: datetime
    version: str = "1.0"  # Consent policy version
    source: str = "app"   # app, web, email
    
    # GDPR compliance
    legal_basis: Optional[str] = None  # consent, legitimate_interest, etc.
    can_withdraw: bool = True
    withdrawal_method: Optional[str] = None
    
    class Config:
        extra = "forbid"


class UserProfile(BaseModel):
    """User profile with PII separation."""
    
    # Non-PII behavioral data
    user_id: UUID
    created_at: datetime
    last_active_at: Optional[datetime] = None
    
    # Aggregated behavioral metrics (no PII)
    total_plans_generated: int = 0
    total_meals_logged: int = 0
    total_nudges_sent: int = 0
    total_nudges_clicked: int = 0
    
    # Subscription info (no PII)
    current_tier: Optional[str] = None
    subscription_start: Optional[datetime] = None
    ltv_usd: float = 0.0
    
    # Engagement metrics
    weekly_active_weeks: int = 0
    longest_streak_days: int = 0
    average_adherence_percent: Optional[float] = None
    
    # Preferences (anonymized)
    dietary_restrictions: List[str] = Field(default_factory=list)
    budget_tier: Optional[str] = None  # low, medium, high (anonymized)
    time_preference: Optional[str] = None  # quick, moderate, elaborate
    
    class Config:
        extra = "forbid"


class UserPII(BaseModel):
    """Separate PII storage with encryption."""
    user_id: UUID
    
    # Direct identifiers (encrypted)
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    
    # Location data (hashed/anonymized)
    region: Optional[str] = None  # US, EU, etc.
    timezone: Optional[str] = None
    
    # Device information
    device_ids: List[str] = Field(default_factory=list)
    
    # Consent tracking
    consents: List[UserConsent] = Field(default_factory=list)
    
    # Data retention
    retention_until: Optional[datetime] = None
    deletion_requested: bool = False
    deletion_requested_at: Optional[datetime] = None
    
    class Config:
        extra = "forbid"
    
    def has_consent(self, consent_type: ConsentType) -> bool:
        """Check if user has granted specific consent."""
        for consent in self.consents:
            if consent.consent_type == consent_type and consent.granted:
                return True
        return False
    
    def can_process_for(self, consent_type: ConsentType) -> bool:
        """Check if we can process data for specific purpose."""
        return self.has_consent(consent_type) and not self.deletion_requested


# Analytics aggregation models

class CohortMetrics(BaseModel):
    """Cohort analysis metrics."""
    cohort_id: str  # YYYY-MM format
    cohort_size: int
    
    # Retention metrics
    day_1_retention: float
    day_7_retention: float
    day_30_retention: float
    day_90_retention: float
    
    # Engagement metrics
    avg_plans_per_user: float
    avg_meals_logged_per_user: float
    avg_adherence_percent: float
    
    # Monetization metrics
    conversion_rate: float
    avg_ltv_usd: float
    avg_time_to_convert_days: Optional[float] = None
    
    # Calculated at
    calculated_at: datetime


class FunnelMetrics(BaseModel):
    """Activation funnel metrics."""
    period_start: datetime
    period_end: datetime
    
    # Funnel steps
    registered_users: int
    completed_onboarding: int
    generated_first_plan: int
    logged_first_meal: int
    active_day_7: int
    active_day_30: int
    
    # Conversion rates
    onboarding_rate: float
    first_plan_rate: float
    first_meal_rate: float
    d7_activation_rate: float
    d30_retention_rate: float
    
    class Config:
        extra = "forbid"


class RevenueMetrics(BaseModel):
    """Revenue and subscription metrics."""
    period_start: datetime
    period_end: datetime
    
    # Subscription metrics
    new_subscribers: int
    churned_subscribers: int
    net_subscriber_growth: int
    total_active_subscribers: int
    
    # Revenue metrics
    mrr_usd: float  # Monthly Recurring Revenue
    arr_usd: float  # Annual Recurring Revenue
    arpu_usd: float  # Average Revenue Per User
    ltv_usd: float  # Customer Lifetime Value
    
    # Tier breakdown
    free_users: int
    plus_subscribers: int
    pro_subscribers: int
    
    # Churn analysis
    voluntary_churn_rate: float
    involuntary_churn_rate: float
    
    class Config:
        extra = "forbid"
