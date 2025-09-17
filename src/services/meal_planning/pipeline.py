"""Meal plan pipeline orchestration."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Dict, Optional

from .data_store import PlanDataStore
from .models import PlanPreferences
from .plan_coordinator import PlanCoordinator
from .repository import GeneratedMealPlan
from .ml_logging import FeatureLogger


class MealPlanPipeline:
    """Coordinates data collection, plan generation, and feature logging."""

    def __init__(
        self,
        coordinator: PlanCoordinator,
        data_store: PlanDataStore,
        feature_logger: FeatureLogger,
    ) -> None:
        self._coordinator = coordinator
        self._data_store = data_store
        self._feature_logger = feature_logger

    def generate_plan(
        self,
        user_id: str,
        *,
        overrides: Optional[PlanPreferences] = None,
        week_start: Optional[date] = None,
        force_new: bool = False,
        context: Optional[Dict[str, object]] = None,
        metadata: Optional[Dict[str, object]] = None,
        idempotency_key: Optional[str] = None,
    ) -> GeneratedMealPlan:
        """Generate a weekly plan leveraging stored preferences and overrides."""

        base_preferences = self._data_store.get_user_preferences(user_id)
        merged_preferences = _merge_preferences(base_preferences, overrides)

        command = PlanCoordinator.build_generation_command(
            user_id=user_id,
            preferences=merged_preferences,
            week_start=week_start,
            force_new=force_new,
            context=context,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        plan = self._coordinator.generate_plan(command)
        self._data_store.save_generated_plan(plan)
        self._feature_logger.log_plan_generation(plan, merged_preferences)
        return plan


def _merge_preferences(
    base: PlanPreferences,
    overrides: Optional[PlanPreferences],
) -> PlanPreferences:
    if overrides is None:
        return base

    merged = replace(base)

    if overrides.diet is not None:
        merged.diet = overrides.diet
    if overrides.allergies:
        merged.allergies = list(overrides.allergies)
    if overrides.avoid_ingredients:
        merged.avoid_ingredients = list(overrides.avoid_ingredients)
    if overrides.budget_limit is not None:
        merged.budget_limit = overrides.budget_limit
    if overrides.max_prep_minutes is not None:
        merged.max_prep_minutes = overrides.max_prep_minutes
    if overrides.servings is not None:
        merged.servings = overrides.servings
    if overrides.cuisines:
        merged.cuisines = list(overrides.cuisines)
    if overrides.pantry_items:
        merged.pantry_items = list(overrides.pantry_items)
    if overrides.calorie_target is not None:
        merged.calorie_target = overrides.calorie_target
    if overrides.grocery_cadence is not None:
        merged.grocery_cadence = overrides.grocery_cadence

    return merged


__all__ = ["MealPlanPipeline"]
