"""
Gamification Service Layer

Enterprise-grade business logic for widget gamification features including
adherence calculation, streak management, and challenge generation.

Architecture:
- GamificationService: Main business logic orchestrator
- AdherenceCalculator: Adherence percentage and trend analysis
- StreakManager: Streak counting and milestone tracking
- ChallengeGenerator: Dynamic challenge creation and management

Author: AI Nutritionist Development Team
Date: September 2025
"""

import hashlib
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import json

from src.models.gamification import (
    GamificationSummary,
    AdherenceRing,
    Streak,
    Challenge,
    AdherenceLevel,
    ChallengeType,
    ChallengeStatus,
    calculate_adherence_level,
    get_ring_color,
    generate_motivation_message,
    create_compact_message,
    STREAK_MILESTONES,
    MAX_CHALLENGES_PER_USER,
    WIDGET_DEEP_LINK_SCHEME
)


class AdherenceCalculator:
    """Calculate adherence metrics for gamification display."""
    
    def calculate_adherence_percentage(
        self,
        user_id: UUID,
        days_back: int = 7
    ) -> Tuple[float, str, int]:
        """
        Calculate adherence percentage and trend.
        
        Returns:
            Tuple of (percentage, trend, days_tracked)
        """
        # Mock data - in production would query meal_feedback table
        adherence_data = self._get_mock_adherence_data(user_id, days_back)
        
        if not adherence_data:
            return 0.0, "stable", 0
        
        # Calculate percentage
        total_meals = len(adherence_data)
        successful_meals = sum(1 for meal in adherence_data if meal["completed"])
        percentage = (successful_meals / total_meals) * 100 if total_meals > 0 else 0.0
        
        # Calculate trend (comparing last 3 days vs previous 3 days)
        trend = self._calculate_trend(adherence_data)
        
        return round(percentage, 1), trend, total_meals // 3  # Assume 3 meals per day
    
    def _get_mock_adherence_data(self, user_id: UUID, days_back: int) -> List[Dict[str, Any]]:
        """Mock adherence data - replace with real database query."""
        # Simulate realistic adherence patterns
        import random
        random.seed(str(user_id))  # Consistent data per user
        
        data = []
        for day in range(days_back):
            for meal in range(3):  # 3 meals per day
                # Higher adherence probability for breakfast, lower for late meals
                base_probability = 0.8 if meal == 0 else 0.7 if meal == 1 else 0.6
                completed = random.random() < base_probability
                
                data.append({
                    "day": day,
                    "meal": meal,
                    "completed": completed,
                    "timestamp": datetime.now() - timedelta(days=day, hours=meal*4)
                })
        
        return data
    
    def _calculate_trend(self, adherence_data: List[Dict[str, Any]]) -> str:
        """Calculate adherence trend from historical data."""
        if len(adherence_data) < 6:  # Need at least 6 data points
            return "stable"
        
        # Split data into recent and previous periods
        mid_point = len(adherence_data) // 2
        recent_data = adherence_data[:mid_point]
        previous_data = adherence_data[mid_point:]
        
        recent_percentage = sum(1 for meal in recent_data if meal["completed"]) / len(recent_data)
        previous_percentage = sum(1 for meal in previous_data if meal["completed"]) / len(previous_data)
        
        difference = recent_percentage - previous_percentage
        
        if difference > 0.1:  # 10% improvement
            return "up"
        elif difference < -0.1:  # 10% decline
            return "down"
        else:
            return "stable"


