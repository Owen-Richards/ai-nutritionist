"""Analytics user models.

User profiles, consent management, and PII handling for analytics.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import ConsentType


class UserConsent(BaseModel):
    """User consent preferences for data processing."""
    user_id: UUID
    consent_type: ConsentType
    granted: bool
    granted_at: datetime
    version: str = "1.0"  # Consent policy version
    source: str = "app"   # app, web, email
    
    # GDPR compliance
    legal_basis: Optional[str] = None  # consent, legitimate_interest, etc.
    can_withdraw: bool = True
    withdrawal_method: Optional[str] = None
    
    class Config:
        extra = "forbid"


class UserProfile(BaseModel):
    """User profile with PII separation."""
    
    # Non-PII behavioral data
    user_id: UUID
    created_at: datetime
    last_active_at: Optional[datetime] = None
    
    # Aggregated behavioral metrics (no PII)
    total_plans_generated: int = 0
    total_meals_logged: int = 0
    total_nudges_sent: int = 0
    total_nudges_clicked: int = 0
    
    # Subscription info (no PII)
    current_tier: Optional[str] = None
    subscription_start: Optional[datetime] = None
    ltv_usd: float = 0.0
    
    # Engagement metrics
    weekly_active_weeks: int = 0
    longest_streak_days: int = 0
    average_adherence_percent: Optional[float] = None
    
    # Preferences (anonymized)
    dietary_restrictions: List[str] = Field(default_factory=list)
    budget_tier: Optional[str] = None  # low, medium, high (anonymized)
    time_preference: Optional[str] = None  # quick, moderate, elaborate
    
    class Config:
        extra = "forbid"


class UserPII(BaseModel):
    """Separate PII storage with encryption."""
    user_id: UUID
    
    # Direct identifiers (encrypted)
    email: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    
    # Location data (hashed/anonymized)
    region: Optional[str] = None  # US, EU, etc.
    timezone: Optional[str] = None
    
    # Device information
    device_ids: List[str] = Field(default_factory=list)
    
    # Consent tracking
    consents: List[UserConsent] = Field(default_factory=list)
    
    # Data retention
    retention_until: Optional[datetime] = None
    deletion_requested: bool = False
    deletion_requested_at: Optional[datetime] = None
    
    class Config:
        extra = "forbid"
    
    def has_consent(self, consent_type: ConsentType) -> bool:
        """Check if user has granted specific consent."""
        for consent in self.consents:
            if consent.consent_type == consent_type and consent.granted:
                return True
        return False
    
    def can_process_for(self, consent_type: ConsentType) -> bool:
        """Check if we can process data for specific purpose."""
        return self.has_consent(consent_type) and not self.deletion_requested
