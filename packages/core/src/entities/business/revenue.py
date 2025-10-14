"""Revenue entities.

Revenue stream and affiliate commission entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RevenueStream(BaseModel):
    """Revenue stream entity."""
    
    stream_id: UUID
    source: str  # subscription, affiliate, marketplace, etc.
    amount: float
    currency: str = "USD"
    user_id: Optional[UUID] = None
    created_at: datetime
    description: str
    
    class Config:
        extra = "forbid"


class AffiliateCommission(BaseModel):
    """Affiliate commission entity."""
    
    commission_id: UUID
    user_id: UUID
    partner: str  # Amazon, grocery store, etc.
    product_id: str
    commission_rate: float  # percentage
    sale_amount: float
    commission_amount: float
    sale_date: datetime
    paid_date: Optional[datetime] = None
    status: str  # pending, paid, cancelled
    
    class Config:
        extra = "forbid"
