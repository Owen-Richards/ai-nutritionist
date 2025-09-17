"""Orchestrates meal plan generation, retrieval, and feedback."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from .models import (
    PlanDraft,
    PlanFeedbackCommand,
    PlanGenerationCommand,
    PlanPreferences,
)
from .repository import GeneratedMealPlan, MealEntry, PlanFeedback, PlanRepository
from .rule_engine import RuleBasedMealPlanEngine


@dataclass
class FeedbackResult:
    """Result returned after processing meal feedback."""

    status: str
    action: str
    message: str


class PlanCoordinator:
    """Facade responsible for orchestrating meal plan lifecycle operations."""

    def __init__(
        self,
        repository: PlanRepository,
        engine: Optional[RuleBasedMealPlanEngine] = None,
        idempotency_ttl_hours: int = 24,
    ) -> None:
        self._repository = repository
        self._engine = engine or RuleBasedMealPlanEngine()
        self._idempotency_ttl = idempotency_ttl_hours

    def generate_plan(self, command: PlanGenerationCommand) -> GeneratedMealPlan:
        """Generate or retrieve a plan for the requested week."""

        plan = None
        if command.idempotency_key:
            plan = self._repository.get_plan_by_idempotency(command.user_id, command.idempotency_key)
        if plan:
            return plan

        if not command.force_new:
            plan = self._repository.get_plan_for_week(command.user_id, command.week_start)
            if plan:
                return plan

        draft = self._engine.generate(command)
        plan = self._materialize_plan(command, draft)
        self._repository.save_plan(plan)

        if command.idempotency_key:
            expires_at = datetime.now(UTC) + timedelta(hours=self._idempotency_ttl)
            self._repository.remember_idempotency(command.user_id, command.idempotency_key, plan, expires_at)

        return plan

    def get_plan(self, user_id: str, week_start: Optional[date] = None) -> Optional[GeneratedMealPlan]:
        """Fetch a plan for the requested week or fallback to the latest one."""

        target_week = week_start or compute_week_start(date.today())
        plan = self._repository.get_plan_for_week(user_id, target_week)
        if plan:
            return plan
        if week_start and week_start != target_week:
            return None
        return self._repository.get_latest_plan(user_id)

    def record_feedback(self, command: PlanFeedbackCommand) -> FeedbackResult:
        """Record feedback for a meal and return next-step guidance."""

        if command.rating < 1 or command.rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        if not command.plan_id:
            raise ValueError("Feedback requires an associated plan_id")

        feedback = PlanFeedback(
            user_id=command.user_id,
            plan_id=command.plan_id,
            meal_id=command.meal_id,
            rating=command.rating,
            comment=command.comment,
            emoji=command.emoji,
            created_at=datetime.now(UTC),
            consumed_at=command.consumed_at,
        )
        self._repository.record_feedback(feedback)
        self._engine.ingest_feedback(command)

        if command.rating >= 4:
            action = "reinforce"
            message = "Noted as a hit. Similar meals will be prioritised."
        elif command.rating <= 2:
            action = "adjust"
            message = "Meal flagged for adjustment in future plans."
        else:
            action = "watch"
            message = "Feedback captured. We will keep monitoring preference drift."

        return FeedbackResult(status="ok", action=action, message=message)

    @staticmethod
    def build_generation_command(
        user_id: str,
        preferences: PlanPreferences,
        week_start: Optional[date] = None,
        *,
        force_new: bool = False,
        context: Optional[Dict[str, object]] = None,
        metadata: Optional[Dict[str, object]] = None,
        idempotency_key: Optional[str] = None,
    ) -> PlanGenerationCommand:
        """Helper to create a command with defaults normalised."""

        target_week = compute_week_start(week_start or date.today())
        return PlanGenerationCommand(
            user_id=user_id,
            preferences=preferences,
            week_start=target_week,
            force_new=force_new,
            context=context or {},
            request_metadata=metadata or {},
            idempotency_key=idempotency_key,
        )

    def _materialize_plan(self, command: PlanGenerationCommand, draft: PlanDraft) -> GeneratedMealPlan:
        plan_id = command.request_metadata.get("plan_id") if command.request_metadata else None
        if not plan_id:
            plan_id = uuid4().hex

        generated_at = datetime.now(UTC)
        meals = [
            MealEntry(
                meal_id=f"{plan_id}:{meal.day}:{meal.meal_type}:{index}",
                day=meal.day,
                meal_type=meal.meal_type,
                title=meal.title,
                description=meal.description,
                ingredients=meal.ingredients,
                calories=meal.calories,
                prep_minutes=meal.prep_minutes,
                macros=meal.macros,
                cost=meal.cost,
                tags=meal.tags,
            )
            for index, meal in enumerate(draft.meals)
        ]

        metadata = {
            "preferences": asdict(command.preferences),
            "macro_summary": draft.macro_summary,
            "notes": draft.notes,
            "warnings": draft.warnings,
        }

        grocery_list = _build_grocery_list(draft)

        return GeneratedMealPlan(
            plan_id=plan_id,
            user_id=command.user_id,
            week_start=command.week_start,
            generated_at=generated_at,
            meals=meals,
            estimated_cost=draft.estimated_cost,
            total_calories=draft.macro_summary.get("calories", 0),
            grocery_list=grocery_list,
            metadata=metadata,
        )


def compute_week_start(target: Optional[date] = None) -> date:
    """Return the Monday for the supplied date."""

    target = target or date.today()
    return target - timedelta(days=target.weekday())


def _build_grocery_list(draft: PlanDraft) -> List[Dict[str, object]]:
    """Create a deduplicated grocery list based on meal ingredients."""

    aggregated: Dict[str, int] = {}
    for meal in draft.meals:
        for ingredient in meal.ingredients:
            key = ingredient.strip().lower()
            aggregated[key] = aggregated.get(key, 0) + 1

    return [
        {"name": ingredient, "quantity": count}
        for ingredient, count in sorted(aggregated.items())
    ]


__all__ = [
    "PlanCoordinator",
    "PlanPreferences",
    "PlanGenerationCommand",
    "PlanFeedbackCommand",
    "FeedbackResult",
    "compute_week_start",
]
