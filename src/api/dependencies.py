"""Dependency wiring for the HTTP API."""

from __future__ import annotations

import os
from functools import lru_cache

from services.meal_planning.plan_coordinator import PlanCoordinator
from services.meal_planning.repository import InMemoryPlanRepository
from services.meal_planning.rule_engine import RuleBasedMealPlanEngine
from services.meal_planning.pipeline import MealPlanPipeline
from services.meal_planning.data_store import InMemoryPlanDataStore
from services.meal_planning.ml_logging import FeatureLogger

_PLAN_REPOSITORY = InMemoryPlanRepository()
_DATA_STORE = InMemoryPlanDataStore()
_FEATURE_LOGGER = FeatureLogger()


@lru_cache(maxsize=1)
def _build_coordinator() -> PlanCoordinator:
    ttl_hours = int(os.getenv("PLAN_IDEMPOTENCY_TTL_HOURS", "24"))
    engine = RuleBasedMealPlanEngine()
    return PlanCoordinator(repository=_PLAN_REPOSITORY, engine=engine, idempotency_ttl_hours=ttl_hours)


def get_plan_coordinator() -> PlanCoordinator:
    """Primary dependency for plan routes."""

    return _build_coordinator()


@lru_cache(maxsize=1)
def _build_pipeline() -> MealPlanPipeline:
    return MealPlanPipeline(
        coordinator=get_plan_coordinator(),
        data_store=_DATA_STORE,
        feature_logger=_FEATURE_LOGGER,
    )


def get_plan_pipeline() -> MealPlanPipeline:
    return _build_pipeline()


def get_plan_data_store() -> InMemoryPlanDataStore:
    return _DATA_STORE


def get_feature_logger() -> FeatureLogger:
    return _FEATURE_LOGGER


__all__ = ["get_plan_coordinator", "get_plan_pipeline", "get_plan_data_store", "get_feature_logger"]
