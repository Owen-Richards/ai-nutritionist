"""User authentication entities.

User authentication and session management entities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserAuth(BaseModel):
    """User authentication entity."""
    
    user_id: UUID
    password_hash: str
    salt: str
    last_login: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    class Config:
        extra = "forbid"


class UserSession(BaseModel):
    """User session entity."""
    
    session_id: UUID
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    is_active: bool = True
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    
    class Config:
        extra = "forbid"
