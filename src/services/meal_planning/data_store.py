"""Data store abstractions for meal plan inputs and persistence support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Protocol

from .models import PlanPreferences
from .repository import GeneratedMealPlan


@dataclass
class UserRecord:
    """Represents a user profile entry."""

    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    region: str = "us"


@dataclass
class UserPreferenceRecord:
    """Captured user preferences for meal planning."""

    user_id: str
    diet: Optional[str] = None
    allergies: List[str] = field(default_factory=list)
    avoid_ingredients: List[str] = field(default_factory=list)
    budget_weekly: Optional[float] = None
    max_prep_minutes: Optional[int] = None
    servings: Optional[int] = None
    cuisines: List[str] = field(default_factory=list)
    pantry_items: List[str] = field(default_factory=list)
    calorie_target: Optional[int] = None
    grocery_cadence: Optional[str] = None

    def to_preferences(self) -> PlanPreferences:
        return PlanPreferences(
            diet=self.diet,
            allergies=list(self.allergies),
            avoid_ingredients=list(self.avoid_ingredients),
            budget_limit=self.budget_weekly,
            max_prep_minutes=self.max_prep_minutes,
            servings=self.servings,
            cuisines=list(self.cuisines),
            pantry_items=list(self.pantry_items),
            calorie_target=self.calorie_target,
            grocery_cadence=self.grocery_cadence,
        )


@dataclass
class PantryItemRecord:
    """Represents an item the user commonly stocks."""

    user_id: str
    name: str
    quantity: Optional[str] = None


class PlanDataStore(Protocol):
    """Protocol for retrieving and persisting plan-related data."""

    def get_user_preferences(self, user_id: str) -> PlanPreferences:
        ...

    def save_generated_plan(self, plan: GeneratedMealPlan) -> None:
        ...

    def list_recent_plans(self, user_id: str, limit: int = 5) -> List[GeneratedMealPlan]:
        ...


class InMemoryPlanDataStore(PlanDataStore):
    """Lightweight in-memory data store for local usage and tests."""

    def __init__(self) -> None:
        self._users: Dict[str, UserRecord] = {}
        self._preferences: Dict[str, UserPreferenceRecord] = {}
        self._pantry: Dict[str, List[PantryItemRecord]] = {}
        self._plans: Dict[str, List[GeneratedMealPlan]] = {}

    def register_user(self, record: UserRecord) -> None:
        self._users[record.user_id] = record

    def register_preferences(self, record: UserPreferenceRecord) -> None:
        self._preferences[record.user_id] = record

    def register_pantry_items(self, user_id: str, items: Iterable[PantryItemRecord]) -> None:
        self._pantry.setdefault(user_id, [])
        self._pantry[user_id].extend(items)

    def get_user_preferences(self, user_id: str) -> PlanPreferences:
        record = self._preferences.get(user_id)
        if record:
            return record.to_preferences()
        return PlanPreferences()

    def save_generated_plan(self, plan: GeneratedMealPlan) -> None:
        plans = self._plans.setdefault(plan.user_id, [])
        plans.insert(0, plan)
        del plans[5:]

    def list_recent_plans(self, user_id: str, limit: int = 5) -> List[GeneratedMealPlan]:
        plans = self._plans.get(user_id, [])
        return plans[:limit]


__all__ = [
    "PlanDataStore",
    "InMemoryPlanDataStore",
    "UserRecord",
    "UserPreferenceRecord",
    "PantryItemRecord",
]
