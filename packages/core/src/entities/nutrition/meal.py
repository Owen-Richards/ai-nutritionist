"""Meal entities.

Core meal, meal plan, and day plan entities.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Meal(BaseModel):
    """Individual meal entity."""
    
    meal_id: UUID
    name: str
    meal_type: str  # breakfast, lunch, dinner, snack
    recipes: List[UUID] = Field(default_factory=list)
    total_calories: int
    total_protein: int
    total_carbs: int
    total_fat: int
    estimated_cost: float
    prep_time_minutes: int
    
    class Config:
        extra = "forbid"


class DayPlan(BaseModel):
    """Single day meal plan entity."""
    
    day_plan_id: UUID
    user_id: UUID
    date: date
    meals: List[Meal] = Field(default_factory=list)
    total_calories: int
    total_protein: int
    total_carbs: int
    total_fat: int
    total_cost: float
    
    class Config:
        extra = "forbid"


class MealPlan(BaseModel):
    """Multi-day meal plan entity."""
    
    plan_id: UUID
    user_id: UUID
    name: str
    start_date: date
    end_date: date
    day_plans: List[DayPlan] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    class Config:
        extra = "forbid"
