"""Persistence primitives for meal plans."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Protocol, Tuple


@dataclass(frozen=True)
class MealEntry:
    """A single meal persisted as part of a weekly plan."""

    meal_id: str
    day: str
    meal_type: str
    title: str
    description: str
    ingredients: List[str]
    calories: int
    prep_minutes: int
    macros: Dict[str, float]
    cost: float
    tags: List[str] = field(default_factory=list)


@dataclass
class GeneratedMealPlan:
    """Materialized weekly plan stored for retrieval."""

    plan_id: str
    user_id: str
    week_start: date
    generated_at: datetime
    meals: List[MealEntry]
    estimated_cost: float
    total_calories: int
    grocery_list: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanFeedback:
    """Captured user feedback for a specific meal."""

    user_id: str
    plan_id: str
    meal_id: str
    rating: int
    comment: Optional[str]
    emoji: Optional[str]
    created_at: datetime
    consumed_at: Optional[datetime] = None


class PlanRepository(Protocol):
    """Abstract storage contract for meal plans and feedback."""

    def save_plan(self, plan: GeneratedMealPlan) -> None:
        ...

    def get_plan_for_week(self, user_id: str, week_start: date) -> Optional[GeneratedMealPlan]:
        ...

    def get_latest_plan(self, user_id: str) -> Optional[GeneratedMealPlan]:
        ...

    def remember_idempotency(self, user_id: str, key: str, plan: GeneratedMealPlan, expires_at: datetime) -> None:
        ...

    def get_plan_by_idempotency(self, user_id: str, key: str) -> Optional[GeneratedMealPlan]:
        ...

    def record_feedback(self, feedback: PlanFeedback) -> None:
        ...

    def list_feedback(self, user_id: str, plan_id: str) -> List[PlanFeedback]:
        ...


class InMemoryPlanRepository(PlanRepository):
    """Thread-safe in-memory repository for local development and testing."""

    def __init__(self) -> None:
        self._plans_by_week: Dict[Tuple[str, date], GeneratedMealPlan] = {}
        self._latest_plan: Dict[str, GeneratedMealPlan] = {}
        self._idempotency: Dict[Tuple[str, str], Tuple[GeneratedMealPlan, datetime]] = {}
        self._feedback: Dict[Tuple[str, str], List[PlanFeedback]] = {}
        self._lock = Lock()

    def save_plan(self, plan: GeneratedMealPlan) -> None:
        with self._lock:
            plan_copy = copy.deepcopy(plan)
            self._plans_by_week[(plan.user_id, plan.week_start)] = plan_copy
            self._latest_plan[plan.user_id] = plan_copy

    def get_plan_for_week(self, user_id: str, week_start: date) -> Optional[GeneratedMealPlan]:
        with self._lock:
            plan = self._plans_by_week.get((user_id, week_start))
            return copy.deepcopy(plan) if plan else None

    def get_latest_plan(self, user_id: str) -> Optional[GeneratedMealPlan]:
        with self._lock:
            plan = self._latest_plan.get(user_id)
            return copy.deepcopy(plan) if plan else None

    def remember_idempotency(self, user_id: str, key: str, plan: GeneratedMealPlan, expires_at: datetime) -> None:
        with self._lock:
            self._idempotency[(user_id, key)] = (copy.deepcopy(plan), expires_at)

    def get_plan_by_idempotency(self, user_id: str, key: str) -> Optional[GeneratedMealPlan]:
        with self._lock:
            entry = self._idempotency.get((user_id, key))
            if not entry:
                return None
            plan, expires_at = entry
            if expires_at < datetime.now(UTC):
                del self._idempotency[(user_id, key)]
                return None
            return copy.deepcopy(plan)

    def record_feedback(self, feedback: PlanFeedback) -> None:
        with self._lock:
            key = (feedback.user_id, feedback.plan_id)
            feedback_list = self._feedback.setdefault(key, [])
            feedback_list.append(copy.deepcopy(feedback))

    def list_feedback(self, user_id: str, plan_id: str) -> List[PlanFeedback]:
        with self._lock:
            items = self._feedback.get((user_id, plan_id), [])
            return copy.deepcopy(items)


__all__ = [
    "MealEntry",
    "GeneratedMealPlan",
    "PlanFeedback",
    "PlanRepository",
    "InMemoryPlanRepository",
]
