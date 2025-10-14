"""User identity entities.

User identity and authentication related entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserIdentity(BaseModel):
    """User identity entity."""
    
    user_id: UUID
    email: str
    phone: Optional[str] = None
    verified_email: bool = False
    verified_phone: bool = False
    
    class Config:
        extra = "forbid"


class UserSettings(BaseModel):
    """User application settings."""
    
    user_id: UUID
    timezone: str = "UTC"
    language: str = "en"
    notifications_enabled: bool = True
    sms_enabled: bool = False
    email_enabled: bool = True
    
    class Config:
        extra = "forbid"
