"""
Gamification Domain Models

Enterprise-grade domain models for widget gamification features including
adherence tracking, streak management, and mini-challenges.

Architecture:
- AdherenceRing: Progress ring showing daily/weekly adherence percentage
- Streak: Current streak count with milestone tracking
- Challenge: Mini-challenges with completion status
- GamificationSummary: Consolidated widget data model

Author: AI Nutritionist Development Team
Date: September 2025
"""

from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID


class AdherenceLevel(Enum):
    """Adherence performance levels for visual indicators."""
    LOW = "low"          # 0-40%
    MEDIUM = "medium"    # 41-70%
    HIGH = "high"        # 71-89%
    EXCELLENT = "excellent"  # 90-100%


class ChallengeType(Enum):
    """Types of mini-challenges for user engagement."""
    DAILY_GOAL = "daily_goal"
    HYDRATION = "hydration"
    MEAL_PREP = "meal_prep"
    VARIETY = "variety"
    MINDFUL_EATING = "mindful_eating"


class ChallengeStatus(Enum):
    """Challenge completion status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class AdherenceRing:
    """
    Progress ring data for widget display.
    
    Represents user's adherence as a visual ring with percentage,
    color coding, and trend information.
    """
    percentage: float  # 0.0 - 100.0
    level: AdherenceLevel
    trend: str  # "up", "down", "stable"
    days_tracked: int
    target_percentage: float  # User's personal goal
    ring_color: str  # Hex color code for widget
    
    def __post_init__(self):
        """Validate adherence ring data."""
        if not 0.0 <= self.percentage <= 100.0:
            raise ValueError("Percentage must be between 0 and 100")
        if not 0.0 <= self.target_percentage <= 100.0:
            raise ValueError("Target percentage must be between 0 and 100")
        if self.days_tracked < 0:
            raise ValueError("Days tracked cannot be negative")
        if self.trend not in ["up", "down", "stable"]:
            raise ValueError("Trend must be 'up', 'down', or 'stable'")


@dataclass(frozen=True)
class Streak:
    """
    Current streak information for gamification.
    
    Tracks consecutive days of successful adherence with
    milestone achievements and motivation messaging.
    """
    current_count: int
    best_count: int
    milestone_reached: Optional[int]  # Last milestone achieved
    next_milestone: int
    streak_type: str  # "meals", "hydration", "overall"
    is_active: bool  # True if streak is ongoing today
    motivation_message: str
    
    def __post_init__(self):
        """Validate streak data."""
        if self.current_count < 0:
            raise ValueError("Current count cannot be negative")
        if self.best_count < 0:
            raise ValueError("Best count cannot be negative")
        if self.next_milestone <= self.current_count:
            raise ValueError("Next milestone must be greater than current count")
        if self.milestone_reached and self.milestone_reached > self.current_count:
            raise ValueError("Milestone reached cannot be greater than current count")


@dataclass(frozen=True)
class Challenge:
    """
    Mini-challenge for user engagement.
    
    Short-term goals designed to increase adherence and
    provide immediate gratification through completion.
    """
    id: UUID
    title: str
    description: str
    challenge_type: ChallengeType
    status: ChallengeStatus
    progress: float  # 0.0 - 1.0 (completion percentage)
    target_value: int
    current_value: int
    expires_at: datetime
    reward_points: int
    difficulty_level: int  # 1-5 scale
    
    def __post_init__(self):
        """Validate challenge data."""
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")
        if self.target_value <= 0:
            raise ValueError("Target value must be positive")
        if self.current_value < 0:
            raise ValueError("Current value cannot be negative")
        if not 1 <= self.difficulty_level <= 5:
            raise ValueError("Difficulty level must be between 1 and 5")
        if self.reward_points < 0:
            raise ValueError("Reward points cannot be negative")


@dataclass(frozen=True)
class GamificationSummary:
    """
    Complete gamification data for widget display.
    
    Consolidated model containing all gamification elements
    optimized for mobile widget consumption with caching support.
    """
    user_id: UUID
    adherence_ring: AdherenceRing
    current_streak: Streak
    active_challenge: Optional[Challenge]
    total_points: int
    level: int
    level_progress: float  # 0.0 - 1.0 to next level
    last_updated: datetime
    cache_key: str  # For ETag generation
    widget_deep_link: str  # Deep link to full app
    
    # Widget-specific optimizations
    compact_message: str  # Short message for small widgets
    primary_metric: str   # Most important metric to highlight
    secondary_metrics: List[str]  # Additional metrics for larger widgets
    
    def __post_init__(self):
        """Validate gamification summary."""
        if self.total_points < 0:
            raise ValueError("Total points cannot be negative")
        if self.level < 1:
            raise ValueError("Level must be at least 1")
        if not 0.0 <= self.level_progress <= 1.0:
            raise ValueError("Level progress must be between 0.0 and 1.0")
        if len(self.compact_message) > 50:
            raise ValueError("Compact message must be 50 characters or less")


# Widget optimization helpers
def calculate_adherence_level(percentage: float) -> AdherenceLevel:
    """Calculate adherence level from percentage."""
    if percentage >= 90:
        return AdherenceLevel.EXCELLENT
    elif percentage >= 71:
        return AdherenceLevel.HIGH
    elif percentage >= 41:
        return AdherenceLevel.MEDIUM
    else:
        return AdherenceLevel.LOW


def get_ring_color(level: AdherenceLevel) -> str:
    """Get hex color for adherence ring based on level."""
    color_map = {
        AdherenceLevel.EXCELLENT: "#00C851",  # Green
        AdherenceLevel.HIGH: "#39C0ED",      # Blue
        AdherenceLevel.MEDIUM: "#FF8800",    # Orange
        AdherenceLevel.LOW: "#FF4444"        # Red
    }
    return color_map[level]


def generate_motivation_message(streak_count: int, streak_type: str) -> str:
    """Generate motivational message for streak display."""
    if streak_count == 0:
        return f"Start your {streak_type} streak today!"
    elif streak_count == 1:
        return f"Great start! Keep your {streak_type} streak going!"
    elif streak_count < 7:
        return f"{streak_count} days strong! You're building momentum!"
    elif streak_count < 30:
        return f"Amazing {streak_count}-day streak! You're on fire! 🔥"
    else:
        return f"Incredible {streak_count}-day streak! You're a champion! 🏆"


def create_compact_message(adherence: float, streak: int) -> str:
    """Create compact message for small widgets (≤50 chars)."""
    if streak > 0:
        return f"{adherence:.0f}% adherence • {streak} day streak"
    else:
        return f"{adherence:.0f}% adherence today"


# Widget configuration constants
WIDGET_CACHE_TTL_MIN = 5   # Minimum cache TTL in minutes
WIDGET_CACHE_TTL_MAX = 15  # Maximum cache TTL in minutes
WIDGET_DEEP_LINK_SCHEME = "ainutritionist"
MAX_CHALLENGES_PER_USER = 3
STREAK_MILESTONES = [3, 7, 14, 30, 60, 100, 365]
