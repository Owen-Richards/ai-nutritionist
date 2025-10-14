"""Premium reporting scaffolding for strategy, recovery, and progress insights."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from packages.core.src.entities.user import InventoryLink, UserProfilefrom src.services.compliance.playbook_registry import PlaybookRegistry, PlaybookEntry


@dataclass
class StrategyReport:
    summary: str
    highlights: List[str]
    grocery_recommendations: List[str]
    scheduled_for: datetime


@dataclass
class RecoveryPlan:
    reassurance: str
    swaps: List[str]
    mindful_tips: List[str]
    scheduled_for: datetime


@dataclass
class ProgressSlides:
    headline: str
    slides: List[Dict[str, str]]
    period_start: datetime
    period_end: datetime


class PremiumInsightsService:
    """Curates proactive insights from profile, pantry, and analytics signals."""

    def __init__(self, *, timezone_pref: str = "UTC", playbook_registry: Optional[PlaybookRegistry] = None) -> None:
        self._timezone_pref = timezone_pref
        self._playbooks = playbook_registry

    def generate_strategy_report(
        self,
        user_profile: UserProfile,
        inventory_links: Optional[List[InventoryLink]] = None,
        *,
        scheduled_for: Optional[datetime] = None,
    ) -> StrategyReport:
        scheduled_time = scheduled_for or datetime.now(timezone.utc)
        highlights = self._build_highlights(user_profile)
        grocery_recs = [link.inventory_id for link in inventory_links or user_profile.inventory_links]
        summary = "Balanced plan ready – here's how we'll keep momentum this week."
        return StrategyReport(
            summary=summary,
            highlights=highlights,
            grocery_recommendations=grocery_recs,
            scheduled_for=scheduled_time,
        )

    def generate_recovery_plan(
        self,
        user_profile: UserProfile,
        *,
        deviation_reason: Optional[str] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> RecoveryPlan:
        scheduled_time = scheduled_for or datetime.now(timezone.utc) + timedelta(hours=2)
        reassurance = "One meal won't derail you. Let's pivot with something light and satisfying."
        swaps = self._build_swaps(user_profile, deviation_reason)
        mindful_tips = self._pull_playbook_tips(user_profile) or [
            "Hydrate before your next meal",
            "Add a short walk to reset energy",
        ]
        return RecoveryPlan(
            reassurance=reassurance,
            swaps=swaps,
            mindful_tips=mindful_tips,
            scheduled_for=scheduled_time,
        )

    def generate_progress_slides(
        self,
        user_profile: UserProfile,
        *,
        period_days: int = 30,
        now: Optional[datetime] = None,
    ) -> ProgressSlides:
        current_time = now or datetime.now(timezone.utc)
        start = current_time - timedelta(days=period_days)
        slides = [
            {
                "title": "Consistency",
                "body": f"{user_profile.meal_plans_this_month} plans completed",
            },
            {
                "title": "Healthy choices",
                "body": f"{len(user_profile.medical_cautions)} cautions considered automatically",
            },
        ]
        headline = "Your month of healthier eating at a glance"
        return ProgressSlides(
            headline=headline,
            slides=slides,
            period_start=start,
            period_end=current_time,
        )

    @staticmethod
    def _build_highlights(user_profile: UserProfile) -> List[str]:
        highlights = []
        primary_goal = user_profile.get_primary_goal()
        if primary_goal:
            highlights.append(f"Primary focus: {primary_goal.goal_type.value}")
        if user_profile.inventory_links:
            highlights.append("Pantry synced – meals will reuse on-hand ingredients")
        if user_profile.wearable_integrations:
            highlights.append("Wearable insights tuned into your meal timing")
        return highlights

    @staticmethod
    def _build_swaps(user_profile: UserProfile, deviation_reason: Optional[str]) -> List[str]:
        base_swaps = ["Swap in a high-protein snack", "Plan a lighter dinner"]
        if deviation_reason and "travel" in deviation_reason.lower():
            base_swaps.append("Pack portable snacks for tomorrow")
        return base_swaps

    def _pull_playbook_tips(self, user_profile: UserProfile) -> Optional[List[str]]:
        if not self._playbooks or not user_profile.medical_cautions:
            return None
        caution = user_profile.medical_cautions[0]
        entry: Optional[PlaybookEntry] = self._playbooks.get(caution.condition, language_key=user_profile.language)
        if not entry:
            return None
        return entry.responses
