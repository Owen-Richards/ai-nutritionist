"""Data models used by the meal planning orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class PlanPreferences:
    """Normalized preference inputs for meal plan generation."""

    diet: Optional[str] = None
    allergies: List[str] = field(default_factory=list)
    avoid_ingredients: List[str] = field(default_factory=list)
    budget_limit: Optional[float] = None
    max_prep_minutes: Optional[int] = None
    servings: Optional[int] = None
    cuisines: List[str] = field(default_factory=list)
    pantry_items: List[str] = field(default_factory=list)
    calorie_target: Optional[int] = None
    grocery_cadence: Optional[str] = None
    inventory_sources: List[str] = field(default_factory=list)
    preferred_channels: List[str] = field(default_factory=list)
    dietary_patterns: List[str] = field(default_factory=list)
    intolerances: List[str] = field(default_factory=list)
    preference_tags: List[str] = field(default_factory=list)
    required_ingredients: List[str] = field(default_factory=list)


@dataclass
class PlanGenerationCommand:
    """Encapsulates a plan generation request."""

    user_id: str
    preferences: PlanPreferences
    week_start: date
    force_new: bool = False
    context: Dict[str, Any] = field(default_factory=dict)
    request_metadata: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    inventory_snapshot_id: Optional[str] = None
    pantry_state_version: Optional[str] = None


@dataclass
class DraftMeal:
    """Meal candidate produced by the generation engine before persistence."""

    day: str
    meal_type: str
    title: str
    description: str
    ingredients: List[str]
    calories: int
    prep_minutes: int
    cost: float
    macros: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class PlanDraft:
    """Draft meal plan produced by the engine prior to orchestration enrichment."""

    meals: List[DraftMeal]
    estimated_cost: float
    macro_summary: Dict[str, float]
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class PlanFeedbackCommand:
    """Normalized payload for feedback ingestion."""

    user_id: str
    plan_id: str
    meal_id: str
    rating: int
    emoji: Optional[str] = None
    comment: Optional[str] = None
    consumed_at: Optional[datetime] = None


__all__ = [
    "PlanPreferences",
    "PlanGenerationCommand",
    "DraftMeal",
    "PlanDraft",
    "PlanFeedbackCommand",
]
