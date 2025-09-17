"""Unit tests for the plan HTTP API."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from api.dependencies import get_plan_coordinator, get_plan_pipeline
from services.meal_planning.plan_coordinator import PlanCoordinator
from services.meal_planning.repository import InMemoryPlanRepository
from services.meal_planning.rule_engine import RuleBasedMealPlanEngine
from services.meal_planning.pipeline import MealPlanPipeline
from services.meal_planning.data_store import InMemoryPlanDataStore
from services.meal_planning.ml_logging import FeatureLogger


class CountingEngine(RuleBasedMealPlanEngine):
    """Rule engine that tracks generation calls."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    def generate(self, command):  # type: ignore[override]
        self.call_count += 1
        return super().generate(command)


@pytest.fixture()
def api_client() -> TestClient:
    app = create_app()
    engine = CountingEngine()
    repository = InMemoryPlanRepository()
    coordinator = PlanCoordinator(repository=repository, engine=engine)
    data_store = InMemoryPlanDataStore()
    feature_logger = FeatureLogger()
    pipeline = MealPlanPipeline(coordinator=coordinator, data_store=data_store, feature_logger=feature_logger)

    def override_coordinator() -> PlanCoordinator:
        return coordinator

    def override_pipeline() -> MealPlanPipeline:
        return pipeline

    app.dependency_overrides[get_plan_coordinator] = override_coordinator
    app.dependency_overrides[get_plan_pipeline] = override_pipeline

    with TestClient(app) as client:
        client._engine = engine  # type: ignore[attr-defined]
        client._pipeline = pipeline  # type: ignore[attr-defined]
        client._data_store = data_store  # type: ignore[attr-defined]
        client._feature_logger = feature_logger  # type: ignore[attr-defined]
        yield client


def test_generate_plan_with_idempotency_key(api_client: TestClient) -> None:
    payload = {
        "user_id": "user-123",
        "week_start": date(2025, 9, 15).isoformat(),
        "preferences": {"diet": "vegetarian", "max_prep_minutes": 25},
    }

    response = api_client.post(
        "/v1/plan/generate",
        json=payload,
        headers={"X-Idempotency-Key": "abc123"},
    )
    assert response.status_code == 201
    body = response.json()
    plan_id = body["plan_id"]
    assert api_client._engine.call_count == 1  # type: ignore[attr-defined]
    assert body["grocery_list"], "grocery list should be returned"

    replay = api_client.post(
        "/v1/plan/generate",
        json=payload,
        headers={"X-Idempotency-Key": "abc123"},
    )
    assert replay.status_code == 201
    assert replay.json()["plan_id"] == plan_id
    assert api_client._engine.call_count == 1  # type: ignore[attr-defined]


def test_get_current_plan_returns_existing_plan(api_client: TestClient) -> None:
    payload = {"user_id": "user-321", "force_new": True}
    create = api_client.post("/v1/plan/generate", json=payload)
    assert create.status_code == 201
    plan_id = create.json()["plan_id"]

    fetch = api_client.get("/v1/plan/current", params={"user_id": "user-321"})
    assert fetch.status_code == 200
    body = fetch.json()
    assert body["plan_id"] == plan_id
    assert len(body["meals"]) == 21
    assert all("tags" in meal for meal in body["meals"])  # ensure tags returned


def test_submit_feedback_validates_rating(api_client: TestClient) -> None:
    payload = {"user_id": "feedback-user", "force_new": True}
    create = api_client.post("/v1/plan/generate", json=payload)
    plan = create.json()

    good_feedback = {
        "user_id": "feedback-user",
        "plan_id": plan["plan_id"],
        "meal_id": plan["meals"][0]["meal_id"],
        "rating": 5,
        "comment": "Loved it",
    }
    ok = api_client.post("/v1/plan/feedback", json=good_feedback)
    assert ok.status_code == 202
    assert ok.json()["action"] == "reinforce"

    bad_feedback = dict(good_feedback)
    bad_feedback["rating"] = 7
    bad = api_client.post("/v1/plan/feedback", json=bad_feedback)
    assert bad.status_code == 422  # Pydantic validation error
    response_detail = bad.json()["detail"]
    # Check that the error mentions rating validation
    assert any("rating" in str(error).lower() for error in response_detail)
