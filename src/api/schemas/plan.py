"""Pydantic schemas for the plan HTTP API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from services.meal_planning.models import PlanPreferences


class PlanPreferencesInput(BaseModel):
    """User-supplied preferences for generation requests."""

    diet: Optional[str] = Field(None, description="Dietary pattern, e.g. vegetarian, vegan")
    allergies: List[str] = Field(default_factory=list)
    avoid_ingredients: List[str] = Field(default_factory=list)
    budget_limit: Optional[float] = Field(None, ge=0)
    max_prep_minutes: Optional[int] = Field(None, ge=1)
    servings: Optional[int] = Field(None, ge=1)
    cuisines: List[str] = Field(default_factory=list)
    pantry_items: List[str] = Field(default_factory=list)
    calorie_target: Optional[int] = Field(None, ge=1200)
    grocery_cadence: Optional[str] = None

    def to_domain(self) -> PlanPreferences:
        return PlanPreferences(
            diet=self.diet,
            allergies=list(self.allergies),
            avoid_ingredients=list(self.avoid_ingredients),
            budget_limit=self.budget_limit,
            max_prep_minutes=self.max_prep_minutes,
            servings=self.servings,
            cuisines=list(self.cuisines),
            pantry_items=list(self.pantry_items),
            calorie_target=self.calorie_target,
            grocery_cadence=self.grocery_cadence,
        )

    def has_overrides(self) -> bool:
        payload = self.model_dump(exclude_defaults=True, exclude_none=True)
        return bool(payload)


class PlanGenerateRequest(BaseModel):
    """Payload for plan generation."""

    user_id: str = Field(..., min_length=3)
    week_start: Optional[date] = Field(None, description="Anchor week start (Monday)")
    force_new: bool = False
    preferences: PlanPreferencesInput = Field(default_factory=PlanPreferencesInput)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("context", "metadata", mode="before")
    def _default_dict(cls, value: Any) -> Dict[str, Any]:  # noqa: D401
        """Ensure optional dict fields always become dicts."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        raise ValueError("must be an object")


class PlanMeal(BaseModel):
    """Meal representation returned to clients."""

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
    tags: List[str] = Field(default_factory=list)


class GroceryItem(BaseModel):
    """Item included in the generated grocery list."""

    name: str
    quantity: int = Field(ge=1)


class PlanResponse(BaseModel):
    """Full plan payload returned from the API."""

    plan_id: str
    user_id: str
    week_start: date
    generated_at: datetime
    estimated_cost: float
    total_calories: int
    meals: List[PlanMeal]
    grocery_list: List[GroceryItem]
    metadata: Dict[str, Any]


class PlanFeedbackRequest(BaseModel):
    """Meal feedback payload."""

    user_id: str = Field(..., min_length=3)
    plan_id: str = Field(..., min_length=8)
    meal_id: str = Field(..., min_length=3)
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)")
    emoji: Optional[str] = Field(None, max_length=8)
    comment: Optional[str] = Field(None, max_length=512)
    consumed_at: Optional[datetime] = None


class PlanFeedbackResponse(BaseModel):
    """Feedback acknowledgement."""

    status: str
    action: str
    message: str


class PlanSummaryResponse(PlanResponse):
    """Alias for plan retrieval responses."""

    pass


__all__ = [
    "PlanPreferencesInput",
    "PlanGenerateRequest",
    "PlanMeal",
    "PlanResponse",
    "PlanFeedbackRequest",
    "PlanFeedbackResponse",
    "PlanSummaryResponse",
    "GroceryItem",
]
