"""
Health Goals Manager - Health goals and targets management
Consolidates: health_goals_service.py, target_setting_service.py
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class GoalType(Enum):
    """Types of health goals"""
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    ATHLETIC_PERFORMANCE = "athletic_performance"
    HEALTH_CONDITION = "health_condition"
    NUTRITION_QUALITY = "nutrition_quality"

@dataclass
class HealthGoal:
    """Health goal definition"""
    goal_id: str
    user_id: str
    goal_type: GoalType
    title: str
    description: str
    target_value: float
    current_value: float
    unit: str
    target_date: str
    created_date: str
    priority: str  # high, medium, low
    status: str    # active, paused, completed, cancelled
    progress_percentage: float = 0
    milestones: List[Dict[str, Any]] = None

class HealthGoalsManager:
    """
    Manages user health goals, tracks progress, and provides
    personalized recommendations for goal achievement.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.goals_database = {}  # In-memory storage for demo
        self.goal_templates = self._initialize_goal_templates()
        
    def create_health_goal(
        self,
        user_id: str,
        goal_type: str,
        target_value: float,
        target_date: str,
        current_value: float = 0,
        custom_title: str = None,
        custom_description: str = None
    ) -> Dict[str, Any]:
        """
        Create a new health goal for a user
        
        Args:
            user_id: User identifier
            goal_type: Type of goal (weight_loss, muscle_gain, etc.)
            target_value: Target value to achieve
            target_date: Target completion date
            current_value: Current baseline value
            custom_title: Custom goal title
            custom_description: Custom goal description
            
        Returns:
            Created goal with initial setup
        """
        try:
            goal_enum = GoalType(goal_type)
            template = self.goal_templates.get(goal_type, {})
            
            goal_id = f"{user_id}_{goal_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            goal = HealthGoal(
                goal_id=goal_id,
                user_id=user_id,
                goal_type=goal_enum,
                title=custom_title or template.get('title', f"{goal_type.title()} Goal"),
                description=custom_description or template.get('description', ''),
                target_value=target_value,
                current_value=current_value,
                unit=template.get('unit', 'units'),
                target_date=target_date,
                created_date=datetime.now().isoformat(),
                priority=template.get('default_priority', 'medium'),
                status='active',
                milestones=self._create_milestones(goal_type, current_value, target_value, target_date)
            )
            
            # Calculate initial progress
            goal.progress_percentage = self._calculate_progress(goal)
            
            # Store goal
            self.goals_database[goal_id] = goal
            
            # Generate initial recommendations
            recommendations = self._generate_goal_recommendations(goal)
            
            result = asdict(goal)
            result.update({
                'initial_recommendations': recommendations,
                'estimated_timeline': self._estimate_timeline(goal),
                'success_probability': self._estimate_success_probability(goal)
            })
            
            self.logger.info(f"Created health goal: {goal.title} for user {user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating health goal: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def update_goal_progress(
        self,
        goal_id: str,
        new_value: float,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Update progress on a health goal
        
        Args:
            goal_id: Goal identifier
            new_value: New current value
            notes: Optional progress notes
            
        Returns:
            Updated goal with progress analysis
        """
        try:
            if goal_id not in self.goals_database:
                return {'error': 'Goal not found', 'success': False}
            
            goal = self.goals_database[goal_id]
            previous_value = goal.current_value
            goal.current_value = new_value
            
            # Recalculate progress
            goal.progress_percentage = self._calculate_progress(goal)
            
            # Log progress entry
            progress_entry = {
                'date': datetime.now().isoformat(),
                'value': new_value,
                'change': new_value - previous_value,
                'notes': notes,
                'progress_percentage': goal.progress_percentage
            }
            
            # Check milestone achievements
            milestone_updates = self._check_milestone_achievements(goal, previous_value)
            
            # Generate updated recommendations
            recommendations = self._generate_progress_recommendations(goal, progress_entry)
            
            # Check if goal is completed
            if goal.progress_percentage >= 100:
                goal.status = 'completed'
                recommendations.append("Congratulations! You've achieved your goal!")
            
            result = {
                'goal': asdict(goal),
                'progress_entry': progress_entry,
                'milestone_updates': milestone_updates,
                'recommendations': recommendations,
                'trend_analysis': self._analyze_progress_trend(goal_id)
            }
            
            self.logger.info(f"Updated progress for goal {goal_id}: {new_value} {goal.unit}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error updating goal progress: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def get_user_goals(
        self,
        user_id: str,
        status_filter: str = None,
        goal_type_filter: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all goals for a user with optional filtering
        
        Args:
            user_id: User identifier
            status_filter: Filter by status (active, completed, etc.)
            goal_type_filter: Filter by goal type
            
        Returns:
            List of user's goals with current status
        """
        try:
            user_goals = [
                goal for goal in self.goals_database.values()
                if goal.user_id == user_id
            ]
            
            # Apply filters
            if status_filter:
                user_goals = [g for g in user_goals if g.status == status_filter]
            
            if goal_type_filter:
                user_goals = [g for g in user_goals if g.goal_type.value == goal_type_filter]
            
            # Convert to dict and add analysis
            goals_with_analysis = []
            for goal in user_goals:
                goal_dict = asdict(goal)
                goal_dict.update({
                    'days_remaining': self._calculate_days_remaining(goal),
                    'weekly_target_change': self._calculate_weekly_target(goal),
                    'on_track_status': self._assess_on_track_status(goal)
                })
                goals_with_analysis.append(goal_dict)
            
            # Sort by priority and creation date
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            goals_with_analysis.sort(
                key=lambda g: (priority_order.get(g['priority'], 1), g['created_date'])
            )
            
            return goals_with_analysis
            
        except Exception as e:
            self.logger.error(f"Error getting user goals: {str(e)}")
            return []
    
    def suggest_goal_adjustments(
        self,
        goal_id: str
    ) -> Dict[str, Any]:
        """
        Suggest adjustments to make goal more achievable
        
        Args:
            goal_id: Goal identifier
            
        Returns:
            Suggested adjustments and rationale
        """
        try:
            if goal_id not in self.goals_database:
                return {'error': 'Goal not found'}
            
            goal = self.goals_database[goal_id]
            suggestions = {
                'timeline_adjustments': [],
                'target_adjustments': [],
                'strategy_adjustments': [],
                'support_recommendations': []
            }
            
            # Analyze current progress rate
            progress_rate = self._calculate_progress_rate(goal)
            days_remaining = self._calculate_days_remaining(goal)
            
            # Timeline adjustments
            if progress_rate < 0.5 and days_remaining > 0:  # Slow progress
                realistic_date = self._calculate_realistic_completion_date(goal, progress_rate)
                suggestions['timeline_adjustments'].append({
                    'type': 'extend_deadline',
                    'suggestion': f"Consider extending deadline to {realistic_date}",
                    'rationale': "Current progress rate suggests more time needed"
                })
            
            # Target adjustments
            if goal.progress_percentage < 20 and days_remaining < 30:  # Behind schedule
                adjusted_target = goal.current_value + (goal.target_value - goal.current_value) * 0.7
                suggestions['target_adjustments'].append({
                    'type': 'reduce_target',
                    'suggestion': f"Consider adjusting target to {adjusted_target:.1f} {goal.unit}",
                    'rationale': "More achievable target based on current progress"
                })
            
            # Strategy adjustments
            strategy_suggestions = self._generate_strategy_adjustments(goal)
            suggestions['strategy_adjustments'] = strategy_suggestions
            
            # Support recommendations
            support_suggestions = self._generate_support_recommendations(goal)
            suggestions['support_recommendations'] = support_suggestions
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error suggesting goal adjustments: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_progress(self, goal: HealthGoal) -> float:
        """Calculate progress percentage for a goal"""
        if goal.target_value == goal.current_value:
            return 100.0
        
        if goal.goal_type in [GoalType.WEIGHT_LOSS]:
            # For weight loss, progress towards lower target
            total_change_needed = abs(goal.target_value - goal.current_value)
            current_change = abs(goal.current_value - goal.target_value)
            
            if goal.current_value <= goal.target_value:
                return 100.0  # Goal achieved
            else:
                progress = ((goal.current_value - goal.target_value) / total_change_needed) * 100
                return min(100.0, max(0.0, progress))
        else:
            # For other goals, progress towards higher target
            if goal.current_value >= goal.target_value:
                return 100.0
            else:
                total_change_needed = goal.target_value - goal.current_value
                current_progress = goal.current_value - goal.current_value  # This needs baseline
                return min(100.0, max(0.0, (current_progress / total_change_needed) * 100))
    
    def _create_milestones(
        self,
        goal_type: str,
        start_value: float,
        target_value: float,
        target_date: str
    ) -> List[Dict[str, Any]]:
        """Create milestone markers for goal tracking"""
        milestones = []
        
        # Create 4 quarterly milestones
        for i in range(1, 5):
            milestone_value = start_value + (target_value - start_value) * (i / 4)
            milestone_date = self._calculate_milestone_date(target_date, i)
            
            milestones.append({
                'milestone_id': f"milestone_{i}",
                'target_value': milestone_value,
                'target_date': milestone_date,
                'achieved': False,
                'achieved_date': None,
                'description': f"{i * 25}% progress milestone"
            })
        
        return milestones
    
    def _calculate_milestone_date(self, target_date: str, quarter: int) -> str:
        """Calculate milestone target date"""
        target_dt = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
        start_dt = datetime.now()
        
        total_days = (target_dt - start_dt).days
        milestone_days = (total_days * quarter) // 4
        
        milestone_dt = start_dt + timedelta(days=milestone_days)
        return milestone_dt.isoformat()
    
    def _generate_goal_recommendations(self, goal: HealthGoal) -> List[str]:
        """Generate initial recommendations for goal achievement"""
        recommendations = []
        
        goal_type = goal.goal_type.value
        
        if goal_type == 'weight_loss':
            recommendations.extend([
                "Create a moderate calorie deficit of 300-500 calories per day",
                "Focus on whole foods and increase protein intake",
                "Incorporate both cardio and strength training",
                "Track your food intake daily for awareness"
            ])
        elif goal_type == 'muscle_gain':
            recommendations.extend([
                "Maintain a slight calorie surplus (200-500 calories)",
                "Aim for 1.6-2.2g protein per kg body weight",
                "Focus on progressive resistance training",
                "Ensure adequate sleep (7-9 hours) for recovery"
            ])
        elif goal_type == 'athletic_performance':
            recommendations.extend([
                "Periodize your training with progressive overload",
                "Focus on sport-specific nutrition timing",
                "Prioritize recovery and injury prevention",
                "Consider working with a sports nutritionist"
            ])
        
        return recommendations
    
    def _estimate_timeline(self, goal: HealthGoal) -> Dict[str, Any]:
        """Estimate realistic timeline for goal achievement"""
        goal_type = goal.goal_type.value
        
        # Safe rates of change per week
        safe_rates = {
            'weight_loss': 0.5,  # kg per week
            'weight_gain': 0.25, # kg per week
            'muscle_gain': 0.1,  # kg per week
        }
        
        safe_rate = safe_rates.get(goal_type, 0.5)
        change_needed = abs(goal.target_value - goal.current_value)
        
        estimated_weeks = change_needed / safe_rate if safe_rate > 0 else 12
        estimated_date = datetime.now() + timedelta(weeks=estimated_weeks)
        
        return {
            'estimated_weeks': estimated_weeks,
            'estimated_completion_date': estimated_date.isoformat(),
            'recommended_weekly_change': safe_rate,
            'is_realistic': estimated_weeks <= 52  # Within a year
        }
    
    def _estimate_success_probability(self, goal: HealthGoal) -> float:
        """Estimate probability of goal success based on various factors"""
        factors = []
        
        # Timeline realism
        timeline_estimate = self._estimate_timeline(goal)
        if timeline_estimate['is_realistic']:
            factors.append(80)
        else:
            factors.append(40)
        
        # Goal size (smaller goals are more achievable)
        change_percent = abs(goal.target_value - goal.current_value) / goal.current_value * 100
        if change_percent <= 10:
            factors.append(90)
        elif change_percent <= 20:
            factors.append(70)
        else:
            factors.append(50)
        
        # Priority level
        priority_scores = {'high': 85, 'medium': 70, 'low': 55}
        factors.append(priority_scores.get(goal.priority, 70))
        
        return sum(factors) / len(factors) if factors else 50
    
    def _generate_progress_recommendations(
        self,
        goal: HealthGoal,
        progress_entry: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on progress"""
        recommendations = []
        
        change = progress_entry['change']
        progress_pct = progress_entry['progress_percentage']
        
        if change > 0:
            recommendations.append("Great progress! Keep up the good work.")
        elif change == 0:
            recommendations.append("No change this period. Consider adjusting your approach.")
        else:
            recommendations.append("Temporary setback is normal. Stay focused on your plan.")
        
        if progress_pct < 25:
            recommendations.append("Consider increasing the intensity of your efforts.")
        elif progress_pct > 75:
            recommendations.append("You're close to your goal! Maintain consistency.")
        
        return recommendations
    
    def _check_milestone_achievements(
        self,
        goal: HealthGoal,
        previous_value: float
    ) -> List[Dict[str, Any]]:
        """Check if any milestones were achieved with this update"""
        achievements = []
        
        if not goal.milestones:
            return achievements
        
        for milestone in goal.milestones:
            if not milestone['achieved']:
                target_val = milestone['target_value']
                
                # Check if milestone was reached
                if goal.goal_type == GoalType.WEIGHT_LOSS:
                    achieved = goal.current_value <= target_val and previous_value > target_val
                else:
                    achieved = goal.current_value >= target_val and previous_value < target_val
                
                if achieved:
                    milestone['achieved'] = True
                    milestone['achieved_date'] = datetime.now().isoformat()
                    achievements.append({
                        'milestone_id': milestone['milestone_id'],
                        'description': milestone['description'],
                        'achieved_date': milestone['achieved_date']
                    })
        
        return achievements
    
    def _analyze_progress_trend(self, goal_id: str) -> Dict[str, Any]:
        """Analyze progress trend over time"""
        # Placeholder for trend analysis
        return {
            'trend_direction': 'positive',
            'consistency_score': 75,
            'acceleration': 'steady',
            'prediction': 'on_track'
        }
    
    def _calculate_days_remaining(self, goal: HealthGoal) -> int:
        """Calculate days remaining until target date"""
        target_dt = datetime.fromisoformat(goal.target_date.replace('Z', '+00:00'))
        now_dt = datetime.now()
        
        return (target_dt - now_dt).days
    
    def _calculate_weekly_target(self, goal: HealthGoal) -> float:
        """Calculate weekly target change needed"""
        days_remaining = self._calculate_days_remaining(goal)
        if days_remaining <= 0:
            return 0
        
        change_needed = goal.target_value - goal.current_value
        weeks_remaining = days_remaining / 7
        
        return change_needed / weeks_remaining if weeks_remaining > 0 else 0
    
    def _assess_on_track_status(self, goal: HealthGoal) -> str:
        """Assess if goal is on track"""
        progress_pct = goal.progress_percentage
        days_remaining = self._calculate_days_remaining(goal)
        
        # Calculate expected progress based on time elapsed
        target_dt = datetime.fromisoformat(goal.target_date.replace('Z', '+00:00'))
        start_dt = datetime.fromisoformat(goal.created_date.replace('Z', '+00:00'))
        total_days = (target_dt - start_dt).days
        elapsed_days = (datetime.now() - start_dt).days
        
        expected_progress = (elapsed_days / total_days) * 100 if total_days > 0 else 0
        
        if progress_pct >= expected_progress * 1.1:
            return 'ahead'
        elif progress_pct >= expected_progress * 0.9:
            return 'on_track'
        else:
            return 'behind'
    
    def _calculate_progress_rate(self, goal: HealthGoal) -> float:
        """Calculate progress rate per day"""
        start_dt = datetime.fromisoformat(goal.created_date.replace('Z', '+00:00'))
        elapsed_days = (datetime.now() - start_dt).days
        
        if elapsed_days == 0:
            return 0
        
        return goal.progress_percentage / elapsed_days
    
    def _calculate_realistic_completion_date(self, goal: HealthGoal, progress_rate: float) -> str:
        """Calculate realistic completion date based on current progress rate"""
        remaining_progress = 100 - goal.progress_percentage
        
        if progress_rate > 0:
            days_needed = remaining_progress / progress_rate
            completion_date = datetime.now() + timedelta(days=days_needed)
            return completion_date.strftime('%Y-%m-%d')
        
        return goal.target_date
    
    def _generate_strategy_adjustments(self, goal: HealthGoal) -> List[Dict[str, str]]:
        """Generate strategy adjustment suggestions"""
        return [
            {
                'type': 'frequency',
                'suggestion': 'Increase tracking frequency to daily',
                'rationale': 'More frequent monitoring improves adherence'
            },
            {
                'type': 'approach',
                'suggestion': 'Break goal into smaller weekly targets',
                'rationale': 'Smaller targets feel more achievable'
            }
        ]
    
    def _generate_support_recommendations(self, goal: HealthGoal) -> List[Dict[str, str]]:
        """Generate support recommendations"""
        return [
            {
                'type': 'accountability',
                'suggestion': 'Find an accountability partner',
                'rationale': 'Social support increases success rates'
            },
            {
                'type': 'professional',
                'suggestion': 'Consider consulting a professional',
                'rationale': 'Expert guidance can optimize your approach'
            }
        ]
    
    def _initialize_goal_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize goal templates with defaults"""
        return {
            'weight_loss': {
                'title': 'Weight Loss Goal',
                'description': 'Achieve healthy weight loss through balanced nutrition and exercise',
                'unit': 'kg',
                'default_priority': 'high'
            },
            'muscle_gain': {
                'title': 'Muscle Building Goal',
                'description': 'Build lean muscle mass through strength training and proper nutrition',
                'unit': 'kg',
                'default_priority': 'medium'
            },
            'athletic_performance': {
                'title': 'Performance Enhancement',
                'description': 'Improve athletic performance through targeted training and nutrition',
                'unit': 'score',
                'default_priority': 'high'
            },
            'nutrition_quality': {
                'title': 'Nutrition Quality Improvement',
                'description': 'Enhance overall nutrition quality and dietary habits',
                'unit': 'score',
                'default_priority': 'medium'
            }
        }
