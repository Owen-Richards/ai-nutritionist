"""Nutrition goals entities.

Nutrition targets and dietary goal entities.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class NutritionTargets(BaseModel):
    """Daily nutrition targets for a user."""
    
    user_id: UUID
    target_calories: int
    target_protein: int  # grams
    target_carbs: int    # grams
    target_fat: int      # grams
    target_fiber: Optional[int] = None  # grams
    target_sodium: Optional[int] = None # mg
    effective_date: date
    
    class Config:
        extra = "forbid"


class DietaryGoal(BaseModel):
    """User's dietary goal entity."""
    
    goal_id: UUID
    user_id: UUID
    goal_type: str  # weight_loss, muscle_gain, maintenance, etc.
    target_value: Optional[float] = None  # target weight, etc.
    target_date: Optional[date] = None
    current_value: Optional[float] = None
    progress_percent: float = 0.0
    is_active: bool = True
    
    class Config:
        extra = "forbid"
