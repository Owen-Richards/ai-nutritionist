from datetime import UTC, datetime, date
from typing import Dict

from services.meal_planning.pipeline import MealPlanPipeline
from services.meal_planning.optimizer import SmartSwapEngine
from services.meal_planning.repository import GeneratedMealPlan, MealEntry
from services.meal_planning.models import PlanPreferences
from services.personalization.goals import HealthGoalsService


class _DummyCoordinator:
    def generate_plan(self, *args, **kwargs):  # pragma: no cover - not used in tests
        raise NotImplementedError


class _DummyFeatureLogger:
    def log_plan_generation(self, plan, preferences):  # pragma: no cover - not used
        pass


class _DummyStore:
    def __init__(self, plan: GeneratedMealPlan) -> None:
        self._plan = plan

    def get_user_preferences(self, user_id: str) -> PlanPreferences:
        return PlanPreferences()

    def save_generated_plan(self, plan: GeneratedMealPlan) -> None:
        self._plan = plan

    def list_recent_plans(self, user_id: str, limit: int = 5):
        return [self._plan]


def _sample_plan() -> GeneratedMealPlan:
    meal = MealEntry(
        meal_id="meal-1",
        day="monday",
        meal_type="dinner",
        title="Peanut stir fry",
        description="Savory stir fry",
        ingredients=["peanut oil", "tofu", "vegetables"],
        calories=520,
        prep_minutes=30,
        macros={"protein": 28.0},
        cost=9.5,
        tags=["vegetarian"],
    )
    return GeneratedMealPlan(
        plan_id="plan-1",
        user_id="user-1",
        week_start=date(2025, 1, 6),
        generated_at=datetime(2025, 1, 1, 8, tzinfo=UTC),
        meals=[meal],
        estimated_cost=65.0,
        total_calories=1800,
        grocery_list=[],
        metadata={"preferences": {"max_prep_minutes": 20, "allergies": ["peanut"], "budget_limit": 7.0}},
    )


def test_suggest_swaps_respects_constraints() -> None:
    plan = _sample_plan()
    pipeline = MealPlanPipeline(
        coordinator=_DummyCoordinator(),
        data_store=_DummyStore(plan),
        feature_logger=_DummyFeatureLogger(),
        swap_engine=SmartSwapEngine(),
    )

    suggestions = pipeline.suggest_swaps(
        "user-1",
        meal_id="meal-1",
        constraints={"max_prep_minutes": 15, "budget_limit": 6.0, "allergies": ["peanut"]},
    )

    badges = {item.get("badge") for item in suggestions}
    assert "quick" in badges
    assert "allergen-safe" in badges
    assert any(s.get("deep_link_path", "").startswith("/plans/") for s in suggestions)


def test_goals_service_tracks_and_recovers_streaks() -> None:
    service = HealthGoalsService()
    base = datetime(2025, 2, 1, 8)

    state = service.update_daily_streak("user-7", completed=True, reference_date=base)
    assert state.current == 1

    state = service.update_daily_streak("user-7", completed=True, reference_date=base.replace(day=2))
    assert state.current == 2
    assert service.celebrate_small_win("user-7") is not None

    service.update_daily_streak("user-7", completed=False, reference_date=base.replace(day=4))
    recovery = service.generate_recovery_message("user-7", reference_date=base.replace(day=5))
    assert "restart" in recovery.lower() or "start" in recovery.lower()

    summary = service.get_streak_state("user-7")
    assert summary.current == 0
