"""Subscription entities.

Subscription, billing, and plan entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SubscriptionPlan(BaseModel):
    """Subscription plan entity."""
    
    plan_id: UUID
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    features: list[str] = []
    max_meal_plans: Optional[int] = None
    max_recipes: Optional[int] = None
    priority_support: bool = False
    is_active: bool = True
    
    class Config:
        extra = "forbid"


class BillingCycle(BaseModel):
    """Billing cycle entity."""
    
    cycle_id: UUID
    subscription_id: UUID
    start_date: datetime
    end_date: datetime
    amount: float
    status: str  # pending, paid, failed, refunded
    paid_at: Optional[datetime] = None
    
    class Config:
        extra = "forbid"


class Subscription(BaseModel):
    """User subscription entity."""
    
    subscription_id: UUID
    user_id: UUID
    plan_id: UUID
    status: str  # active, cancelled, expired, suspended
    started_at: datetime
    expires_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    auto_renew: bool = True
    current_period_start: datetime
    current_period_end: datetime
    
    class Config:
        extra = "forbid"
