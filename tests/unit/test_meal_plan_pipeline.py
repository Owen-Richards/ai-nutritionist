"""Unit tests for the meal plan pipeline."""

from __future__ import annotations

from datetime import date

from services.meal_planning.data_store import (
    InMemoryPlanDataStore,
    PantryItemRecord,
    UserPreferenceRecord,
)
from services.meal_planning.ml_logging import FeatureLogger
from services.meal_planning.pipeline import MealPlanPipeline
from services.meal_planning.plan_coordinator import PlanCoordinator
from services.meal_planning.repository import InMemoryPlanRepository
from services.meal_planning.rule_engine import RuleBasedMealPlanEngine
from services.meal_planning.models import PlanPreferences


def _build_pipeline() -> tuple[MealPlanPipeline, InMemoryPlanDataStore, FeatureLogger]:
    repository = InMemoryPlanRepository()
    engine = RuleBasedMealPlanEngine()
    coordinator = PlanCoordinator(repository=repository, engine=engine)
    data_store = InMemoryPlanDataStore()
    feature_logger = FeatureLogger()
    pipeline = MealPlanPipeline(coordinator=coordinator, data_store=data_store, feature_logger=feature_logger)
    return pipeline, data_store, feature_logger


def test_pipeline_generates_vegan_plan() -> None:
    pipeline, data_store, feature_logger = _build_pipeline()
    data_store.register_preferences(UserPreferenceRecord(user_id="vegan-user", diet="vegan"))

    plan = pipeline.generate_plan(user_id="vegan-user")

    assert all("vegan" in meal.tags for meal in plan.meals), "All meals should respect vegan diet"
    assert feature_logger.get_plan_records(), "Feature logging should capture plan generation"


def test_pipeline_respects_max_prep_minutes() -> None:
    pipeline, data_store, _ = _build_pipeline()
    data_store.register_preferences(
        UserPreferenceRecord(
            user_id="busy-user",
            diet="pescatarian",
            max_prep_minutes=15,
        )
    )

    plan = pipeline.generate_plan(user_id="busy-user")

    assert all(meal.prep_minutes <= 15 for meal in plan.meals), "Prep times should respect constraint"


def test_pipeline_merges_overrides() -> None:
    pipeline, data_store, _ = _build_pipeline()
    data_store.register_preferences(
        UserPreferenceRecord(
            user_id="budget-user",
            budget_weekly=90.0,
            pantry_items=["chickpeas", "brown rice"],
        )
    )

    overrides = PlanPreferences(budget_limit=75.0, max_prep_minutes=20)
    plan = pipeline.generate_plan(user_id="budget-user", overrides=overrides, week_start=date(2025, 9, 15))

    notes = plan.metadata.get("notes", [])
    assert any("budget" in note.lower() for note in notes)
    assert plan.week_start.isoformat() == "2025-09-15"


def test_pipeline_produces_grocery_list_counts() -> None:
    pipeline, data_store, _ = _build_pipeline()
    data_store.register_pantry_items(
        "cook",
        [PantryItemRecord(user_id="cook", name="olive oil")],
    )

    plan = pipeline.generate_plan(user_id="cook")

    aggregated = {item["name"]: item["quantity"] for item in plan.grocery_list}
    assert aggregated, "Grocery list should not be empty"
    # Ingredients appear multiple times across meals; ensure aggregation occurs
    assert any(quantity > 1 for quantity in aggregated.values())