class StreakManager:
    """Manage user streaks and milestone tracking."""
    
    def calculate_current_streak(self, user_id: UUID, streak_type: str = "overall") -> Streak:
        """Calculate current streak for user."""
        # Mock data - in production would query meal_feedback and user activity
        current_count = self._get_mock_current_streak(user_id)
        best_count = self._get_mock_best_streak(user_id)
        
        # Find milestone information
        milestone_reached = None
        next_milestone = 3  # Default first milestone
        
        for milestone in STREAK_MILESTONES:
            if current_count >= milestone:
                milestone_reached = milestone
            elif current_count < milestone:
                next_milestone = milestone
                break
        
        # Check if streak is active (user completed today's goals)
        is_active = self._is_streak_active(user_id)
        
        motivation_message = generate_motivation_message(current_count, streak_type)
        
        return Streak(
            current_count=current_count,
            best_count=best_count,
            milestone_reached=milestone_reached,
            next_milestone=next_milestone,
            streak_type=streak_type,
            is_active=is_active,
            motivation_message=motivation_message
        )
    
    def _get_mock_current_streak(self, user_id: UUID) -> int:
        """Mock current streak - replace with real database query."""
        import random
        random.seed(str(user_id))
        return random.randint(0, 45)  # 0-45 day streak
    
    def _get_mock_best_streak(self, user_id: UUID) -> int:
        """Mock best streak - replace with real database query."""
        import random
        random.seed(str(user_id) + "best")
        current = self._get_mock_current_streak(user_id)
        return max(current, random.randint(current, current + 20))
    
    def _is_streak_active(self, user_id: UUID) -> bool:
        """Check if user's streak is active today."""
        import random
        random.seed(str(user_id) + str(date.today()))
        return random.random() > 0.3  # 70% chance streak is active


