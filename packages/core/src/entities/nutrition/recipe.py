"""Recipe entities.

Recipe, ingredient, and nutrition information entities.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NutritionInfo(BaseModel):
    """Nutrition information per serving."""
    
    calories: int
    protein: int  # grams
    carbs: int    # grams
    fat: int      # grams
    fiber: Optional[int] = None  # grams
    sugar: Optional[int] = None  # grams
    sodium: Optional[int] = None # mg
    
    class Config:
        extra = "forbid"


class Ingredient(BaseModel):
    """Recipe ingredient entity."""
    
    ingredient_id: UUID
    name: str
    amount: float
    unit: str  # cups, tbsp, oz, etc.
    category: str  # protein, vegetable, grain, etc.
    estimated_cost: float
    
    class Config:
        extra = "forbid"


class Recipe(BaseModel):
    """Recipe entity."""
    
    recipe_id: UUID
    name: str
    description: Optional[str] = None
    ingredients: List[Ingredient] = Field(default_factory=list)
    instructions: List[str] = Field(default_factory=list)
    servings: int
    prep_time_minutes: int
    cook_time_minutes: int
    nutrition_per_serving: NutritionInfo
    difficulty: str = "medium"  # easy, medium, hard
    cuisine_type: str = "american"
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "forbid"
