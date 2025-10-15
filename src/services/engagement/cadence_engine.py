"""Adaptive cadence engine for proactive-yet-considerate outreach."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence
from uuid import UUID

from packages.core.src.entities.analytics import EventTypefrom packages.core.src.entities.user import InventoryLink, UserGoal, UserProfilefrom services.analytics_service.src.application.analytics_service import AnalyticsService

@dataclass
class OutreachPlan:
    """Represents a single scheduled touchpoint."""

    user_id: str
    cadence_type: str
    template_id: str
    channel: str
    scheduled_for: datetime
    priority: str = "normal"
    metadata: Dict[str, object] = field(default_factory=dict)


class CadenceEngine:
    """Determines when and how to reach out without overwhelming users."""

    def __init__(
        self,
        analytics_service: AnalyticsService,
        *,
        strategy_interval_days: int = 7,
        progress_interval_days: int = 30,
        min_touch_gap_hours: int = 20,
    ) -> None:
        self._analytics = analytics_service
        self._strategy_interval_days = strategy_interval_days
        self._progress_interval_days = progress_interval_days
        self._min_touch_gap = timedelta(hours=min_touch_gap_hours)

    async def plan_user_cadence(
        self,
        user_profile: UserProfile,
        *,
        now: Optional[datetime] = None,
        recent_deviation: Optional[Dict[str, str]] = None,
        inventory_links: Optional[Sequence[InventoryLink]] = None,
        log_events: bool = False,
    ) -> List[OutreachPlan]:
        """Return a set of outreach actions that respect preferences and history."""

        current_time = now or datetime.now(timezone.utc)
        user_uuid = self._coerce_uuid(user_profile.user_id)
        preferred_channels = list(user_profile.preferred_channels or ["sms"])
        if not preferred_channels:
            preferred_channels = ["sms"]

        if user_profile.consent_flags.get("messaging_opt_out", False):
            return []

        last_touch = None
        if user_uuid:
            last_nudge = self._analytics.get_last_event_time(user_uuid, EventType.NUDGE_SENT)
            last_message = self._analytics.get_last_event_time(user_uuid, EventType.MESSAGE_INGESTED)
            last_touch = max(
                [value for value in (last_nudge, last_message) if value is not None],
                default=None,
            )

        if last_touch and current_time - last_touch < self._min_touch_gap:
            return []

        plans: List[OutreachPlan] = []

        channel = preferred_channels[0]
        inventory_ids = [link.inventory_id for link in inventory_links or user_profile.inventory_links]
        primary_goal = self._extract_primary_goal(user_profile)

        # Weekly strategy report
        strategy_due = self._is_due(user_uuid, EventType.STRATEGY_REPORT_SCHEDULED, self._strategy_interval_days, current_time)
        if strategy_due:
            scheduled_for = current_time + timedelta(hours=1)
            plan = OutreachPlan(
                user_id=user_profile.user_id,
                cadence_type="strategy_report",
                template_id="weekly_strategy_v1",
                channel=channel,
                scheduled_for=scheduled_for,
                metadata={
                    "inventory_sources": inventory_ids,
                    "goal_focus": primary_goal,
                    "reason": "weekly_cadence",
                },
            )
            plans.append(plan)
            if log_events and user_uuid:
                await self._analytics.track_strategy_report_scheduled(
                    user_uuid,
                    scheduled_for=scheduled_for,
                    channel=channel,
                    cadence="weekly",
                    personalization_score=self._estimate_personalization_score(user_profile),
                    inventory_sources=inventory_ids,
                    goal_focus=primary_goal,
                )

        # Recovery plan after deviation
        if recent_deviation:
            recovery_due = self._is_due(user_uuid, EventType.RECOVERY_PLAN_CREATED, 2, current_time)
            if recovery_due:
                scheduled_for = current_time + timedelta(hours=2)
                plan = OutreachPlan(
                    user_id=user_profile.user_id,
                    cadence_type="recovery_plan",
                    template_id="recovery_plan_v1",
                    channel=channel,
                    scheduled_for=scheduled_for,
                    priority="high",
                    metadata={
                        "deviation_reason": recent_deviation.get("reason"),
                        "inventory_sources": inventory_ids,
                        "recent_meal_id": recent_deviation.get("meal_id"),
                    },
                )
                plans.append(plan)
                if log_events and user_uuid:
                    await self._analytics.track_recovery_plan_created(
                        user_uuid,
                        plan_id=recent_deviation.get("plan_id", ""),
                        deviation_reason=recent_deviation.get("reason"),
                        channel=channel,
                        scheduled_for=scheduled_for,
                    )

        # Monthly (or configured) progress summary
        progress_due = self._is_due(user_uuid, EventType.PROGRESS_SUMMARY_PUBLISHED, self._progress_interval_days, current_time)
        if progress_due:
            period_end = current_time
            period_start = period_end - timedelta(days=self._progress_interval_days)
            plan = OutreachPlan(
                user_id=user_profile.user_id,
                cadence_type="progress_summary",
                template_id="progress_slides_v1",
                channel=channel,
                scheduled_for=current_time + timedelta(days=1),
                metadata={
                    "period_start": period_start.isoformat(),
                    "highlights": self._summarise_highlights(user_profile),
                },
            )
            plans.append(plan)
            if log_events and user_uuid:
                await self._analytics.track_progress_summary(
                    user_uuid,
                    period_start=period_start,
                    period_end=period_end,
                    channel=channel,
                    highlights=plan.metadata.get("highlights"),
                )

        return plans

    def _is_due(
        self,
        user_id: Optional[UUID],
        event_type: EventType,
        interval_days: int,
        now: datetime,
    ) -> bool:
        if not user_id:
            return True
        last_event = self._analytics.get_last_event_time(user_id, event_type)
        if not last_event:
            return True
        return now - last_event >= timedelta(days=interval_days)

    @staticmethod
    def _extract_primary_goal(user_profile: UserProfile) -> Optional[str]:
        goal = user_profile.get_primary_goal()
        if isinstance(goal, UserGoal):
            return goal.goal_type.value
        return None

    @staticmethod
    def _estimate_personalization_score(user_profile: UserProfile) -> float:
        score = 0.4
        if user_profile.medical_cautions:
            score += 0.2
        if user_profile.inventory_links:
            score += 0.2
        if user_profile.wearable_integrations:
            score += 0.2
        return round(min(score, 0.95), 2)

    @staticmethod
    def _summarise_highlights(user_profile: UserProfile) -> List[str]:
        highlights: List[str] = []
        if user_profile.meal_plans_this_month:
            highlights.append(f"{user_profile.meal_plans_this_month} meal plans generated this month")
        if user_profile.grocery_lists_this_month:
            highlights.append(f"{user_profile.grocery_lists_this_month} smart grocery lists shared")
        primary_goal = CadenceEngine._extract_primary_goal(user_profile)
        if primary_goal:
            highlights.append(f"Focused on {primary_goal.replace('_', ' ')}")
        return highlights

    @staticmethod
    def _coerce_uuid(value: str) -> Optional[UUID]:
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None
