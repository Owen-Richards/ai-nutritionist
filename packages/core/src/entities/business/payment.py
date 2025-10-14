"""Payment entities.

Payment, invoice, and transaction entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Payment(BaseModel):
    """Payment entity."""
    
    payment_id: UUID
    user_id: UUID
    subscription_id: Optional[UUID] = None
    amount: float
    currency: str = "USD"
    payment_method: str  # card, paypal, etc.
    status: str  # pending, completed, failed, refunded
    processed_at: Optional[datetime] = None
    gateway_transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    
    class Config:
        extra = "forbid"


class Invoice(BaseModel):
    """Invoice entity."""
    
    invoice_id: UUID
    user_id: UUID
    subscription_id: UUID
    amount: float
    tax_amount: float = 0.0
    total_amount: float
    due_date: datetime
    paid_date: Optional[datetime] = None
    status: str  # draft, sent, paid, overdue, cancelled
    
    class Config:
        extra = "forbid"


class Transaction(BaseModel):
    """Financial transaction entity."""
    
    transaction_id: UUID
    user_id: UUID
    type: str  # charge, refund, chargeback
    amount: float
    currency: str = "USD"
    description: str
    created_at: datetime
    reference_id: Optional[str] = None  # External reference
    
    class Config:
        extra = "forbid"