class ChallengeGenerator:
    """Generate and manage mini-challenges for users."""
    
    def __init__(self):
        self.challenge_templates = {
            ChallengeType.DAILY_GOAL: {
                "title": "Daily Goal Master",
                "description": "Complete all your meals for the day",
                "target_value": 3,
                "reward_points": 50,
                "difficulty": 2
            },
            ChallengeType.HYDRATION: {
                "title": "Hydration Hero",
                "description": "Log 8 glasses of water",
                "target_value": 8,
                "reward_points": 30,
                "difficulty": 1
            },
            ChallengeType.MEAL_PREP: {
                "title": "Prep Champion",
                "description": "Prepare 3 meals in advance",
                "target_value": 3,
                "reward_points": 75,
                "difficulty": 3
            },
            ChallengeType.VARIETY: {
                "title": "Variety Explorer",
                "description": "Try 5 different vegetables this week",
                "target_value": 5,
                "reward_points": 60,
                "difficulty": 2
            },
            ChallengeType.MINDFUL_EATING: {
                "title": "Mindful Moments",
                "description": "Eat without distractions for 3 meals",
                "target_value": 3,
                "reward_points": 40,
                "difficulty": 2
            }
        }
    
    def get_active_challenge(self, user_id: UUID) -> Optional[Challenge]:
        """Get user's current active challenge."""
        # Mock data - in production would query challenges table
        challenge_data = self._get_mock_challenge_data(user_id)
        
        if not challenge_data:
            return None
        
        template = self.challenge_templates[challenge_data["type"]]
        
        progress = min(challenge_data["current_value"] / challenge_data["target_value"], 1.0)
        
        # Determine status
        if progress >= 1.0:
            status = ChallengeStatus.COMPLETED
        elif datetime.now() > challenge_data["expires_at"]:
            status = ChallengeStatus.EXPIRED
        elif challenge_data["current_value"] > 0:
            status = ChallengeStatus.IN_PROGRESS
        else:
            status = ChallengeStatus.NOT_STARTED
        
        return Challenge(
            id=challenge_data["id"],
            title=template["title"],
            description=template["description"],
            challenge_type=challenge_data["type"],
            status=status,
            progress=progress,
            target_value=challenge_data["target_value"],
            current_value=challenge_data["current_value"],
            expires_at=challenge_data["expires_at"],
            reward_points=template["reward_points"],
            difficulty_level=template["difficulty"]
        )
    
    def _get_mock_challenge_data(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Mock challenge data - replace with real database query."""
        import random
        random.seed(str(user_id) + "challenge")
        
        # 80% chance user has an active challenge
        if random.random() < 0.2:
            return None
        
        challenge_type = random.choice(list(ChallengeType))
        template = self.challenge_templates[challenge_type]
        
        return {
            "id": uuid4(),
            "type": challenge_type,
            "target_value": template["target_value"],
            "current_value": random.randint(0, template["target_value"] + 1),
            "expires_at": datetime.now() + timedelta(days=1),
            "created_at": datetime.now() - timedelta(hours=random.randint(1, 23))
        }


class GamificationService:
    """
    Main gamification service orchestrating all gamification features.
    
    Provides consolidated business logic for widget API consumption
    with caching optimization and performance monitoring.
    """
    
    def __init__(self):
        self.adherence_calculator = AdherenceCalculator()
        self.streak_manager = StreakManager()
        self.challenge_generator = ChallengeGenerator()
    
    async def get_gamification_summary(self, user_id: UUID) -> GamificationSummary:
        """
        Get complete gamification summary for widget display.
        
        Orchestrates all gamification components and optimizes for
        mobile widget consumption with caching support.
        """
        # Calculate adherence metrics
        adherence_percentage, trend, days_tracked = (
            self.adherence_calculator.calculate_adherence_percentage(user_id)
        )
        
        # Create adherence ring
        level = calculate_adherence_level(adherence_percentage)
        adherence_ring = AdherenceRing(
            percentage=adherence_percentage,
            level=level,
            trend=trend,
            days_tracked=days_tracked,
            target_percentage=80.0,  # Default target
            ring_color=get_ring_color(level)
        )
        
        # Get current streak
        current_streak = self.streak_manager.calculate_current_streak(user_id)
        
        # Get active challenge
        active_challenge = self.challenge_generator.get_active_challenge(user_id)
        
        # Calculate user level and points (mock data)
        total_points, level, level_progress = self._calculate_user_level(user_id)
        
        # Generate cache key for ETag
        cache_key = self._generate_cache_key(user_id, adherence_percentage, current_streak.current_count)
        
        # Create widget-optimized content
        compact_message = create_compact_message(adherence_percentage, current_streak.current_count)
        primary_metric = f"{adherence_percentage:.0f}% adherence"
        secondary_metrics = [
            f"{current_streak.current_count} day streak",
            f"Level {level}",
            f"{total_points} points"
        ]
        
        # Generate deep link
        deep_link = f"{WIDGET_DEEP_LINK_SCHEME}://dashboard?user_id={user_id}"
        
        return GamificationSummary(
            user_id=user_id,
            adherence_ring=adherence_ring,
            current_streak=current_streak,
            active_challenge=active_challenge,
            total_points=total_points,
            level=level,
            level_progress=level_progress,
            last_updated=datetime.now(),
            cache_key=cache_key,
            widget_deep_link=deep_link,
            compact_message=compact_message,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics
        )
    
    def _calculate_user_level(self, user_id: UUID) -> Tuple[int, int, float]:
        """Calculate user level, total points, and progress to next level."""
        import random
        random.seed(str(user_id) + "level")
        
        total_points = random.randint(500, 5000)
        
        # Level calculation: 1000 points per level
        level = (total_points // 1000) + 1
        points_in_current_level = total_points % 1000
        level_progress = points_in_current_level / 1000.0
        
        return total_points, level, level_progress
    
    def _generate_cache_key(self, user_id: UUID, adherence: float, streak: int) -> str:
        """Generate cache key for ETag header."""
        data = f"{user_id}:{adherence}:{streak}:{datetime.now().strftime('%Y-%m-%d-%H')}"
        return hashlib.md5(data.encode()).hexdigest()
    
    async def invalidate_user_cache(self, user_id: UUID) -> None:
        """Invalidate user's gamification cache when data changes."""
        # In production, would clear cache entries
        pass
    
    async def get_cache_headers(self, summary: GamificationSummary) -> Dict[str, str]:
        """Generate cache headers for widget API response."""
        from src.models.gamification import WIDGET_CACHE_TTL_MIN, WIDGET_CACHE_TTL_MAX
        import random
        
        # Randomize TTL between 5-15 minutes to prevent thundering herd
        ttl_seconds = random.randint(WIDGET_CACHE_TTL_MIN * 60, WIDGET_CACHE_TTL_MAX * 60)
        
        return {
            "ETag": f'"{summary.cache_key}"',
            "Cache-Control": f"private, max-age={ttl_seconds}",
            "Expires": (datetime.now() + timedelta(seconds=ttl_seconds)).strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            ),
            "Last-Modified": summary.last_updated.strftime("%a, %d %b %Y %H:%M:%S GMT")
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for gamification service."""
        return {
            "status": "healthy",
            "components": {
                "adherence_calculator": "operational",
                "streak_manager": "operational", 
                "challenge_generator": "operational"
            },
            "timestamp": datetime.now().isoformat()
        }
