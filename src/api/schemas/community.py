"""API schemas for community endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from services.community.models import CrewType, PulseMetricType, ReflectionType


class JoinCrewRequest(BaseModel):
    """Request payload for joining a crew."""
    
    user_id: str = Field(..., min_length=3, description="User identifier")
    crew_id: str = Field(..., min_length=8, description="Crew identifier")
    privacy_consent: Dict[str, bool] = Field(
        default_factory=lambda: {
            "share_progress": True,
            "share_reflections": False,
            "receive_challenges": True
        },
        description="Privacy consent settings"
    )
    notifications_enabled: bool = Field(True, description="Enable SMS notifications")
    user_name: str = Field(..., min_length=1, max_length=50, description="User display name")


class JoinCrewResponse(BaseModel):
    """Response for crew join operation."""
    
    success: bool
    message: str
    member_id: Optional[str] = None
    welcome_sms: Optional[str] = None
    crew_info: Optional[Dict[str, str]] = None


class SubmitReflectionRequest(BaseModel):
    """Request payload for submitting a reflection."""
    
    user_id: str = Field(..., min_length=3, description="User identifier")
    crew_id: str = Field(..., min_length=8, description="Crew identifier")
    content: str = Field(..., min_length=1, max_length=1000, description="Reflection content")
    reflection_type: ReflectionType = Field(..., description="Type of reflection")
    mood_score: Optional[int] = Field(None, ge=1, le=5, description="Mood rating 1-5")
    progress_rating: Optional[int] = Field(None, ge=1, le=5, description="Progress rating 1-5")
    is_anonymous: bool = Field(False, description="Submit as anonymous reflection")
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate reflection content."""
        if not v.strip():
            raise ValueError("Reflection content cannot be empty or whitespace only")
        return v.strip()


class SubmitReflectionResponse(BaseModel):
    """Response for reflection submission."""
    
    success: bool
    message: str
    reflection_id: Optional[str] = None
    pii_redacted: bool = False


class PulseMetricSubmission(BaseModel):
    """Individual pulse metric submission."""
    
    metric_type: PulseMetricType
    value: float = Field(..., ge=1.0, le=5.0, description="Metric value on 1-5 scale")


class SubmitPulseRequest(BaseModel):
    """Request payload for submitting pulse metrics."""
    
    user_id: str = Field(..., min_length=3, description="User identifier") 
    metrics: List[PulseMetricSubmission] = Field(..., min_length=1, description="Pulse metrics")


class SubmitPulseResponse(BaseModel):
    """Response for pulse submission."""
    
    success: bool
    message: str
    metrics_recorded: int


class CrewMemberInfo(BaseModel):
    """Information about a crew member (anonymized)."""
    
    member_since: datetime
    is_active: bool
    contributions: int  # Number of reflections/metrics


class CrewPulseMetrics(BaseModel):
    """Aggregated metrics for crew pulse."""
    
    metric_type: PulseMetricType
    average: float
    median: float
    count: int
    trend: str = "stable"  # "improving", "declining", "stable"


class CrewPulseResponse(BaseModel):
    """Response for crew pulse data."""
    
    crew_id: str
    pulse_date: datetime
    total_active_members: int
    engagement_score: float
    metrics: List[CrewPulseMetrics]
    recent_reflections: List[str]  # Anonymized excerpts
    challenge_completion_rate: float
    anonymization_applied: bool
    data_suppressed: bool = False
    suppression_reason: Optional[str] = None


class CrewSummary(BaseModel):
    """Summary information about a crew."""
    
    crew_id: str
    name: str
    crew_type: CrewType
    description: str
    member_count: int
    max_members: int
    is_active: bool
    created_at: datetime


__all__ = [
    "JoinCrewRequest",
    "JoinCrewResponse",
    "SubmitReflectionRequest", 
    "SubmitReflectionResponse",
    "PulseMetricSubmission",
    "SubmitPulseRequest",
    "SubmitPulseResponse",
    "CrewMemberInfo",
    "CrewPulseMetrics",
    "CrewPulseResponse",
    "CrewSummary",
]
