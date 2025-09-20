"""Community domain models for crews, reflections, and pulse data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class CrewType(Enum):
    """Types of nutrition crews users can join."""
    
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    HEALTHY_HABITS = "healthy_habits"
    BUDGET_COOKING = "budget_cooking"
    PLANT_BASED = "plant_based"
    MEAL_PREP = "meal_prep"
    NUTRITION_FOCUSED = "nutrition_focused"


class MembershipStatus(Enum):
    """Status of crew membership."""
    
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    LEFT = "left"
    BANNED = "banned"


class PulseMetricType(Enum):
    """Types of metrics tracked in crew pulses."""
    
    ADHERENCE = "adherence"
    ENERGY_LEVEL = "energy_level"
    SATISFACTION = "satisfaction"
    PROGRESS = "progress"
    MOTIVATION = "motivation"


class ReflectionType(Enum):
    """Types of reflections users can submit."""
    
    DAILY_CHECK_IN = "daily_check_in"
    WEEKLY_REFLECTION = "weekly_reflection"
    CHALLENGE_COMPLETION = "challenge_completion"
    MILESTONE_CELEBRATION = "milestone_celebration"


@dataclass(frozen=True)
class Crew:
    """Represents a nutrition crew/community group."""
    
    crew_id: str
    name: str
    crew_type: CrewType
    description: str
    cohort_key: str  # For grouping crews in same time period
    created_at: datetime
    max_members: int = 50
    is_active: bool = True
    privacy_settings: Dict[str, bool] = field(default_factory=lambda: {
        "allow_member_visibility": True,
        "allow_aggregate_sharing": True,
        "require_anonymization": True
    })


@dataclass
class CrewMember:
    """Represents a user's membership in a crew."""
    
    member_id: str
    crew_id: str
    user_id: str
    status: MembershipStatus
    joined_at: datetime
    notifications_enabled: bool = True
    privacy_consent: bool = True
    consent_timestamp: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate member data on creation."""
        if not self.member_id:
            object.__setattr__(self, 'member_id', uuid4().hex)


@dataclass
class Reflection:
    """User reflection/check-in within a crew context."""
    
    reflection_id: str
    user_id: str
    crew_id: str
    reflection_type: ReflectionType
    content: str
    mood_score: Optional[int] = None  # 1-5 scale
    progress_rating: Optional[int] = None  # 1-5 scale
    created_at: datetime = field(default_factory=datetime.now)
    is_anonymous: bool = False
    pii_redacted: bool = False
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate reflection data."""
        if not self.reflection_id:
            self.reflection_id = uuid4().hex
        
        # Validate mood and progress scores
        if self.mood_score is not None and not (1 <= self.mood_score <= 5):
            raise ValueError("Mood score must be between 1 and 5")
        if self.progress_rating is not None and not (1 <= self.progress_rating <= 5):
            raise ValueError("Progress rating must be between 1 and 5")
        
        # Content length validation
        if len(self.content.strip()) == 0:
            raise ValueError("Reflection content cannot be empty")
        if len(self.content) > 1000:
            raise ValueError("Reflection content must be under 1000 characters")


@dataclass
class PulseMetric:
    """Individual metric data point for crew pulse."""
    
    metric_type: PulseMetricType
    value: float
    user_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_anonymous: bool = True


@dataclass
class CrewPulse:
    """Aggregated crew health and engagement metrics."""
    
    crew_id: str
    pulse_date: datetime
    total_active_members: int
    metrics: Dict[PulseMetricType, Dict[str, float]]  # metric_type -> {avg, median, count}
    engagement_score: float  # 0-100 composite score
    recent_reflections: List[str]  # Anonymized reflection excerpts
    challenge_completion_rate: float
    anonymization_applied: bool = True
    
    def __post_init__(self) -> None:
        """Validate pulse data meets privacy requirements."""
        if self.total_active_members < 5 and not self.anonymization_applied:
            raise ValueError("Crews with <5 members must have anonymization applied")


@dataclass
class Challenge:
    """Community challenge within a crew."""
    
    challenge_id: str
    crew_id: str
    title: str
    description: str
    challenge_type: str  # "daily", "weekly", "milestone"
    start_date: datetime
    end_date: datetime
    participation_count: int = 0
    completion_count: int = 0
    is_active: bool = True
    
    def __post_init__(self) -> None:
        """Validate challenge data."""
        if not self.challenge_id:
            self.challenge_id = uuid4().hex
        
        if self.end_date <= self.start_date:
            raise ValueError("Challenge end date must be after start date")


__all__ = [
    "CrewType",
    "PulseMetricType", 
    "ReflectionType",
    "Crew",
    "CrewMember",
    "Reflection",
    "PulseMetric",
    "CrewPulse",
    "Challenge",
]
