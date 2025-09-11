"""
Health Goals Management Service

Manages user health goals, tracks progress, and provides goal-based recommendations
with intelligent adaptation and achievement prediction.

Consolidates functionality from:
- health_goals_service.py
- goal_tracking_service.py
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


class GoalType(Enum):
    """Types of health goals users can set."""
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    ENDURANCE = "endurance"
    STRENGTH = "strength"
    GENERAL_HEALTH = "general_health"
    DISEASE_MANAGEMENT = "disease_management"
    ENERGY_BOOST = "energy_boost"
    BETTER_SLEEP = "better_sleep"


class GoalStatus(Enum):
    """Status of goal progress."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ON_TRACK = "on_track"
    BEHIND = "behind"
    AHEAD = "ahead"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class GoalPriority(Enum):
    """Priority levels for goals."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Milestone:
    """Individual milestone within a goal."""
    milestone_id: str
    title: str
    description: str
    target_value: float
    current_value: float
    unit: str
    target_date: datetime
    completed: bool = False
    completed_date: Optional[datetime] = None


@dataclass
class ProgressEntry:
    """Individual progress measurement."""
    entry_id: str
    goal_id: str
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    notes: Optional[str] = None
    data_source: str = "manual"
    confidence: float = 1.0


@dataclass
class HealthGoal:
    """Complete health goal definition with tracking."""
    goal_id: str
    user_id: str
    goal_type: GoalType
    title: str
    description: str
    target_value: float
    current_value: float
    start_value: float
    unit: str
    target_date: datetime
    created_date: datetime
    priority: GoalPriority
    status: GoalStatus
    milestones: List[Milestone]
    progress_entries: List[ProgressEntry]
    related_goals: List[str]
    success_metrics: Dict[str, Any]
    adaptive_targets: bool = True
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GoalRecommendation:
    """Recommendation for goal modification or new goals."""
    recommendation_id: str
    goal_id: Optional[str]
    recommendation_type: str  # "adjust_target", "add_milestone", "new_goal", "change_timeline"
    title: str
    description: str
    rationale: str
    confidence_score: float
    impact_score: float
    effort_required: str
    suggested_actions: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GoalInsights:
    """Comprehensive insights about goal progress."""
    user_id: str
    total_goals: int
    active_goals: int
    completed_goals: int
    on_track_goals: int
    behind_goals: int
    overall_progress_score: float
    achievement_rate: float
    average_goal_duration: float
    most_successful_goal_types: List[str]
    recommendations: List[GoalRecommendation]
    predicted_completions: Dict[str, datetime]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class HealthGoalsService:
    """
    Advanced health goals management service with AI-powered tracking and adaptation.
    
    Features:
    - Comprehensive goal setting with SMART criteria validation
    - Automated progress tracking with multiple data sources
    - Intelligent milestone management and adaptive targeting
    - Goal interdependency analysis and conflict detection
    - Predictive achievement modeling and timeline optimization
    - Personalized recommendations for goal adjustment and new goal suggestions
    """

    def __init__(self):
        self.goals_cache: Dict[str, HealthGoal] = {}
        self.user_goals: Dict[str, List[str]] = defaultdict(list)
        self.progress_cache: Dict[str, List[ProgressEntry]] = defaultdict(list)

    def create_health_goal(
        self,
        user_id: str,
        goal_type: str,
        title: str,
        description: str,
        target_value: float,
        unit: str,
        target_date: datetime,
        priority: str = "medium",
        current_value: Optional[float] = None,
        milestones: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[HealthGoal]:
        """
        Create new health goal with validation and intelligent defaults.
        
        Args:
            user_id: User identifier
            goal_type: Type of health goal
            title: Goal title
            description: Detailed description
            target_value: Target value to achieve
            unit: Unit of measurement
            target_date: Target completion date
            priority: Goal priority level
            current_value: Current baseline value
            milestones: Optional milestone definitions
            
        Returns:
            Created health goal or None if creation failed
        """
        try:
            # Validate inputs
            goal_type_enum = GoalType(goal_type.lower())
            priority_enum = GoalPriority[priority.upper()]
            
            # Generate unique goal ID
            goal_id = f"{user_id}_{goal_type}_{int(datetime.utcnow().timestamp())}"
            
            # Set intelligent defaults
            if current_value is None:
                current_value = self._get_default_current_value(goal_type_enum, target_value)
            
            start_value = current_value
            
            # Validate goal feasibility
            is_feasible, feasibility_message = self._validate_goal_feasibility(
                goal_type_enum, current_value, target_value, target_date
            )
            
            if not is_feasible:
                logger.warning(f"Goal may not be feasible: {feasibility_message}")
            
            # Create milestone structure
            goal_milestones = []
            if milestones:
                goal_milestones = self._create_milestones(goal_id, milestones)
            else:
                goal_milestones = self._generate_default_milestones(
                    goal_id, goal_type_enum, current_value, target_value, target_date, unit
                )
            
            # Create goal
            goal = HealthGoal(
                goal_id=goal_id,
                user_id=user_id,
                goal_type=goal_type_enum,
                title=title,
                description=description,
                target_value=target_value,
                current_value=current_value,
                start_value=start_value,
                unit=unit,
                target_date=target_date,
                created_date=datetime.utcnow(),
                priority=priority_enum,
                status=GoalStatus.NOT_STARTED,
                milestones=goal_milestones,
                progress_entries=[],
                related_goals=[],
                success_metrics=self._initialize_success_metrics(goal_type_enum),
                adaptive_targets=True
            )
            
            # Cache goal
            self.goals_cache[goal_id] = goal
            self.user_goals[user_id].append(goal_id)
            
            # Check for goal conflicts/synergies
            self._analyze_goal_relationships(user_id, goal_id)
            
            logger.info(f"Created health goal for user {user_id}: {title}")
            return goal
            
        except Exception as e:
            logger.error(f"Error creating health goal: {e}")
            return None

    def update_progress(
        self,
        goal_id: str,
        value: float,
        timestamp: Optional[datetime] = None,
        notes: Optional[str] = None,
        data_source: str = "manual"
    ) -> bool:
        """
        Update progress for a health goal with intelligent analysis.
        
        Args:
            goal_id: Goal identifier
            value: New progress value
            timestamp: When measurement was taken
            notes: Optional notes about the measurement
            data_source: Source of the data
            
        Returns:
            Success status
        """
        try:
            goal = self.goals_cache.get(goal_id)
            if not goal:
                logger.error(f"Goal not found: {goal_id}")
                return False
            
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            # Create progress entry
            entry_id = f"{goal_id}_{int(timestamp.timestamp())}"
            progress_entry = ProgressEntry(
                entry_id=entry_id,
                goal_id=goal_id,
                timestamp=timestamp,
                metric_name=goal.goal_type.value,
                value=value,
                unit=goal.unit,
                notes=notes,
                data_source=data_source,
                confidence=1.0 if data_source == "manual" else 0.8
            )
            
            # Update goal progress
            goal.current_value = value
            goal.progress_entries.append(progress_entry)
            goal.last_updated = timestamp
            
            # Update goal status
            self._update_goal_status(goal)
            
            # Check milestone completions
            self._check_milestone_completions(goal)
            
            # Update adaptive targets if enabled
            if goal.adaptive_targets:
                self._update_adaptive_targets(goal)
            
            # Cache progress entry
            self.progress_cache[goal_id].append(progress_entry)
            
            logger.info(f"Updated progress for goal {goal_id}: {value} {goal.unit}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            return False

    def get_goal_insights(self, user_id: str) -> Optional[GoalInsights]:
        """
        Generate comprehensive insights about user's goals and progress.
        
        Args:
            user_id: User identifier
            
        Returns:
            Comprehensive goal insights
        """
        try:
            user_goal_ids = self.user_goals.get(user_id, [])
            user_goals = [self.goals_cache[gid] for gid in user_goal_ids if gid in self.goals_cache]
            
            if not user_goals:
                return GoalInsights(
                    user_id=user_id,
                    total_goals=0,
                    active_goals=0,
                    completed_goals=0,
                    on_track_goals=0,
                    behind_goals=0,
                    overall_progress_score=0.0,
                    achievement_rate=0.0,
                    average_goal_duration=0.0,
                    most_successful_goal_types=[],
                    recommendations=[],
                    predicted_completions={}
                )
            
            # Calculate metrics
            total_goals = len(user_goals)
            active_goals = len([g for g in user_goals if g.status in [GoalStatus.IN_PROGRESS, GoalStatus.ON_TRACK, GoalStatus.BEHIND, GoalStatus.AHEAD]])
            completed_goals = len([g for g in user_goals if g.status == GoalStatus.COMPLETED])
            on_track_goals = len([g for g in user_goals if g.status in [GoalStatus.ON_TRACK, GoalStatus.AHEAD]])
            behind_goals = len([g for g in user_goals if g.status == GoalStatus.BEHIND])
            
            # Overall progress score
            progress_scores = []
            for goal in user_goals:
                if goal.status != GoalStatus.NOT_STARTED:
                    progress = self._calculate_goal_progress_percentage(goal)
                    progress_scores.append(progress)
            
            overall_progress_score = statistics.mean(progress_scores) if progress_scores else 0.0
            
            # Achievement rate
            achievement_rate = completed_goals / total_goals if total_goals > 0 else 0.0
            
            # Average goal duration
            completed_goals_with_duration = [
                g for g in user_goals 
                if g.status == GoalStatus.COMPLETED and g.progress_entries
            ]
            
            if completed_goals_with_duration:
                durations = []
                for goal in completed_goals_with_duration:
                    start_date = goal.created_date
                    end_date = max(entry.timestamp for entry in goal.progress_entries)
                    duration = (end_date - start_date).days
                    durations.append(duration)
                average_goal_duration = statistics.mean(durations)
            else:
                average_goal_duration = 0.0
            
            # Most successful goal types
            goal_type_success = defaultdict(list)
            for goal in user_goals:
                success_score = self._calculate_goal_success_score(goal)
                goal_type_success[goal.goal_type.value].append(success_score)
            
            goal_type_averages = {
                goal_type: statistics.mean(scores)
                for goal_type, scores in goal_type_success.items()
            }
            
            most_successful_types = sorted(
                goal_type_averages.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            most_successful_goal_types = [goal_type for goal_type, _ in most_successful_types]
            
            # Generate recommendations
            recommendations = self._generate_goal_recommendations(user_id, user_goals)
            
            # Predict completion dates
            predicted_completions = {}
            for goal in user_goals:
                if goal.status in [GoalStatus.IN_PROGRESS, GoalStatus.ON_TRACK, GoalStatus.BEHIND]:
                    predicted_date = self._predict_goal_completion(goal)
                    if predicted_date:
                        predicted_completions[goal.goal_id] = predicted_date
            
            insights = GoalInsights(
                user_id=user_id,
                total_goals=total_goals,
                active_goals=active_goals,
                completed_goals=completed_goals,
                on_track_goals=on_track_goals,
                behind_goals=behind_goals,
                overall_progress_score=overall_progress_score,
                achievement_rate=achievement_rate,
                average_goal_duration=average_goal_duration,
                most_successful_goal_types=most_successful_goal_types,
                recommendations=recommendations,
                predicted_completions=predicted_completions
            )
            
            logger.info(f"Generated goal insights for user {user_id}")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating goal insights: {e}")
            return None

    def get_user_goals(
        self,
        user_id: str,
        status_filter: Optional[List[str]] = None,
        goal_type_filter: Optional[List[str]] = None
    ) -> List[HealthGoal]:
        """
        Get user's health goals with optional filtering.
        
        Args:
            user_id: User identifier
            status_filter: Optional list of statuses to filter by
            goal_type_filter: Optional list of goal types to filter by
            
        Returns:
            List of matching health goals
        """
        try:
            user_goal_ids = self.user_goals.get(user_id, [])
            goals = [self.goals_cache[gid] for gid in user_goal_ids if gid in self.goals_cache]
            
            # Apply filters
            if status_filter:
                status_enums = [GoalStatus(s.lower()) for s in status_filter]
                goals = [g for g in goals if g.status in status_enums]
            
            if goal_type_filter:
                type_enums = [GoalType(t.lower()) for t in goal_type_filter]
                goals = [g for g in goals if g.goal_type in type_enums]
            
            # Sort by priority and creation date
            goals.sort(key=lambda g: (g.priority.value, g.created_date), reverse=True)
            
            return goals
            
        except Exception as e:
            logger.error(f"Error retrieving user goals: {e}")
            return []

    def update_goal_status(self, goal_id: str, new_status: str) -> bool:
        """
        Manually update goal status.
        
        Args:
            goal_id: Goal identifier
            new_status: New status value
            
        Returns:
            Success status
        """
        try:
            goal = self.goals_cache.get(goal_id)
            if not goal:
                return False
            
            old_status = goal.status
            goal.status = GoalStatus(new_status.lower())
            goal.last_updated = datetime.utcnow()
            
            logger.info(f"Updated goal {goal_id} status: {old_status.value} -> {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating goal status: {e}")
            return False

    def analyze_goal_conflicts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Analyze conflicts between user's goals.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of detected conflicts
        """
        try:
            user_goals = self.get_user_goals(user_id)
            conflicts = []
            
            for i, goal1 in enumerate(user_goals):
                for goal2 in user_goals[i+1:]:
                    conflict = self._detect_goal_conflict(goal1, goal2)
                    if conflict:
                        conflicts.append(conflict)
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error analyzing goal conflicts: {e}")
            return []

    def _get_default_current_value(self, goal_type: GoalType, target_value: float) -> float:
        """Get intelligent default for current value based on goal type."""
        defaults = {
            GoalType.WEIGHT_LOSS: lambda t: t + 20,  # Start 20 units above target
            GoalType.WEIGHT_GAIN: lambda t: t - 20,  # Start 20 units below target
            GoalType.MUSCLE_GAIN: lambda t: t - 10,
            GoalType.ENDURANCE: lambda t: t * 0.5,   # Start at 50% of target
            GoalType.STRENGTH: lambda t: t * 0.6
        }
        
        if goal_type in defaults:
            return defaults[goal_type](target_value)
        
        return target_value * 0.7  # Default to 70% of target

    def _validate_goal_feasibility(
        self,
        goal_type: GoalType,
        current_value: float,
        target_value: float,
        target_date: datetime
    ) -> Tuple[bool, str]:
        """Validate if goal is feasible given timeframe and values."""
        days_to_target = (target_date - datetime.utcnow()).days
        
        if days_to_target <= 0:
            return False, "Target date must be in the future"
        
        value_difference = abs(target_value - current_value)
        
        # Define safe rates of change per week
        safe_rates = {
            GoalType.WEIGHT_LOSS: 1.0,     # 1 unit per week
            GoalType.WEIGHT_GAIN: 0.5,     # 0.5 units per week
            GoalType.MUSCLE_GAIN: 0.25,    # 0.25 units per week
        }
        
        if goal_type in safe_rates:
            weeks_available = days_to_target / 7
            safe_change = safe_rates[goal_type] * weeks_available
            
            if value_difference > safe_change * 1.5:  # 50% buffer
                return False, f"Target change too aggressive for timeframe"
        
        return True, "Goal appears feasible"

    def _create_milestones(self, goal_id: str, milestone_data: List[Dict[str, Any]]) -> List[Milestone]:
        """Create milestone objects from data."""
        milestones = []
        for i, data in enumerate(milestone_data):
            milestone = Milestone(
                milestone_id=f"{goal_id}_milestone_{i}",
                title=data.get('title', f"Milestone {i+1}"),
                description=data.get('description', ''),
                target_value=data['target_value'],
                current_value=data.get('current_value', 0),
                unit=data['unit'],
                target_date=datetime.fromisoformat(data['target_date'])
            )
            milestones.append(milestone)
        return milestones

    def _generate_default_milestones(
        self,
        goal_id: str,
        goal_type: GoalType,
        current_value: float,
        target_value: float,
        target_date: datetime,
        unit: str
    ) -> List[Milestone]:
        """Generate intelligent default milestones."""
        milestones = []
        
        # Create 3-4 evenly spaced milestones
        value_difference = target_value - current_value
        days_to_target = (target_date - datetime.utcnow()).days
        
        milestone_count = min(4, max(2, days_to_target // 30))  # One milestone per month, max 4
        
        for i in range(1, milestone_count + 1):
            milestone_value = current_value + (value_difference * i / milestone_count)
            milestone_date = datetime.utcnow() + timedelta(days=days_to_target * i / milestone_count)
            
            milestone = Milestone(
                milestone_id=f"{goal_id}_milestone_{i}",
                title=f"Milestone {i}",
                description=f"Reach {milestone_value:.1f} {unit}",
                target_value=milestone_value,
                current_value=current_value,
                unit=unit,
                target_date=milestone_date
            )
            milestones.append(milestone)
        
        return milestones

    def _initialize_success_metrics(self, goal_type: GoalType) -> Dict[str, Any]:
        """Initialize success metrics based on goal type."""
        base_metrics = {
            "consistency_score": 0.0,
            "velocity_score": 0.0,
            "milestone_completion_rate": 0.0,
            "adherence_score": 0.0
        }
        
        # Add goal-specific metrics
        specific_metrics = {
            GoalType.WEIGHT_LOSS: {"weekly_loss_rate": 0.0, "plateau_count": 0},
            GoalType.MUSCLE_GAIN: {"strength_correlation": 0.0, "measurement_consistency": 0.0},
            GoalType.ENDURANCE: {"improvement_rate": 0.0, "session_frequency": 0.0}
        }
        
        if goal_type in specific_metrics:
            base_metrics.update(specific_metrics[goal_type])
        
        return base_metrics

    def _update_goal_status(self, goal: HealthGoal) -> None:
        """Update goal status based on current progress."""
        if goal.current_value == goal.target_value:
            goal.status = GoalStatus.COMPLETED
            return
        
        if not goal.progress_entries:
            goal.status = GoalStatus.NOT_STARTED
            return
        
        # Calculate expected progress
        days_elapsed = (datetime.utcnow() - goal.created_date).days
        days_total = (goal.target_date - goal.created_date).days
        
        if days_total <= 0:
            goal.status = GoalStatus.IN_PROGRESS
            return
        
        expected_progress = days_elapsed / days_total
        actual_progress = self._calculate_goal_progress_percentage(goal) / 100.0
        
        # Determine status based on progress comparison
        if actual_progress >= expected_progress * 1.1:  # 10% ahead
            goal.status = GoalStatus.AHEAD
        elif actual_progress >= expected_progress * 0.9:  # Within 10%
            goal.status = GoalStatus.ON_TRACK
        else:
            goal.status = GoalStatus.BEHIND

    def _calculate_goal_progress_percentage(self, goal: HealthGoal) -> float:
        """Calculate progress percentage for a goal."""
        if goal.target_value == goal.start_value:
            return 100.0 if goal.current_value == goal.target_value else 0.0
        
        progress = abs(goal.current_value - goal.start_value) / abs(goal.target_value - goal.start_value)
        return min(100.0, max(0.0, progress * 100.0))

    def _check_milestone_completions(self, goal: HealthGoal) -> None:
        """Check and update milestone completions."""
        for milestone in goal.milestones:
            if not milestone.completed:
                # Check if milestone target is reached
                if goal.goal_type in [GoalType.WEIGHT_LOSS]:
                    # For weight loss, check if current is <= target
                    if goal.current_value <= milestone.target_value:
                        milestone.completed = True
                        milestone.completed_date = datetime.utcnow()
                        milestone.current_value = goal.current_value
                else:
                    # For other goals, check if current is >= target
                    if goal.current_value >= milestone.target_value:
                        milestone.completed = True
                        milestone.completed_date = datetime.utcnow()
                        milestone.current_value = goal.current_value

    def _update_adaptive_targets(self, goal: HealthGoal) -> None:
        """Update goal targets based on progress patterns."""
        if len(goal.progress_entries) < 5:  # Need sufficient data
            return
        
        # Analyze recent progress trend
        recent_entries = goal.progress_entries[-5:]
        values = [entry.value for entry in recent_entries]
        dates = [entry.timestamp for entry in recent_entries]
        
        if len(set(values)) < 2:  # No variation in values
            return
        
        # Calculate trend (simplified linear regression)
        try:
            # Convert dates to days since first entry
            base_date = dates[0]
            x_values = [(d - base_date).days for d in dates]
            
            # Simple slope calculation
            n = len(x_values)
            sum_x = sum(x_values)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(x_values, values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # Predict completion date based on current trend
            if abs(slope) > 0.001:  # Meaningful progress
                remaining_change = goal.target_value - goal.current_value
                days_to_complete = remaining_change / slope
                
                predicted_completion = datetime.utcnow() + timedelta(days=days_to_complete)
                
                # If significantly ahead of schedule, suggest stretch target
                if predicted_completion < goal.target_date - timedelta(days=30):
                    stretch_factor = 1.2  # 20% more ambitious
                    if goal.goal_type == GoalType.WEIGHT_LOSS:
                        stretch_factor = 0.9  # 10% more weight loss
                    
                    # Don't automatically update, just log suggestion
                    logger.info(f"Goal {goal.goal_id} ahead of schedule - consider stretch target")
                    
        except (ZeroDivisionError, ValueError):
            # Not enough variance for trend analysis
            pass

    def _calculate_goal_success_score(self, goal: HealthGoal) -> float:
        """Calculate overall success score for a goal."""
        scores = []
        
        # Completion score
        if goal.status == GoalStatus.COMPLETED:
            scores.append(1.0)
        else:
            progress_percentage = self._calculate_goal_progress_percentage(goal)
            scores.append(progress_percentage / 100.0)
        
        # Milestone completion rate
        if goal.milestones:
            completed_milestones = len([m for m in goal.milestones if m.completed])
            milestone_rate = completed_milestones / len(goal.milestones)
            scores.append(milestone_rate)
        
        # Consistency score (based on regular progress updates)
        if len(goal.progress_entries) > 1:
            entries = goal.progress_entries
            total_days = (entries[-1].timestamp - entries[0].timestamp).days
            if total_days > 0:
                expected_entries = total_days // 7  # Weekly updates expected
                actual_entries = len(entries)
                consistency = min(1.0, actual_entries / max(1, expected_entries))
                scores.append(consistency)
        
        return statistics.mean(scores) if scores else 0.0

    def _generate_goal_recommendations(self, user_id: str, goals: List[HealthGoal]) -> List[GoalRecommendation]:
        """Generate personalized goal recommendations."""
        recommendations = []
        
        # Analyze current goal performance
        behind_goals = [g for g in goals if g.status == GoalStatus.BEHIND]
        completed_goals = [g for g in goals if g.status == GoalStatus.COMPLETED]
        
        # Recommend adjustments for behind goals
        for goal in behind_goals:
            if len(goal.progress_entries) > 3:
                rec = GoalRecommendation(
                    recommendation_id=f"adjust_{goal.goal_id}",
                    goal_id=goal.goal_id,
                    recommendation_type="adjust_target",
                    title="Consider adjusting your goal timeline",
                    description=f"Your {goal.title} goal is behind schedule. Consider extending the timeline or adjusting the target.",
                    rationale="Current progress indicates the original timeline may be too aggressive",
                    confidence_score=0.8,
                    impact_score=0.7,
                    effort_required="low",
                    suggested_actions=[
                        "Extend target date by 2-4 weeks",
                        "Break down remaining progress into smaller milestones",
                        "Review what's preventing consistent progress"
                    ]
                )
                recommendations.append(rec)
        
        # Recommend new goals based on successful patterns
        if completed_goals:
            successful_types = [g.goal_type for g in completed_goals]
            most_successful = max(set(successful_types), key=successful_types.count)
            
            # Suggest related goal
            related_goals = {
                GoalType.WEIGHT_LOSS: GoalType.MUSCLE_GAIN,
                GoalType.MUSCLE_GAIN: GoalType.STRENGTH,
                GoalType.ENDURANCE: GoalType.GENERAL_HEALTH
            }
            
            if most_successful in related_goals:
                next_goal_type = related_goals[most_successful]
                rec = GoalRecommendation(
                    recommendation_id=f"new_goal_{next_goal_type.value}",
                    goal_id=None,
                    recommendation_type="new_goal",
                    title=f"Ready for a {next_goal_type.value.replace('_', ' ')} goal?",
                    description=f"Based on your success with {most_successful.value}, you might enjoy working on {next_goal_type.value}",
                    rationale="Leveraging successful goal patterns for continuous improvement",
                    confidence_score=0.7,
                    impact_score=0.8,
                    effort_required="medium",
                    suggested_actions=[
                        f"Set a {next_goal_type.value} goal",
                        "Use similar strategies that worked before",
                        "Start with moderate targets"
                    ]
                )
                recommendations.append(rec)
        
        return recommendations

    def _predict_goal_completion(self, goal: HealthGoal) -> Optional[datetime]:
        """Predict when goal will be completed based on current trend."""
        if len(goal.progress_entries) < 3:
            return None
        
        # Use recent progress to predict completion
        recent_entries = goal.progress_entries[-5:]  # Last 5 entries
        
        if len(recent_entries) < 2:
            return None
        
        # Calculate average progress rate
        first_entry = recent_entries[0]
        last_entry = recent_entries[-1]
        
        time_diff = (last_entry.timestamp - first_entry.timestamp).days
        value_diff = last_entry.value - first_entry.value
        
        if time_diff <= 0 or abs(value_diff) < 0.001:
            return None
        
        daily_rate = value_diff / time_diff
        remaining_change = goal.target_value - goal.current_value
        
        if abs(daily_rate) < 0.001:
            return None
        
        days_to_completion = remaining_change / daily_rate
        
        if days_to_completion <= 0:
            return datetime.utcnow()  # Already completed
        
        predicted_date = datetime.utcnow() + timedelta(days=days_to_completion)
        
        # Don't predict more than 2 years in the future
        max_future_date = datetime.utcnow() + timedelta(days=730)
        if predicted_date > max_future_date:
            return None
        
        return predicted_date

    def _detect_goal_conflict(self, goal1: HealthGoal, goal2: HealthGoal) -> Optional[Dict[str, Any]]:
        """Detect conflicts between two goals."""
        # Define conflicting goal types
        conflicts = {
            (GoalType.WEIGHT_LOSS, GoalType.MUSCLE_GAIN): "Simultaneous weight loss and muscle gain can be challenging",
            (GoalType.ENDURANCE, GoalType.STRENGTH): "High-intensity strength and endurance training may conflict",
        }
        
        goal_pair = (goal1.goal_type, goal2.goal_type)
        reverse_pair = (goal2.goal_type, goal1.goal_type)
        
        if goal_pair in conflicts:
            return {
                "goal1_id": goal1.goal_id,
                "goal2_id": goal2.goal_id,
                "conflict_type": "goal_type_conflict",
                "description": conflicts[goal_pair],
                "severity": "medium",
                "suggestion": "Consider focusing on one goal at a time or adjusting timelines"
            }
        elif reverse_pair in conflicts:
            return {
                "goal1_id": goal1.goal_id,
                "goal2_id": goal2.goal_id,
                "conflict_type": "goal_type_conflict",
                "description": conflicts[reverse_pair],
                "severity": "medium",
                "suggestion": "Consider focusing on one goal at a time or adjusting timelines"
            }
        
        # Check timeline conflicts (too many aggressive goals at once)
        if (goal1.priority == GoalPriority.HIGH and goal2.priority == GoalPriority.HIGH and
            abs((goal1.target_date - goal2.target_date).days) < 60):
            return {
                "goal1_id": goal1.goal_id,
                "goal2_id": goal2.goal_id,
                "conflict_type": "timeline_conflict",
                "description": "Multiple high-priority goals with similar timelines",
                "severity": "low",
                "suggestion": "Consider staggering goal timelines for better focus"
            }
        
        return None

    def _analyze_goal_relationships(self, user_id: str, new_goal_id: str) -> None:
        """Analyze relationships between goals for better recommendations."""
        new_goal = self.goals_cache[new_goal_id]
        user_goal_ids = self.user_goals[user_id]
        
        synergistic_goals = []
        conflicting_goals = []
        
        for goal_id in user_goal_ids:
            if goal_id != new_goal_id and goal_id in self.goals_cache:
                other_goal = self.goals_cache[goal_id]
                
                # Check for synergies
                if self._goals_are_synergistic(new_goal, other_goal):
                    synergistic_goals.append(goal_id)
                
                # Check for conflicts
                conflict = self._detect_goal_conflict(new_goal, other_goal)
                if conflict:
                    conflicting_goals.append(goal_id)
        
        # Update related goals
        new_goal.related_goals = synergistic_goals
        
        # Log findings
        if synergistic_goals:
            logger.info(f"Goal {new_goal_id} has synergies with: {synergistic_goals}")
        if conflicting_goals:
            logger.warning(f"Goal {new_goal_id} conflicts with: {conflicting_goals}")

    def _goals_are_synergistic(self, goal1: HealthGoal, goal2: HealthGoal) -> bool:
        """Check if two goals support each other."""
        synergies = {
            (GoalType.WEIGHT_LOSS, GoalType.GENERAL_HEALTH),
            (GoalType.MUSCLE_GAIN, GoalType.STRENGTH),
            (GoalType.ENDURANCE, GoalType.GENERAL_HEALTH),
            (GoalType.BETTER_SLEEP, GoalType.ENERGY_BOOST)
        }
        
        goal_pair = (goal1.goal_type, goal2.goal_type)
        reverse_pair = (goal2.goal_type, goal1.goal_type)
        
        return goal_pair in synergies or reverse_pair in synergies
