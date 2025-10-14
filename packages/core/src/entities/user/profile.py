"""User profile entities.

Core user profile and preference entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """User profile entity."""
    
    user_id: UUID
    email: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    class Config:
        extra = "forbid"


class UserPreferences(BaseModel):
    """User dietary and lifestyle preferences."""
    
    user_id: UUID
    dietary_restrictions: List[str] = Field(default_factory=list)
    allergens: List[str] = Field(default_factory=list)
    cuisine_preferences: List[str] = Field(default_factory=list)
    budget_tier: str = "medium"  # low, medium, high
    time_preference: str = "moderate"  # quick, moderate, elaborate
    
    class Config:
        extra = "forbid"


class UserGoals(BaseModel):
    """User health and nutrition goals."""
    
    user_id: UUID
    primary_goal: str  # weight_loss, muscle_gain, maintain, etc.
    target_calories: Optional[int] = None
    target_protein: Optional[int] = None
    target_carbs: Optional[int] = None
    target_fat: Optional[int] = None
    activity_level: str = "moderate"  # sedentary, light, moderate, active, very_active
    
    class Config:
        extra = "forbid"
