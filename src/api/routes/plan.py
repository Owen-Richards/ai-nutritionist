"""Plan API routes."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.services.meal_planning.plan_coordinator import (
    FeedbackResult,
    PlanCoordinator,
    PlanFeedbackCommand,
)
from src.services.meal_planning.repository import GeneratedMealPlan
from src.services.meal_planning.pipeline import MealPlanPipeline

from src.api.dependencies import get_plan_coordinator, get_plan_pipeline
from src.api.schemas.plan import (
    PlanFeedbackRequest,
    PlanFeedbackResponse,
    PlanGenerateRequest,
    PlanResponse,
    PlanSummaryResponse,
)

router = APIRouter(prefix="/v1/plan", tags=["plan"])


@router.post(
    "/generate",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalised weekly meal plan",
)
def generate_plan(
    payload: PlanGenerateRequest,
    pipeline: MealPlanPipeline = Depends(get_plan_pipeline),
    coordinator: PlanCoordinator = Depends(get_plan_coordinator),
    idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
) -> PlanResponse:
    """Create or retrieve a weekly plan for the supplied user."""

    overrides = payload.preferences.to_domain() if payload.preferences.has_overrides() else None
    plan = pipeline.generate_plan(
        user_id=payload.user_id,
        overrides=overrides,
        week_start=payload.week_start,
        force_new=payload.force_new,
        context=payload.context,
        metadata=payload.metadata,
        idempotency_key=idempotency_key,
    )
    return _to_plan_response(plan)


@router.get(
    "/current",
    response_model=PlanSummaryResponse,
    summary="Fetch the current (or requested week) meal plan",
)
def get_current_plan(
    user_id: str,
    week_start: Optional[date] = None,
    coordinator: PlanCoordinator = Depends(get_plan_coordinator),
) -> PlanSummaryResponse:
    """Return the persisted plan for the user."""

    plan = coordinator.get_plan(user_id=user_id, week_start=week_start)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return _to_plan_response(plan)


@router.post(
    "/feedback",
    response_model=PlanFeedbackResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit feedback for a meal inside a plan",
)
def submit_feedback(
    payload: PlanFeedbackRequest,
    coordinator: PlanCoordinator = Depends(get_plan_coordinator),
) -> PlanFeedbackResponse:
    """Capture user reaction to a specific meal."""

    command = PlanFeedbackCommand(
        user_id=payload.user_id,
        plan_id=payload.plan_id,
        meal_id=payload.meal_id,
        rating=payload.rating,
        emoji=payload.emoji,
        comment=payload.comment,
        consumed_at=payload.consumed_at,
    )
    try:
        result = coordinator.record_feedback(command)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_feedback_response(result)


def _to_plan_response(plan: GeneratedMealPlan) -> PlanResponse:
    return PlanResponse(
        plan_id=plan.plan_id,
        user_id=plan.user_id,
        week_start=plan.week_start,
        generated_at=plan.generated_at,
        estimated_cost=plan.estimated_cost,
        total_calories=plan.total_calories,
        meals=[
            {
                "meal_id": meal.meal_id,
                "day": meal.day,
                "meal_type": meal.meal_type,
                "title": meal.title,
                "description": meal.description,
                "ingredients": meal.ingredients,
                "calories": meal.calories,
                "prep_minutes": meal.prep_minutes,
                "macros": meal.macros,
                "cost": meal.cost,
                "tags": meal.tags,
            }
            for meal in plan.meals
        ],
        grocery_list=[{"name": item["name"], "quantity": item["quantity"]} for item in plan.grocery_list],
        metadata=plan.metadata,
    )


def _to_feedback_response(result: FeedbackResult) -> PlanFeedbackResponse:
    return PlanFeedbackResponse(status=result.status, action=result.action, message=result.message)


__all__ = ["router"]
