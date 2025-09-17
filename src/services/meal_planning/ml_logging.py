"""Feature logging utilities for meal plan generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import PlanPreferences
from .repository import GeneratedMealPlan


@dataclass
class PlanFeatureRecord:
    """Stored representation of plan generation features."""

    user_id: str
    plan_id: str
    week_start: str
    estimated_cost: float
    total_calories: int
    diet: str | None
    budget_limit: float | None
    max_prep_minutes: int | None
    macro_summary: Dict[str, float]


class FeatureLogger:
    """Collects plan features for offline analysis."""

    def __init__(self) -> None:
        self._plan_records: List[PlanFeatureRecord] = []

    def log_plan_generation(
        self,
        plan: GeneratedMealPlan,
        preferences: PlanPreferences,
    ) -> None:
        record = PlanFeatureRecord(
            user_id=plan.user_id,
            plan_id=plan.plan_id,
            week_start=plan.week_start.isoformat(),
            estimated_cost=plan.estimated_cost,
            total_calories=plan.total_calories,
            diet=preferences.diet,
            budget_limit=preferences.budget_limit,
            max_prep_minutes=preferences.max_prep_minutes,
            macro_summary=plan.metadata.get("macro_summary", {}),
        )
        self._plan_records.append(record)

    def get_plan_records(self) -> List[PlanFeatureRecord]:
        return list(self._plan_records)

    def reset(self) -> None:
        self._plan_records.clear()


__all__ = ["FeatureLogger", "PlanFeatureRecord"]
