"""
Behavioral Analysis Service

Analyzes user interaction patterns, eating behaviors, and engagement metrics
to provide insights and improve personalization effectiveness.

Consolidates functionality from:
- user_behavior_analysis_service.py
- engagement_tracking_service.py
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from collections import defaultdict, Counter
import statistics

logger = logging.getLogger(__name__)


class InteractionType(Enum):
    """Types of user interactions to track."""
    MESSAGE_SENT = "message_sent"
    MEAL_PLAN_REQUESTED = "meal_plan_requested"
    RECIPE_VIEWED = "recipe_viewed"
    FEEDBACK_PROVIDED = "feedback_provided"
    GOAL_UPDATED = "goal_updated"
    PREFERENCE_CHANGED = "preference_changed"
    SUBSCRIPTION_ACTION = "subscription_action"
    SHOPPING_LIST_GENERATED = "shopping_list_generated"


class EngagementLevel(Enum):
    """User engagement levels."""
    VERY_HIGH = "very_high"  # Daily active
    HIGH = "high"           # 4-6 times per week
    MEDIUM = "medium"       # 2-3 times per week
    LOW = "low"            # Once per week
    INACTIVE = "inactive"   # Less than once per week


@dataclass
class UserInteraction:
    """Individual user interaction record."""
    user_id: str
    interaction_type: InteractionType
    timestamp: datetime
    context: Dict[str, Any]
    session_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorPattern:
    """Identified behavioral pattern."""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: float
    confidence: float
    first_observed: datetime
    last_observed: datetime
    strength: float
    triggers: List[str]


@dataclass
class EngagementMetrics:
    """User engagement metrics."""
    user_id: str
    total_interactions: int
    unique_days_active: int
    average_session_duration: float
    most_common_interactions: List[Tuple[str, int]]
    peak_activity_hours: List[int]
    engagement_level: EngagementLevel
    retention_score: float
    churn_risk: float
    last_activity: datetime
    created_at: datetime


@dataclass
class BehaviorInsights:
    """Comprehensive behavior analysis insights."""
    user_id: str
    engagement_metrics: EngagementMetrics
    identified_patterns: List[BehaviorPattern]
    eating_schedule: Dict[str, Any]
    goal_achievement_trends: Dict[str, float]
    recommendation_effectiveness: Dict[str, float]
    personalization_opportunities: List[str]
    generated_at: datetime


class BehaviorAnalysisService:
    """
    Advanced behavioral analysis service for nutrition coaching personalization.
    
    Features:
    - Real-time interaction tracking and pattern detection
    - Engagement level classification and churn prediction
    - Eating behavior analysis and schedule optimization
    - Goal achievement correlation analysis
    - Personalization effectiveness measurement
    - Automated insight generation for coaching improvements
    """

    def __init__(self):
        self.interaction_cache: Dict[str, List[UserInteraction]] = defaultdict(list)
        self.pattern_cache: Dict[str, List[BehaviorPattern]] = defaultdict(list)
        self.engagement_cache: Dict[str, EngagementMetrics] = {}

    def track_interaction(
        self,
        user_id: str,
        interaction_type: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track user interaction with comprehensive context capture.
        
        Args:
            user_id: User identifier
            interaction_type: Type of interaction
            context: Interaction context data
            session_id: Session identifier
            duration_seconds: Interaction duration
            success: Whether interaction was successful
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            interaction = UserInteraction(
                user_id=user_id,
                interaction_type=InteractionType(interaction_type),
                timestamp=datetime.utcnow(),
                context=context or {},
                session_id=session_id,
                duration_seconds=duration_seconds,
                success=success,
                metadata=metadata or {}
            )
            
            # Cache interaction
            self.interaction_cache[user_id].append(interaction)
            
            # Maintain cache size (keep last 1000 interactions)
            if len(self.interaction_cache[user_id]) > 1000:
                self.interaction_cache[user_id] = self.interaction_cache[user_id][-1000:]
            
            # Persist to storage
            self._save_interaction_to_storage(interaction)
            
            # Trigger real-time pattern detection for high-frequency users
            if len(self.interaction_cache[user_id]) % 10 == 0:
                self._detect_real_time_patterns(user_id)
            
            logger.debug(f"Tracked interaction for {user_id}: {interaction_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking interaction: {e}")
            return False

    def analyze_user_behavior(
        self,
        user_id: str,
        analysis_period_days: int = 30
    ) -> Optional[BehaviorInsights]:
        """
        Perform comprehensive behavioral analysis for user.
        
        Args:
            user_id: User identifier
            analysis_period_days: Period for analysis in days
            
        Returns:
            Comprehensive behavior insights
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=analysis_period_days)
            
            # Get recent interactions
            interactions = self._get_user_interactions(user_id, cutoff_date)
            if not interactions:
                logger.warning(f"No interactions found for user {user_id}")
                return None
            
            # Calculate engagement metrics
            engagement_metrics = self._calculate_engagement_metrics(user_id, interactions)
            
            # Detect behavioral patterns
            patterns = self._detect_behavioral_patterns(user_id, interactions)
            
            # Analyze eating schedule
            eating_schedule = self._analyze_eating_schedule(user_id, interactions)
            
            # Analyze goal achievement
            goal_trends = self._analyze_goal_achievement_trends(user_id, interactions)
            
            # Measure recommendation effectiveness
            rec_effectiveness = self._measure_recommendation_effectiveness(user_id, interactions)
            
            # Identify personalization opportunities
            opportunities = self._identify_personalization_opportunities(
                engagement_metrics, patterns, eating_schedule
            )
            
            insights = BehaviorInsights(
                user_id=user_id,
                engagement_metrics=engagement_metrics,
                identified_patterns=patterns,
                eating_schedule=eating_schedule,
                goal_achievement_trends=goal_trends,
                recommendation_effectiveness=rec_effectiveness,
                personalization_opportunities=opportunities,
                generated_at=datetime.utcnow()
            )
            
            logger.info(f"Generated behavior insights for user {user_id}")
            return insights
            
        except Exception as e:
            logger.error(f"Error analyzing user behavior: {e}")
            return None

    def get_engagement_level(self, user_id: str) -> EngagementLevel:
        """
        Classify user engagement level based on recent activity.
        
        Args:
            user_id: User identifier
            
        Returns:
            Current engagement level
        """
        try:
            if user_id in self.engagement_cache:
                return self.engagement_cache[user_id].engagement_level
            
            # Calculate engagement from recent activity
            recent_interactions = self._get_user_interactions(
                user_id, datetime.utcnow() - timedelta(days=7)
            )
            
            if not recent_interactions:
                return EngagementLevel.INACTIVE
            
            # Count unique active days in last week
            active_days = len(set(
                interaction.timestamp.date() for interaction in recent_interactions
            ))
            
            if active_days >= 6:
                return EngagementLevel.VERY_HIGH
            elif active_days >= 4:
                return EngagementLevel.HIGH
            elif active_days >= 2:
                return EngagementLevel.MEDIUM
            elif active_days >= 1:
                return EngagementLevel.LOW
            else:
                return EngagementLevel.INACTIVE
                
        except Exception as e:
            logger.error(f"Error getting engagement level: {e}")
            return EngagementLevel.INACTIVE

    def predict_churn_risk(self, user_id: str) -> float:
        """
        Predict user churn risk based on behavioral patterns.
        
        Args:
            user_id: User identifier
            
        Returns:
            Churn risk score (0.0-1.0)
        """
        try:
            # Get recent activity patterns
            recent_interactions = self._get_user_interactions(
                user_id, datetime.utcnow() - timedelta(days=14)
            )
            
            if not recent_interactions:
                return 1.0  # No recent activity = high churn risk
            
            # Calculate risk factors
            risk_factors = []
            
            # Days since last activity
            days_since_last = (datetime.utcnow() - recent_interactions[-1].timestamp).days
            risk_factors.append(min(1.0, days_since_last / 7.0))
            
            # Declining interaction frequency
            first_week = [i for i in recent_interactions if i.timestamp >= datetime.utcnow() - timedelta(days=7)]
            second_week = [i for i in recent_interactions if i.timestamp < datetime.utcnow() - timedelta(days=7)]
            
            if second_week:
                freq_decline = max(0.0, (len(second_week) - len(first_week)) / len(second_week))
                risk_factors.append(freq_decline)
            
            # Failed interaction rate
            failed_interactions = [i for i in recent_interactions if not i.success]
            failure_rate = len(failed_interactions) / len(recent_interactions)
            risk_factors.append(failure_rate)
            
            # Session duration decline
            session_durations = [i.duration_seconds for i in recent_interactions if i.duration_seconds]
            if len(session_durations) >= 5:
                recent_avg = statistics.mean(session_durations[-5:])
                overall_avg = statistics.mean(session_durations)
                if overall_avg > 0:
                    duration_decline = max(0.0, (overall_avg - recent_avg) / overall_avg)
                    risk_factors.append(duration_decline)
            
            # Calculate weighted average
            churn_risk = statistics.mean(risk_factors) if risk_factors else 0.5
            
            logger.debug(f"Churn risk for {user_id}: {churn_risk:.3f}")
            return min(1.0, max(0.0, churn_risk))
            
        except Exception as e:
            logger.error(f"Error predicting churn risk: {e}")
            return 0.5

    def get_optimal_engagement_times(self, user_id: str) -> List[Tuple[int, float]]:
        """
        Identify optimal times for user engagement based on activity patterns.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of (hour, engagement_probability) tuples
        """
        try:
            interactions = self._get_user_interactions(
                user_id, datetime.utcnow() - timedelta(days=30)
            )
            
            if not interactions:
                # Return general optimal times
                return [(7, 0.6), (12, 0.8), (18, 0.7)]
            
            # Analyze hourly activity patterns
            hourly_counts = Counter(interaction.timestamp.hour for interaction in interactions)
            total_interactions = len(interactions)
            
            # Calculate engagement probability for each hour
            engagement_times = []
            for hour in range(24):
                count = hourly_counts.get(hour, 0)
                probability = count / total_interactions if total_interactions > 0 else 0
                if probability > 0.05:  # Only include hours with significant activity
                    engagement_times.append((hour, probability))
            
            # Sort by probability descending
            engagement_times.sort(key=lambda x: x[1], reverse=True)
            
            return engagement_times[:5]  # Top 5 optimal times
            
        except Exception as e:
            logger.error(f"Error getting optimal engagement times: {e}")
            return [(12, 0.5)]

    def measure_goal_progress_correlation(
        self,
        user_id: str,
        goal_type: str
    ) -> Dict[str, float]:
        """
        Measure correlation between user actions and goal progress.
        
        Args:
            user_id: User identifier
            goal_type: Type of goal to analyze
            
        Returns:
            Dictionary of action-correlation pairs
        """
        try:
            interactions = self._get_user_interactions(
                user_id, datetime.utcnow() - timedelta(days=60)
            )
            
            # Group interactions by type and measure frequency
            action_frequencies = defaultdict(int)
            for interaction in interactions:
                action_frequencies[interaction.interaction_type.value] += 1
            
            # Mock goal progress data (in production, this would come from goal service)
            goal_progress = self._get_mock_goal_progress(user_id, goal_type)
            
            # Calculate correlations (simplified - in production use proper correlation analysis)
            correlations = {}
            for action_type, frequency in action_frequencies.items():
                # Higher frequency of certain actions correlates with better progress
                correlation_map = {
                    "meal_plan_requested": 0.7,
                    "feedback_provided": 0.8,
                    "recipe_viewed": 0.5,
                    "goal_updated": 0.6,
                    "shopping_list_generated": 0.6
                }
                
                base_correlation = correlation_map.get(action_type, 0.3)
                # Adjust based on frequency (more engagement = higher correlation)
                frequency_factor = min(1.0, frequency / 10.0)
                correlations[action_type] = base_correlation * frequency_factor
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error measuring goal progress correlation: {e}")
            return {}

    def _calculate_engagement_metrics(
        self,
        user_id: str,
        interactions: List[UserInteraction]
    ) -> EngagementMetrics:
        """Calculate comprehensive engagement metrics."""
        if not interactions:
            return EngagementMetrics(
                user_id=user_id,
                total_interactions=0,
                unique_days_active=0,
                average_session_duration=0,
                most_common_interactions=[],
                peak_activity_hours=[],
                engagement_level=EngagementLevel.INACTIVE,
                retention_score=0.0,
                churn_risk=1.0,
                last_activity=datetime.utcnow() - timedelta(days=365),
                created_at=datetime.utcnow()
            )
        
        # Calculate metrics
        total_interactions = len(interactions)
        unique_days = len(set(i.timestamp.date() for i in interactions))
        
        # Session duration
        durations = [i.duration_seconds for i in interactions if i.duration_seconds]
        avg_duration = statistics.mean(durations) if durations else 0
        
        # Most common interactions
        interaction_counts = Counter(i.interaction_type.value for i in interactions)
        most_common = interaction_counts.most_common(5)
        
        # Peak activity hours
        hour_counts = Counter(i.timestamp.hour for i in interactions)
        peak_hours = [hour for hour, _ in hour_counts.most_common(3)]
        
        # Engagement level
        weekly_days = unique_days * 7 / 30  # Normalize to weekly
        if weekly_days >= 6:
            level = EngagementLevel.VERY_HIGH
        elif weekly_days >= 4:
            level = EngagementLevel.HIGH
        elif weekly_days >= 2:
            level = EngagementLevel.MEDIUM
        elif weekly_days >= 1:
            level = EngagementLevel.LOW
        else:
            level = EngagementLevel.INACTIVE
        
        # Retention score (based on consistency)
        retention_score = min(1.0, unique_days / 30.0)
        
        # Churn risk
        churn_risk = self.predict_churn_risk(user_id)
        
        return EngagementMetrics(
            user_id=user_id,
            total_interactions=total_interactions,
            unique_days_active=unique_days,
            average_session_duration=avg_duration,
            most_common_interactions=most_common,
            peak_activity_hours=peak_hours,
            engagement_level=level,
            retention_score=retention_score,
            churn_risk=churn_risk,
            last_activity=interactions[-1].timestamp,
            created_at=datetime.utcnow()
        )

    def _detect_behavioral_patterns(
        self,
        user_id: str,
        interactions: List[UserInteraction]
    ) -> List[BehaviorPattern]:
        """Detect behavioral patterns from interaction data."""
        patterns = []
        
        try:
            # Time-based patterns
            patterns.extend(self._detect_time_patterns(interactions))
            
            # Sequence patterns
            patterns.extend(self._detect_sequence_patterns(interactions))
            
            # Frequency patterns
            patterns.extend(self._detect_frequency_patterns(interactions))
            
            # Cache patterns
            self.pattern_cache[user_id] = patterns
            
        except Exception as e:
            logger.error(f"Error detecting behavioral patterns: {e}")
        
        return patterns

    def _detect_time_patterns(self, interactions: List[UserInteraction]) -> List[BehaviorPattern]:
        """Detect time-based behavioral patterns."""
        patterns = []
        
        # Weekly patterns
        day_counts = Counter(i.timestamp.weekday() for i in interactions)
        if day_counts:
            most_active_day = day_counts.most_common(1)[0]
            if most_active_day[1] > len(interactions) * 0.3:  # More than 30% on one day
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                patterns.append(BehaviorPattern(
                    pattern_id=f"weekly_peak_{most_active_day[0]}",
                    pattern_type="temporal",
                    description=f"Most active on {day_names[most_active_day[0]]}",
                    frequency=most_active_day[1] / len(interactions),
                    confidence=0.8,
                    first_observed=min(i.timestamp for i in interactions),
                    last_observed=max(i.timestamp for i in interactions),
                    strength=most_active_day[1] / len(interactions),
                    triggers=["weekday_routine"]
                ))
        
        return patterns

    def _detect_sequence_patterns(self, interactions: List[UserInteraction]) -> List[BehaviorPattern]:
        """Detect sequential behavioral patterns."""
        patterns = []
        
        # Look for common interaction sequences
        sequences = []
        for i in range(len(interactions) - 1):
            curr_type = interactions[i].interaction_type.value
            next_type = interactions[i + 1].interaction_type.value
            time_diff = (interactions[i + 1].timestamp - interactions[i].timestamp).total_seconds()
            
            # Only consider sequences within 1 hour
            if time_diff <= 3600:
                sequences.append((curr_type, next_type))
        
        # Find most common sequences
        if sequences:
            sequence_counts = Counter(sequences)
            for (first, second), count in sequence_counts.most_common(3):
                if count >= 3:  # At least 3 occurrences
                    patterns.append(BehaviorPattern(
                        pattern_id=f"sequence_{first}_{second}",
                        pattern_type="sequential",
                        description=f"Often {second} after {first}",
                        frequency=count / len(sequences),
                        confidence=0.7,
                        first_observed=min(i.timestamp for i in interactions),
                        last_observed=max(i.timestamp for i in interactions),
                        strength=count / len(sequences),
                        triggers=[first]
                    ))
        
        return patterns

    def _detect_frequency_patterns(self, interactions: List[UserInteraction]) -> List[BehaviorPattern]:
        """Detect frequency-based behavioral patterns."""
        patterns = []
        
        # Daily interaction frequency
        daily_counts = defaultdict(int)
        for interaction in interactions:
            daily_counts[interaction.timestamp.date()] += 1
        
        if daily_counts:
            avg_daily = statistics.mean(daily_counts.values())
            if avg_daily >= 5:
                patterns.append(BehaviorPattern(
                    pattern_id="high_frequency_user",
                    pattern_type="frequency",
                    description="High daily interaction frequency",
                    frequency=avg_daily,
                    confidence=0.9,
                    first_observed=min(i.timestamp for i in interactions),
                    last_observed=max(i.timestamp for i in interactions),
                    strength=min(1.0, avg_daily / 10.0),
                    triggers=["daily_routine"]
                ))
        
        return patterns

    def _analyze_eating_schedule(
        self,
        user_id: str,
        interactions: List[UserInteraction]
    ) -> Dict[str, Any]:
        """Analyze user's eating schedule from interactions."""
        meal_related = [
            i for i in interactions 
            if i.interaction_type in [
                InteractionType.MEAL_PLAN_REQUESTED,
                InteractionType.RECIPE_VIEWED,
                InteractionType.FEEDBACK_PROVIDED
            ]
        ]
        
        if not meal_related:
            return {"pattern": "insufficient_data"}
        
        # Analyze timing patterns
        hours = [i.timestamp.hour for i in meal_related]
        hour_counts = Counter(hours)
        
        # Identify meal times
        meal_times = []
        for hour, count in hour_counts.most_common():
            if count >= 2:  # At least 2 occurrences
                meal_times.append(hour)
        
        return {
            "pattern": "regular" if len(meal_times) >= 3 else "irregular",
            "peak_meal_hours": meal_times[:3],
            "total_meal_interactions": len(meal_related),
            "consistency_score": len(set(meal_times)) / 24.0 if meal_times else 0
        }

    def _analyze_goal_achievement_trends(
        self,
        user_id: str,
        interactions: List[UserInteraction]
    ) -> Dict[str, float]:
        """Analyze goal achievement trends."""
        # Mock analysis (in production, integrate with goal tracking service)
        goal_interactions = [
            i for i in interactions
            if i.interaction_type == InteractionType.GOAL_UPDATED
        ]
        
        if not goal_interactions:
            return {"trend": 0.5, "confidence": 0.0}
        
        # Simple trend analysis based on interaction frequency
        recent_goals = len([
            i for i in goal_interactions
            if i.timestamp >= datetime.utcnow() - timedelta(days=7)
        ])
        
        return {
            "trend": min(1.0, recent_goals / 3.0),  # Normalize to 0-1
            "confidence": min(1.0, len(goal_interactions) / 10.0),
            "total_goal_updates": len(goal_interactions)
        }

    def _measure_recommendation_effectiveness(
        self,
        user_id: str,
        interactions: List[UserInteraction]
    ) -> Dict[str, float]:
        """Measure effectiveness of recommendations."""
        # Find recommendation-related interactions
        recommendations = [
            i for i in interactions
            if "recommendation" in i.context.get("type", "").lower()
        ]
        
        if not recommendations:
            return {"effectiveness": 0.5, "sample_size": 0}
        
        # Calculate acceptance rate based on follow-up actions
        accepted = len([
            r for r in recommendations
            if r.context.get("accepted", False) or r.success
        ])
        
        effectiveness = accepted / len(recommendations) if recommendations else 0.5
        
        return {
            "effectiveness": effectiveness,
            "sample_size": len(recommendations),
            "acceptance_rate": effectiveness
        }

    def _identify_personalization_opportunities(
        self,
        engagement: EngagementMetrics,
        patterns: List[BehaviorPattern],
        eating_schedule: Dict[str, Any]
    ) -> List[str]:
        """Identify opportunities for improved personalization."""
        opportunities = []
        
        # Low engagement opportunities
        if engagement.engagement_level in [EngagementLevel.LOW, EngagementLevel.INACTIVE]:
            opportunities.append("increase_engagement_frequency")
            opportunities.append("optimize_notification_timing")
        
        # High churn risk
        if engagement.churn_risk > 0.7:
            opportunities.append("implement_retention_strategy")
            opportunities.append("personalize_content_delivery")
        
        # Irregular eating patterns
        if eating_schedule.get("pattern") == "irregular":
            opportunities.append("suggest_meal_timing_optimization")
            opportunities.append("provide_flexible_meal_plans")
        
        # Pattern-based opportunities
        for pattern in patterns:
            if pattern.pattern_type == "temporal":
                opportunities.append("leverage_timing_preferences")
            elif pattern.pattern_type == "sequential":
                opportunities.append("optimize_interaction_flow")
        
        return list(set(opportunities))  # Remove duplicates

    def _detect_real_time_patterns(self, user_id: str) -> None:
        """Detect patterns in real-time for immediate personalization."""
        try:
            recent_interactions = self.interaction_cache[user_id][-10:]
            if len(recent_interactions) >= 5:
                # Quick pattern detection for immediate use
                patterns = self._detect_frequency_patterns(recent_interactions)
                if patterns:
                    self.pattern_cache[user_id].extend(patterns)
        except Exception as e:
            logger.error(f"Error in real-time pattern detection: {e}")

    def _get_user_interactions(
        self,
        user_id: str,
        since: datetime
    ) -> List[UserInteraction]:
        """Get user interactions since specified time."""
        # First check cache
        cached = self.interaction_cache.get(user_id, [])
        recent_cached = [i for i in cached if i.timestamp >= since]
        
        # In production, also query database for older interactions
        # For now, return cached interactions
        return recent_cached

    def _get_mock_goal_progress(self, user_id: str, goal_type: str) -> float:
        """Mock goal progress data (replace with actual goal service integration)."""
        # Return mock progress between 0.0 and 1.0
        return 0.7  # 70% progress

    def _save_interaction_to_storage(self, interaction: UserInteraction) -> bool:
        """Save interaction to persistent storage."""
        # In production, save to database
        # For now, just log
        logger.debug(f"Saved interaction: {interaction.user_id} - {interaction.interaction_type.value}")
        return True
