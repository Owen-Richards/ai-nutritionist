"""
Gamification API Schemas

Pydantic schemas for widget API requests and responses with strict
JSON shape validation optimized for mobile widget consumption.

Architecture:
- AdherenceRingSchema: Progress ring display data
- StreakSchema: Streak information with motivation
- ChallengeSchema: Mini-challenge data
- GamificationSummarySchema: Complete widget response

Author: AI Nutritionist Development Team
Date: September 2025
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator

from src.models.gamification import AdherenceLevel, ChallengeType, ChallengeStatus


class AdherenceRingSchema(BaseModel):
    """Progress ring schema for widget display."""
    
    percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Adherence percentage (0-100)"
    )
    level: AdherenceLevel = Field(
        ...,
        description="Adherence performance level"
    )
    trend: str = Field(
        ...,
        pattern="^(up|down|stable)$",
        description="Adherence trend indicator"
    )
    days_tracked: int = Field(
        ...,
        ge=0,
        description="Number of days tracked"
    )
    target_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="User's target adherence percentage"
    )
    ring_color: str = Field(
        ...,
        pattern="^#[0-9A-Fa-f]{6}$",
        description="Hex color code for progress ring"
    )
    
    class Config:
        json_json_schema_extra = {
            "example": {
                "percentage": 85.5,
                "level": "high",
                "trend": "up",
                "days_tracked": 7,
                "target_percentage": 80.0,
                "ring_color": "#39C0ED"
            }
        }


class StreakSchema(BaseModel):
    """Streak information schema for motivation display."""
    
    current_count: int = Field(
        ...,
        ge=0,
        description="Current consecutive days"
    )
    best_count: int = Field(
        ...,
        ge=0,
        description="Best streak ever achieved"
    )
    milestone_reached: Optional[int] = Field(
        None,
        ge=0,
        description="Last milestone achieved"
    )
    next_milestone: int = Field(
        ...,
        ge=1,
        description="Next milestone target"
    )
    streak_type: str = Field(
        ...,
        description="Type of streak being tracked"
    )
    is_active: bool = Field(
        ...,
        description="Whether streak is active today"
    )
    motivation_message: str = Field(
        ...,
        max_length=100,
        description="Motivational message for user"
    )
    
    @validator('next_milestone')
    def next_milestone_must_be_greater_than_current(cls, v, values):
        """Validate next milestone is greater than current count."""
        if 'current_count' in values and v <= values['current_count']:
            raise ValueError('Next milestone must be greater than current count')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_count": 12,
                "best_count": 25,
                "milestone_reached": 7,
                "next_milestone": 14,
                "streak_type": "meals",
                "is_active": True,
                "motivation_message": "12 days strong! You're building momentum!"
            }
        }


class ChallengeSchema(BaseModel):
    """Mini-challenge schema for engagement."""
    
    id: UUID = Field(
        ...,
        description="Unique challenge identifier"
    )
    title: str = Field(
        ...,
        max_length=50,
        description="Challenge title for display"
    )
    description: str = Field(
        ...,
        max_length=200,
        description="Challenge description"
    )
    challenge_type: ChallengeType = Field(
        ...,
        description="Type of challenge"
    )
    status: ChallengeStatus = Field(
        ...,
        description="Current completion status"
    )
    progress: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completion progress (0.0-1.0)"
    )
    target_value: int = Field(
        ...,
        ge=1,
        description="Target value to complete challenge"
    )
    current_value: int = Field(
        ...,
        ge=0,
        description="Current progress value"
    )
    expires_at: datetime = Field(
        ...,
        description="Challenge expiration timestamp"
    )
    reward_points: int = Field(
        ...,
        ge=0,
        description="Points awarded for completion"
    )
    difficulty_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="Challenge difficulty (1-5)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Daily Goal Master",
                "description": "Complete all your meals for the day",
                "challenge_type": "daily_goal",
                "status": "in_progress",
                "progress": 0.67,
                "target_value": 3,
                "current_value": 2,
                "expires_at": "2025-09-23T23:59:59Z",
                "reward_points": 50,
                "difficulty_level": 2
            }
        }


class GamificationSummarySchema(BaseModel):
    """Complete gamification summary for widget consumption."""
    
    user_id: UUID = Field(
        ...,
        description="User identifier"
    )
    adherence_ring: AdherenceRingSchema = Field(
        ...,
        description="Progress ring data"
    )
    current_streak: StreakSchema = Field(
        ...,
        description="Current streak information"
    )
    active_challenge: Optional[ChallengeSchema] = Field(
        None,
        description="Current active challenge"
    )
    total_points: int = Field(
        ...,
        ge=0,
        description="Total gamification points"
    )
    level: int = Field(
        ...,
        ge=1,
        description="User level"
    )
    level_progress: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Progress to next level (0.0-1.0)"
    )
    last_updated: datetime = Field(
        ...,
        description="Last data update timestamp"
    )
    cache_key: str = Field(
        ...,
        description="Cache key for ETag generation"
    )
    widget_deep_link: str = Field(
        ...,
        description="Deep link to full application"
    )
    
    # Widget-optimized fields
    compact_message: str = Field(
        ...,
        max_length=50,
        description="Short message for small widgets"
    )
    primary_metric: str = Field(
        ...,
        max_length=30,
        description="Most important metric to highlight"
    )
    secondary_metrics: List[str] = Field(
        ...,
        max_items=5,
        description="Additional metrics for larger widgets"
    )
    
    @validator('secondary_metrics')
    def validate_secondary_metrics(cls, v):
        """Validate secondary metrics length."""
        for metric in v:
            if len(metric) > 30:
                raise ValueError('Secondary metrics must be 30 characters or less')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "adherence_ring": {
                    "percentage": 85.5,
                    "level": "high",
                    "trend": "up",
                    "days_tracked": 7,
                    "target_percentage": 80.0,
                    "ring_color": "#39C0ED"
                },
                "current_streak": {
                    "current_count": 12,
                    "best_count": 25,
                    "milestone_reached": 7,
                    "next_milestone": 14,
                    "streak_type": "meals",
                    "is_active": True,
                    "motivation_message": "12 days strong! You're building momentum!"
                },
                "active_challenge": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Daily Goal Master",
                    "description": "Complete all your meals for the day",
                    "challenge_type": "daily_goal",
                    "status": "in_progress",
                    "progress": 0.67,
                    "target_value": 3,
                    "current_value": 2,
                    "expires_at": "2025-09-23T23:59:59Z",
                    "reward_points": 50,
                    "difficulty_level": 2
                },
                "total_points": 2750,
                "level": 3,
                "level_progress": 0.75,
                "last_updated": "2025-09-22T14:30:00Z",
                "cache_key": "abc123def456",
                "widget_deep_link": "ainutritionist://dashboard?user_id=123e4567-e89b-12d3-a456-426614174000",
                "compact_message": "86% adherence • 12 day streak",
                "primary_metric": "86% adherence",
                "secondary_metrics": [
                    "12 day streak",
                    "Level 3",
                    "2750 points"
                ]
            }
        }


class ErrorSchema(BaseModel):
    """Standard error response schema."""
    
    error: str = Field(
        ...,
        description="Error type identifier"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[dict] = Field(
        None,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        ...,
        description="Error timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "user_not_found",
                "message": "User with the specified ID was not found",
                "details": {"user_id": "123e4567-e89b-12d3-a456-426614174000"},
                "timestamp": "2025-09-22T14:30:00Z"
            }
        }


# Widget-specific schemas for contract testing
class WidgetContractSchema(BaseModel):
    """Schema for widget contract validation."""
    
    schema_version: str = Field(
        default="1.0",
        description="Widget schema version"
    )
    required_fields: List[str] = Field(
        ...,
        description="Required fields for widget display"
    )
    optional_fields: List[str] = Field(
        default=[],
        description="Optional fields for enhanced display"
    )
    cache_requirements: dict = Field(
        ...,
        description="Caching requirements and headers"
    )
    deep_link_format: str = Field(
        ...,
        description="Expected deep link URL format"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "schema_version": "1.0",
                "required_fields": [
                    "user_id",
                    "adherence_ring",
                    "current_streak",
                    "compact_message",
                    "widget_deep_link"
                ],
                "optional_fields": [
                    "active_challenge",
                    "secondary_metrics"
                ],
                "cache_requirements": {
                    "etag_required": True,
                    "cache_control_required": True,
                    "min_ttl_minutes": 5,
                    "max_ttl_minutes": 15
                },
                "deep_link_format": "ainutritionist://dashboard?user_id={user_id}"
            }
        }
