"""
Nutrition Insights - Generate insights and recommendations
Consolidates: nutrition_insights_service.py, recommendation_service.py
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)

@dataclass
class NutritionInsight:
    """Single nutrition insight"""
    insight_id: str
    category: str
    title: str
    description: str
    priority: str  # high, medium, low
    confidence: float  # 0-100
    data_source: str
    recommendations: List[str]
    timestamp: str

class NutritionInsights:
    """
    Generates intelligent nutrition insights and personalized
    recommendations based on user data and patterns.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.insight_generators = self._initialize_insight_generators()
        
    def generate_comprehensive_insights(
        self,
        user_id: str,
        nutrition_data: List[Dict[str, Any]],
        goals: List[Dict[str, Any]] = None,
        timeframe_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate comprehensive nutrition insights for a user
        
        Args:
            user_id: User identifier
            nutrition_data: Historical nutrition data
            goals: User's health goals
            timeframe_days: Analysis timeframe in days
            
        Returns:
            Comprehensive insights report
        """
        try:
            self.logger.info(f"Generating insights for user {user_id} over {timeframe_days} days")
            
            insights_report = {
                'user_id': user_id,
                'analysis_period': {
                    'days': timeframe_days,
                    'start_date': (datetime.now() - timedelta(days=timeframe_days)).isoformat()[:10],
                    'end_date': datetime.now().isoformat()[:10]
                },
                'insights': [],
                'key_patterns': [],
                'recommendations': [],
                'action_items': [],
                'scores': {}
            }
            
            # Generate different types of insights
            pattern_insights = self._analyze_patterns(nutrition_data, timeframe_days)
            goal_insights = self._analyze_goal_progress(nutrition_data, goals)
            nutrient_insights = self._analyze_nutrient_trends(nutrition_data)
            timing_insights = self._analyze_meal_timing(nutrition_data)
            quality_insights = self._analyze_nutrition_quality(nutrition_data)
            
            # Combine all insights
            all_insights = (
                pattern_insights + goal_insights + nutrient_insights + 
                timing_insights + quality_insights
            )
            
            # Sort by priority and confidence
            all_insights.sort(key=lambda x: (
                {'high': 0, 'medium': 1, 'low': 2}[x.priority],
                -x.confidence
            ))
            
            insights_report['insights'] = [self._insight_to_dict(i) for i in all_insights[:10]]
            
            # Extract key patterns
            insights_report['key_patterns'] = self._extract_key_patterns(nutrition_data)
            
            # Generate prioritized recommendations
            insights_report['recommendations'] = self._generate_prioritized_recommendations(all_insights)
            
            # Create action items
            insights_report['action_items'] = self._create_action_items(all_insights[:5])
            
            # Calculate scores
            insights_report['scores'] = self._calculate_insight_scores(nutrition_data)
            
            return insights_report
            
        except Exception as e:
            self.logger.error(f"Error generating insights: {str(e)}")
            return {'error': str(e), 'insights': []}
    
    def get_daily_insights(
        self,
        user_id: str,
        current_day_data: Dict[str, Any],
        recent_history: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate daily nutrition insights and tips
        
        Args:
            user_id: User identifier
            current_day_data: Today's nutrition data
            recent_history: Recent days' nutrition data
            
        Returns:
            List of daily insights and tips
        """
        try:
            daily_insights = []
            
            # Analyze today's intake
            today_analysis = self._analyze_daily_intake(current_day_data)
            daily_insights.extend(today_analysis)
            
            # Compare with recent history
            if recent_history:
                comparison_insights = self._compare_with_history(current_day_data, recent_history)
                daily_insights.extend(comparison_insights)
            
            # Generate immediate recommendations
            immediate_recs = self._generate_immediate_recommendations(current_day_data)
            daily_insights.extend(immediate_recs)
            
            return daily_insights
            
        except Exception as e:
            self.logger.error(f"Error generating daily insights: {str(e)}")
            return []
    
    def analyze_nutrient_gaps(
        self,
        nutrition_data: List[Dict[str, Any]],
        target_nutrition: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Analyze nutrient gaps and deficiencies
        
        Args:
            nutrition_data: Historical nutrition data
            target_nutrition: Target nutrition values
            
        Returns:
            Nutrient gap analysis
        """
        try:
            if not nutrition_data:
                return {'error': 'No nutrition data provided'}
            
            # Default targets
            if not target_nutrition:
                target_nutrition = {
                    'protein': 150, 'fiber': 25, 'calcium': 1000,
                    'iron': 8, 'vitamin_c': 90, 'vitamin_d': 15
                }
            
            gap_analysis = {
                'nutrient_adequacy': {},
                'consistent_gaps': [],
                'occasional_gaps': [],
                'surplus_nutrients': [],
                'recommendations': []
            }
            
            # Calculate average intake for each nutrient
            nutrient_averages = self._calculate_nutrient_averages(nutrition_data)
            
            # Analyze each nutrient
            for nutrient, target in target_nutrition.items():
                average_intake = nutrient_averages.get(nutrient, 0)
                adequacy_percent = (average_intake / target) * 100 if target > 0 else 0
                
                gap_analysis['nutrient_adequacy'][nutrient] = {
                    'average_intake': average_intake,
                    'target': target,
                    'adequacy_percent': adequacy_percent,
                    'gap': max(0, target - average_intake),
                    'status': self._classify_adequacy(adequacy_percent)
                }
                
                # Classify gaps
                if adequacy_percent < 50:
                    gap_analysis['consistent_gaps'].append(nutrient)
                elif adequacy_percent < 80:
                    gap_analysis['occasional_gaps'].append(nutrient)
                elif adequacy_percent > 150:
                    gap_analysis['surplus_nutrients'].append(nutrient)
            
            # Generate gap-specific recommendations
            gap_analysis['recommendations'] = self._generate_gap_recommendations(gap_analysis)
            
            return gap_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing nutrient gaps: {str(e)}")
            return {'error': str(e)}
    
    def identify_eating_patterns(
        self,
        nutrition_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Identify eating patterns and behaviors
        
        Args:
            nutrition_data: Historical nutrition data with timestamps
            
        Returns:
            Eating pattern analysis
        """
        try:
            pattern_analysis = {
                'meal_frequency': {},
                'timing_patterns': {},
                'weekend_vs_weekday': {},
                'portion_consistency': {},
                'eating_window': {},
                'behavioral_insights': []
            }
            
            # Analyze meal frequency
            pattern_analysis['meal_frequency'] = self._analyze_meal_frequency(nutrition_data)
            
            # Analyze timing patterns
            pattern_analysis['timing_patterns'] = self._analyze_timing_patterns(nutrition_data)
            
            # Weekend vs weekday comparison
            pattern_analysis['weekend_vs_weekday'] = self._compare_weekend_weekday(nutrition_data)
            
            # Portion consistency
            pattern_analysis['portion_consistency'] = self._analyze_portion_consistency(nutrition_data)
            
            # Eating window analysis
            pattern_analysis['eating_window'] = self._analyze_eating_window(nutrition_data)
            
            # Generate behavioral insights
            pattern_analysis['behavioral_insights'] = self._generate_behavioral_insights(pattern_analysis)
            
            return pattern_analysis
            
        except Exception as e:
            self.logger.error(f"Error identifying eating patterns: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_patterns(self, nutrition_data: List[Dict[str, Any]], days: int) -> List[NutritionInsight]:
        """Analyze nutrition patterns and trends"""
        insights = []
        
        if len(nutrition_data) < 3:
            return insights
        
        # Calorie consistency analysis
        daily_calories = [day.get('total_calories', 0) for day in nutrition_data[-7:]]
        if daily_calories:
            cv = statistics.stdev(daily_calories) / statistics.mean(daily_calories) if statistics.mean(daily_calories) > 0 else 0
            
            if cv > 0.3:  # High variability
                insights.append(NutritionInsight(
                    insight_id="calorie_variability",
                    category="patterns",
                    title="Inconsistent Calorie Intake",
                    description=f"Your daily calories vary significantly (CV: {cv:.1%})",
                    priority="medium",
                    confidence=85,
                    data_source="calorie_tracking",
                    recommendations=[
                        "Try to maintain more consistent meal sizes",
                        "Plan your meals in advance",
                        "Consider setting daily calorie targets"
                    ],
                    timestamp=datetime.now().isoformat()
                ))
        
        return insights
    
    def _analyze_goal_progress(self, nutrition_data: List[Dict[str, Any]], goals: List[Dict[str, Any]]) -> List[NutritionInsight]:
        """Analyze progress toward health goals"""
        insights = []
        
        if not goals:
            return insights
        
        for goal in goals:
            if goal.get('status') == 'active':
                progress = goal.get('progress_percentage', 0)
                
                if progress < 25:
                    insights.append(NutritionInsight(
                        insight_id=f"goal_progress_{goal.get('goal_id')}",
                        category="goals",
                        title=f"Slow Progress on {goal.get('title')}",
                        description=f"You're at {progress:.1f}% progress. Consider adjusting your approach.",
                        priority="high",
                        confidence=90,
                        data_source="goal_tracking",
                        recommendations=[
                            "Review your current strategy",
                            "Consider increasing effort intensity",
                            "Break goal into smaller milestones"
                        ],
                        timestamp=datetime.now().isoformat()
                    ))
        
        return insights
    
    def _analyze_nutrient_trends(self, nutrition_data: List[Dict[str, Any]]) -> List[NutritionInsight]:
        """Analyze nutrient intake trends"""
        insights = []
        
        if len(nutrition_data) < 5:
            return insights
        
        # Fiber trend analysis
        recent_fiber = [day.get('total_fiber', 0) for day in nutrition_data[-7:]]
        avg_fiber = statistics.mean(recent_fiber) if recent_fiber else 0
        
        if avg_fiber < 20:  # Below recommended intake
            insights.append(NutritionInsight(
                insight_id="low_fiber",
                category="nutrients",
                title="Low Fiber Intake",
                description=f"Average fiber intake is {avg_fiber:.1f}g, below the recommended 25g",
                priority="medium",
                confidence=95,
                data_source="nutrient_tracking",
                recommendations=[
                    "Include more vegetables and fruits",
                    "Choose whole grain options",
                    "Add legumes to your meals"
                ],
                timestamp=datetime.now().isoformat()
            ))
        
        return insights
    
    def _analyze_meal_timing(self, nutrition_data: List[Dict[str, Any]]) -> List[NutritionInsight]:
        """Analyze meal timing patterns"""
        insights = []
        
        # This would analyze meal timestamps if available
        # For now, return placeholder insight
        insights.append(NutritionInsight(
            insight_id="meal_timing",
            category="timing",
            title="Meal Timing Analysis",
            description="Consider eating at more regular intervals",
            priority="low",
            confidence=70,
            data_source="timing_analysis",
            recommendations=[
                "Try to eat meals at consistent times",
                "Don't skip breakfast",
                "Have your largest meal mid-day"
            ],
            timestamp=datetime.now().isoformat()
        ))
        
        return insights
    
    def _analyze_nutrition_quality(self, nutrition_data: List[Dict[str, Any]]) -> List[NutritionInsight]:
        """Analyze overall nutrition quality"""
        insights = []
        
        if not nutrition_data:
            return insights
        
        # Protein adequacy
        recent_protein = [day.get('total_protein', 0) for day in nutrition_data[-7:]]
        avg_protein = statistics.mean(recent_protein) if recent_protein else 0
        
        if avg_protein < 100:  # Below minimum for most adults
            insights.append(NutritionInsight(
                insight_id="protein_adequacy",
                category="quality",
                title="Protein Intake Below Optimal",
                description=f"Average protein intake is {avg_protein:.1f}g. Consider increasing.",
                priority="medium",
                confidence=85,
                data_source="nutrient_analysis",
                recommendations=[
                    "Include protein at every meal",
                    "Consider lean meats, fish, or plant proteins",
                    "Add protein-rich snacks"
                ],
                timestamp=datetime.now().isoformat()
            ))
        
        return insights
    
    def _analyze_daily_intake(self, daily_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze single day's intake"""
        insights = []
        
        calories = daily_data.get('total_calories', 0)
        protein = daily_data.get('total_protein', 0)
        
        if calories < 1200:
            insights.append({
                'type': 'warning',
                'title': 'Low Calorie Intake',
                'message': f'Today\'s calories ({calories}) are below minimum recommendations',
                'priority': 'high'
            })
        
        if protein < 50:
            insights.append({
                'type': 'tip',
                'title': 'Protein Boost',
                'message': 'Consider adding protein to your next meal',
                'priority': 'medium'
            })
        
        return insights
    
    def _compare_with_history(self, current_data: Dict[str, Any], history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare current day with historical average"""
        insights = []
        
        if not history:
            return insights
        
        # Calculate historical averages
        avg_calories = statistics.mean([day.get('total_calories', 0) for day in history])
        current_calories = current_data.get('total_calories', 0)
        
        if current_calories > avg_calories * 1.2:
            insights.append({
                'type': 'alert',
                'title': 'Above Average Intake',
                'message': f'Today\'s calories are {((current_calories/avg_calories-1)*100):.0f}% above your average',
                'priority': 'medium'
            })
        
        return insights
    
    def _generate_immediate_recommendations(self, daily_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate immediate actionable recommendations"""
        recommendations = []
        
        fiber = daily_data.get('total_fiber', 0)
        if fiber < 15:
            recommendations.append({
                'type': 'recommendation',
                'title': 'Add Fiber',
                'message': 'Include a serving of vegetables or fruit with your next meal',
                'priority': 'medium'
            })
        
        return recommendations
    
    def _extract_key_patterns(self, nutrition_data: List[Dict[str, Any]]) -> List[str]:
        """Extract key patterns from nutrition data"""
        patterns = []
        
        if len(nutrition_data) >= 7:
            # Weekly calorie pattern
            calories = [day.get('total_calories', 0) for day in nutrition_data[-7:]]
            if statistics.stdev(calories) > 300:
                patterns.append("Highly variable daily calorie intake")
            
            # Protein consistency
            protein = [day.get('total_protein', 0) for day in nutrition_data[-7:]]
            if all(p >= 100 for p in protein):
                patterns.append("Consistently meeting protein targets")
        
        return patterns
    
    def _generate_prioritized_recommendations(self, insights: List[NutritionInsight]) -> List[str]:
        """Generate prioritized recommendations from insights"""
        recommendations = []
        
        # Extract recommendations from high-priority insights
        high_priority_insights = [i for i in insights if i.priority == 'high']
        for insight in high_priority_insights[:3]:
            recommendations.extend(insight.recommendations[:2])  # Top 2 from each
        
        return list(set(recommendations))  # Remove duplicates
    
    def _create_action_items(self, top_insights: List[NutritionInsight]) -> List[Dict[str, Any]]:
        """Create specific action items from insights"""
        action_items = []
        
        for insight in top_insights:
            if insight.recommendations:
                action_items.append({
                    'title': insight.title,
                    'action': insight.recommendations[0],
                    'priority': insight.priority,
                    'category': insight.category
                })
        
        return action_items
    
    def _calculate_insight_scores(self, nutrition_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate various nutrition scores"""
        scores = {}
        
        if nutrition_data:
            recent_data = nutrition_data[-7:] if len(nutrition_data) >= 7 else nutrition_data
            
            # Consistency score
            calories = [day.get('total_calories', 0) for day in recent_data]
            if calories:
                cv = statistics.stdev(calories) / statistics.mean(calories) if statistics.mean(calories) > 0 else 1
                scores['consistency_score'] = max(0, 100 - (cv * 100))
            
            # Balance score (simplified)
            protein_avg = statistics.mean([day.get('total_protein', 0) for day in recent_data])
            scores['balance_score'] = min(100, (protein_avg / 150) * 100)
        
        return scores
    
    def _calculate_nutrient_averages(self, nutrition_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate average nutrient intake"""
        if not nutrition_data:
            return {}
        
        nutrient_sums = {}
        for day in nutrition_data:
            for nutrient, value in day.items():
                if isinstance(value, (int, float)):
                    nutrient_sums[nutrient] = nutrient_sums.get(nutrient, 0) + value
        
        days = len(nutrition_data)
        return {nutrient: total / days for nutrient, total in nutrient_sums.items()}
    
    def _classify_adequacy(self, adequacy_percent: float) -> str:
        """Classify nutrient adequacy level"""
        if adequacy_percent >= 100:
            return "adequate"
        elif adequacy_percent >= 80:
            return "borderline"
        elif adequacy_percent >= 50:
            return "insufficient"
        else:
            return "deficient"
    
    def _generate_gap_recommendations(self, gap_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on nutrient gaps"""
        recommendations = []
        
        consistent_gaps = gap_analysis.get('consistent_gaps', [])
        for nutrient in consistent_gaps:
            if nutrient == 'fiber':
                recommendations.append("Increase fiber with whole grains, fruits, and vegetables")
            elif nutrient == 'protein':
                recommendations.append("Add lean protein sources to each meal")
            elif nutrient == 'calcium':
                recommendations.append("Include dairy, leafy greens, or fortified foods")
        
        return recommendations
    
    def _analyze_meal_frequency(self, nutrition_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze meal frequency patterns"""
        # Placeholder implementation
        return {
            'average_meals_per_day': 3.2,
            'consistency_score': 75,
            'recommendation': 'Consider adding healthy snacks between meals'
        }
    
    def _analyze_timing_patterns(self, nutrition_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze meal timing patterns"""
        # Placeholder implementation
        return {
            'average_first_meal': '07:30',
            'average_last_meal': '19:45',
            'eating_window_hours': 12.25,
            'consistency_score': 68
        }
    
    def _compare_weekend_weekday(self, nutrition_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare weekend vs weekday eating patterns"""
        # Placeholder implementation
        return {
            'weekday_avg_calories': 2100,
            'weekend_avg_calories': 2400,
            'difference_percent': 14.3,
            'pattern': 'higher_weekend_intake'
        }
    
    def _analyze_portion_consistency(self, nutrition_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze portion size consistency"""
        # Placeholder implementation
        return {
            'consistency_score': 72,
            'variability': 'moderate',
            'recommendation': 'Use measuring tools for more consistent portions'
        }
    
    def _analyze_eating_window(self, nutrition_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze daily eating window"""
        # Placeholder implementation
        return {
            'average_window_hours': 12.5,
            'consistency_score': 80,
            'pattern': 'normal_eating_window'
        }
    
    def _generate_behavioral_insights(self, pattern_analysis: Dict[str, Any]) -> List[str]:
        """Generate behavioral insights from patterns"""
        insights = []
        
        eating_window = pattern_analysis.get('eating_window', {})
        if eating_window.get('average_window_hours', 0) > 14:
            insights.append("Consider shortening your eating window for better metabolic health")
        
        weekend_pattern = pattern_analysis.get('weekend_vs_weekday', {})
        if weekend_pattern.get('difference_percent', 0) > 20:
            insights.append("Weekend eating differs significantly from weekdays")
        
        return insights
    
    def _insight_to_dict(self, insight: NutritionInsight) -> Dict[str, Any]:
        """Convert insight object to dictionary"""
        return {
            'insight_id': insight.insight_id,
            'category': insight.category,
            'title': insight.title,
            'description': insight.description,
            'priority': insight.priority,
            'confidence': insight.confidence,
            'data_source': insight.data_source,
            'recommendations': insight.recommendations,
            'timestamp': insight.timestamp
        }
    
    def _initialize_insight_generators(self) -> Dict[str, Any]:
        """Initialize insight generation rules"""
        return {
            'calorie_patterns': {
                'enabled': True,
                'min_data_points': 5,
                'thresholds': {'high_variability': 0.3}
            },
            'nutrient_adequacy': {
                'enabled': True,
                'min_data_points': 3,
                'targets': {'fiber': 25, 'protein': 150}
            }
        }
