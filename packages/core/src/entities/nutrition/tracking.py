"""Nutrition tracking entities.

Food entry and nutrition log entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class FoodEntry(BaseModel):
    """Individual food entry entity."""
    
    entry_id: UUID
    user_id: UUID
    food_name: str
    quantity: float
    unit: str
    calories: int
    protein: int  # grams
    carbs: int    # grams
    fat: int      # grams
    logged_at: datetime
    meal_type: str  # breakfast, lunch, dinner, snack
    
    class Config:
        extra = "forbid"


class NutritionLog(BaseModel):
    """Daily nutrition log entity."""
    
    log_id: UUID
    user_id: UUID
    date: datetime
    total_calories: int
    total_protein: int
    total_carbs: int
    total_fat: int
    food_entries: list[UUID] = []  # References to FoodEntry IDs
    notes: Optional[str] = None
    
    class Config:
        extra = "forbid"
