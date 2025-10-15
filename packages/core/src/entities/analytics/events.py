"""Analytics events module.

Specific analytics event classes for tracking user interactions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseEvent
from .enums import EventType, PIILevel


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


class StrategyReportScheduledEvent(BaseEvent):
    """Event: Strategy report scheduled or delivered."""

    event_type: EventType = EventType.STRATEGY_REPORT_SCHEDULED

    def __init__(
        self,
        user_id: UUID,
        scheduled_for: datetime,
        channel: str,
        cadence: str,
        personalization_score: Optional[float] = None,
        inventory_sources: Optional[List[str]] = None,
        goal_focus: Optional[str] = None,
        **kwargs,
    ):
        properties = {
            "scheduled_for": scheduled_for.isoformat(),
            "channel": channel,
            "cadence": cadence,
            "personalization_score": personalization_score,
            "inventory_sources": inventory_sources or [],
            "goal_focus": goal_focus,
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs,
        )


class RecoveryPlanCreatedEvent(BaseEvent):
    """Event: Recovery plan crafted after a deviation."""

    event_type: EventType = EventType.RECOVERY_PLAN_CREATED

    def __init__(
        self,
        user_id: UUID,
        plan_id: str,
        deviation_reason: Optional[str],
        channel: str,
        scheduled_for: datetime,
        **kwargs,
    ):
        properties = {
            "plan_id": plan_id,
            "deviation_reason": deviation_reason,
            "channel": channel,
            "scheduled_for": scheduled_for.isoformat(),
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs,
        )


class ProgressSummaryPublishedEvent(BaseEvent):
    """Event: Long-term progress summary published."""

    event_type: EventType = EventType.PROGRESS_SUMMARY_PUBLISHED

    def __init__(
        self,
        user_id: UUID,
        period_start: datetime,
        period_end: datetime,
        channel: str,
        highlights: Optional[List[str]] = None,
        **kwargs,
    ):
        properties = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "channel": channel,
            "highlights": highlights or [],
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs,
        )


class MessageIngestedEvent(BaseEvent):
    """Event: Inbound user message captured and normalised."""

    event_type: EventType = EventType.MESSAGE_INGESTED

    def __init__(
        self,
        user_id: Optional[UUID],
        platform: str,
        tones_detected: Optional[List[str]] = None,
        token_count: Optional[int] = None,
        **kwargs,
    ):
        properties = {
            "platform": platform,
            "tones_detected": tones_detected or [],
            "token_count": token_count,
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.PSEUDONYMIZED,
            **kwargs,
        )


class WearableSyncEvent(BaseEvent):
    """Event: Wearable data synced successfully."""

    event_type: EventType = EventType.WEARABLE_SYNCED

    def __init__(
        self,
        user_id: UUID,
        provider: str,
        metrics: Dict[str, Any],
        synced_at: datetime,
        **kwargs,
    ):
        properties = {
            "provider": provider,
            "metrics": metrics,
            "synced_at": synced_at.isoformat(),
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.PSEUDONYMIZED,
            **kwargs,
        )


class InventoryStateRecordedEvent(BaseEvent):
    """Event: Pantry or inventory snapshot recorded."""

    event_type: EventType = EventType.INVENTORY_STATE_RECORDED

    def __init__(
        self,
        user_id: UUID,
        inventory_id: str,
        location: str,
        freshness_index: Optional[float] = None,
        expiring_items: Optional[int] = None,
        **kwargs,
    ):
        properties = {
            "inventory_id": inventory_id,
            "location": location,
            "freshness_index": freshness_index,
            "expiring_items": expiring_items,
        }
        super().__init__(
            user_id=user_id,
            properties=properties,
            pii_level=PIILevel.NONE,
            **kwargs,
        )
