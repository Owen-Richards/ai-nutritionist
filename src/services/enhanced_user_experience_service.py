"""
Enhanced User Experience Service
Provides personalized interactions, smart recommendations, and adaptive user journeys.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class EnhancedUserExperienceService:
    """Personalized user experience with adaptive learning"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        
        # User experience tables
        self.user_profile_table = self.dynamodb.Table('ai-nutritionist-user-profiles')
        self.interaction_history_table = self.dynamodb.Table('ai-nutritionist-interactions')
        self.personalization_table = self.dynamodb.Table('ai-nutritionist-personalization')
        self.feedback_table = self.dynamodb.Table('ai-nutritionist-feedback')
        
        # Personalization weights and factors
        self.personalization_factors = {
            'dietary_preferences': 0.30,
            'interaction_frequency': 0.20,
            'feedback_sentiment': 0.25,
            'conversion_history': 0.15,
            'usage_patterns': 0.10
        }
        
        # User journey stages
        self.user_journey_stages = {
            'discovery': {
                'description': 'New user exploring features',
                'key_actions': ['first_meal_plan', 'nutrition_query', 'recipe_search'],
                'conversion_goal': 'feature_adoption',
                'messaging_tone': 'educational'
            },
            'engagement': {
                'description': 'Regular user building habits',
                'key_actions': ['weekly_meal_plans', 'grocery_lists', 'nutrition_tracking'],
                'conversion_goal': 'premium_subscription',
                'messaging_tone': 'supportive'
            },
            'optimization': {
                'description': 'Power user seeking advanced features',
                'key_actions': ['custom_meal_plans', 'detailed_analytics', 'family_planning'],
                'conversion_goal': 'feature_expansion',
                'messaging_tone': 'expert'
            },
            'advocacy': {
                'description': 'Loyal user who might refer others',
                'key_actions': ['referrals', 'feedback', 'testimonials'],
                'conversion_goal': 'referral_program',
                'messaging_tone': 'collaborative'
            }
        }
        
        # Smart response templates
        self.response_templates = {
            'welcome_new_user': {
                'message': "Welcome to AI Nutritionist! 🌟 I'm here to help you create personalized meal plans. What's your main nutrition goal?",
                'follow_up_prompts': ['Weight loss', 'Muscle gain', 'General health', 'Specific diet'],
                'personalization_level': 0
            },
            'meal_plan_suggestion': {
                'message': "Based on your preferences, I've created a {meal_type} plan focusing on {primary_goal}. Would you like me to adjust anything?",
                'follow_up_prompts': ['Looks perfect!', 'Make it more protein-rich', 'Add more vegetables', 'Different cuisine'],
                'personalization_level': 3
            },
            'upgrade_gentle': {
                'message': "You're getting great results! 📈 Premium users get unlimited meal plans and grocery delivery integration. Want to try it free for 7 days?",
                'follow_up_prompts': ['Yes, start trial', 'Tell me more', 'Maybe later'],
                'personalization_level': 2
            },
            'cost_optimization_notice': {
                'message': "I'm optimizing your experience to keep costs low while maintaining quality. You have {remaining_credits} credits left this month.",
                'follow_up_prompts': ['Check usage', 'Upgrade plan', 'Learn about credits'],
                'personalization_level': 1
            }
        }
    
    def get_personalized_response(self, user_phone: str, message_text: str, 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized response based on user profile and context"""
        try:
            # Get user profile and history
            user_profile = self._get_user_profile(user_phone)
            interaction_history = self._get_recent_interactions(user_phone, days=30)
            
            # Determine user journey stage
            journey_stage = self._determine_journey_stage(user_profile, interaction_history)
            
            # Calculate personalization score
            personalization_score = self._calculate_personalization_score(user_profile, interaction_history)
            
            # Generate personalized response
            response = self._generate_adaptive_response(
                message_text, user_profile, journey_stage, 
                personalization_score, context
            )
            
            # Add smart follow-up suggestions
            response['follow_up_suggestions'] = self._generate_follow_up_suggestions(
                user_profile, journey_stage, context
            )
            
            # Track interaction for learning
            self._track_interaction(user_phone, message_text, response, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating personalized response: {e}")
            return self._get_fallback_response(message_text)
    
    def update_user_feedback(self, user_phone: str, interaction_id: str, 
                           feedback_type: str, feedback_value: Any) -> bool:
        """Update user feedback for personalization learning"""
        try:
            timestamp = datetime.utcnow()
            
            feedback_entry = {
                'feedback_id': f"{user_phone}_{interaction_id}_{timestamp.timestamp()}",
                'user_phone': user_phone,
                'interaction_id': interaction_id,
                'feedback_type': feedback_type,  # 'rating', 'preference', 'complaint', 'suggestion'
                'feedback_value': json.dumps(feedback_value),
                'timestamp': timestamp.isoformat(),
                'processed': False,
                'ttl': int((timestamp + timedelta(days=365)).timestamp())
            }
            
            self.feedback_table.put_item(Item=feedback_entry)
            
            # Update user profile with feedback
            self._process_feedback_for_personalization(user_phone, feedback_type, feedback_value)
            
            logger.info(f"Recorded feedback for user {user_phone}: {feedback_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user feedback: {e}")
            return False
    
    def get_smart_recommendations(self, user_phone: str, context: str = 'general') -> Dict[str, Any]:
        """Get AI-powered smart recommendations for user"""
        try:
            user_profile = self._get_user_profile(user_phone)
            interaction_history = self._get_recent_interactions(user_phone, days=14)
            
            recommendations = {
                'meal_suggestions': self._get_meal_recommendations(user_profile, interaction_history),
                'feature_suggestions': self._get_feature_recommendations(user_profile, interaction_history),
                'optimization_tips': self._get_optimization_tips(user_profile, interaction_history),
                'learning_opportunities': self._get_learning_recommendations(user_profile),
                'context': context,
                'personalization_score': self._calculate_personalization_score(user_profile, interaction_history)
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating smart recommendations: {e}")
            return {'error': 'Unable to generate recommendations'}
    
    def optimize_user_journey(self, user_phone: str) -> Dict[str, Any]:
        """Optimize user journey based on behavior patterns"""
        try:
            user_profile = self._get_user_profile(user_phone)
            interaction_history = self._get_recent_interactions(user_phone, days=90)
            
            # Analyze user behavior patterns
            behavior_analysis = self._analyze_user_behavior(interaction_history)
            
            # Identify optimization opportunities
            optimization_opportunities = self._identify_optimization_opportunities(
                user_profile, behavior_analysis
            )
            
            # Generate journey optimization plan
            optimization_plan = {
                'current_stage': self._determine_journey_stage(user_profile, interaction_history),
                'behavior_insights': behavior_analysis,
                'optimization_opportunities': optimization_opportunities,
                'recommended_actions': self._generate_optimization_actions(optimization_opportunities),
                'success_metrics': self._define_success_metrics(user_profile),
                'timeline': self._create_optimization_timeline(optimization_opportunities)
            }
            
            return optimization_plan
            
        except Exception as e:
            logger.error(f"Error optimizing user journey: {e}")
            return {'error': 'Unable to optimize user journey'}
    
    def get_user_engagement_score(self, user_phone: str) -> Dict[str, Any]:
        """Calculate comprehensive user engagement score"""
        try:
            user_profile = self._get_user_profile(user_phone)
            interaction_history = self._get_recent_interactions(user_phone, days=30)
            
            # Calculate engagement components
            frequency_score = self._calculate_frequency_score(interaction_history)
            depth_score = self._calculate_depth_score(interaction_history)
            diversity_score = self._calculate_diversity_score(interaction_history)
            feedback_score = self._calculate_feedback_score(user_phone)
            retention_score = self._calculate_retention_score(interaction_history)
            
            # Weighted overall score
            overall_score = (
                frequency_score * 0.25 +
                depth_score * 0.20 +
                diversity_score * 0.20 +
                feedback_score * 0.15 +
                retention_score * 0.20
            )
            
            engagement_data = {
                'overall_score': round(overall_score, 2),
                'components': {
                    'frequency': round(frequency_score, 2),
                    'depth': round(depth_score, 2),
                    'diversity': round(diversity_score, 2),
                    'feedback': round(feedback_score, 2),
                    'retention': round(retention_score, 2)
                },
                'engagement_level': self._classify_engagement_level(overall_score),
                'recommendations': self._get_engagement_recommendations(overall_score, {
                    'frequency': frequency_score,
                    'depth': depth_score,
                    'diversity': diversity_score,
                    'feedback': feedback_score,
                    'retention': retention_score
                })
            }
            
            return engagement_data
            
        except Exception as e:
            logger.error(f"Error calculating user engagement score: {e}")
            return {'error': 'Unable to calculate engagement score'}
    
    def create_adaptive_onboarding(self, user_phone: str, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create adaptive onboarding experience based on user context"""
        try:
            # Analyze initial context for personalization hints
            user_characteristics = self._analyze_initial_context(initial_context)
            
            # Create personalized onboarding flow
            onboarding_flow = {
                'welcome_message': self._generate_welcome_message(user_characteristics),
                'key_questions': self._generate_key_questions(user_characteristics),
                'feature_introduction': self._prioritize_features(user_characteristics),
                'quick_wins': self._identify_quick_wins(user_characteristics),
                'expected_timeline': self._estimate_onboarding_timeline(user_characteristics)
            }
            
            # Initialize user profile
            initial_profile = {
                'user_phone': user_phone,
                'created_at': datetime.utcnow().isoformat(),
                'initial_context': json.dumps(initial_context),
                'onboarding_flow': json.dumps(onboarding_flow),
                'characteristics': json.dumps(user_characteristics),
                'journey_stage': 'discovery',
                'personalization_score': 0.1,  # Start low, will increase with interactions
                'last_updated': datetime.utcnow().isoformat()
            }
            
            self.user_profile_table.put_item(Item=initial_profile)
            
            return onboarding_flow
            
        except Exception as e:
            logger.error(f"Error creating adaptive onboarding: {e}")
            return self._get_default_onboarding()
    
    def _get_user_profile(self, user_phone: str) -> Dict[str, Any]:
        """Get user profile with defaults"""
        try:
            response = self.user_profile_table.get_item(Key={'user_phone': user_phone})
            
            if 'Item' in response:
                profile = response['Item']
                # Parse JSON fields
                for field in ['initial_context', 'onboarding_flow', 'characteristics', 'preferences']:
                    if field in profile and isinstance(profile[field], str):
                        try:
                            profile[field] = json.loads(profile[field])
                        except:
                            profile[field] = {}
                return profile
            else:
                # Return default profile
                return {
                    'user_phone': user_phone,
                    'journey_stage': 'discovery',
                    'personalization_score': 0.0,
                    'preferences': {},
                    'characteristics': {}
                }
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {'user_phone': user_phone, 'journey_stage': 'discovery', 'personalization_score': 0.0}
    
    def _get_recent_interactions(self, user_phone: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent user interactions"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            response = self.interaction_history_table.query(
                KeyConditionExpression='user_phone = :phone',
                FilterExpression='#ts BETWEEN :start AND :end',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':phone': user_phone,
                    ':start': start_time.isoformat(),
                    ':end': end_time.isoformat()
                }
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Error getting recent interactions: {e}")
            return []
    
    def _determine_journey_stage(self, user_profile: Dict[str, Any], 
                                interactions: List[Dict[str, Any]]) -> str:
        """Determine user's current journey stage"""
        try:
            # Count interactions and analyze types
            total_interactions = len(interactions)
            interaction_types = set(i.get('interaction_type', '') for i in interactions)
            
            # Check for premium features usage
            has_premium = any('premium' in i.get('context', '') for i in interactions)
            
            # Determine stage based on activity patterns
            if total_interactions < 5:
                return 'discovery'
            elif total_interactions < 20 and not has_premium:
                return 'engagement'
            elif has_premium or total_interactions > 50:
                return 'optimization'
            elif total_interactions > 100:
                return 'advocacy'
            else:
                return 'engagement'
                
        except Exception as e:
            logger.error(f"Error determining journey stage: {e}")
            return 'discovery'
    
    def _calculate_personalization_score(self, user_profile: Dict[str, Any], 
                                       interactions: List[Dict[str, Any]]) -> float:
        """Calculate personalization score (0-1)"""
        try:
            score = 0.0
            
            # Factor 1: Profile completeness
            profile_completeness = len(user_profile.get('preferences', {})) / 10  # Assume 10 key preferences
            score += profile_completeness * self.personalization_factors['dietary_preferences']
            
            # Factor 2: Interaction frequency
            if interactions:
                days_span = 30
                interaction_frequency = len(interactions) / days_span
                frequency_score = min(1.0, interaction_frequency / 2)  # 2 interactions/day = max score
                score += frequency_score * self.personalization_factors['interaction_frequency']
            
            # Factor 3: Feedback sentiment (placeholder)
            feedback_score = 0.7  # Default positive sentiment
            score += feedback_score * self.personalization_factors['feedback_sentiment']
            
            # Factor 4: Conversion history (placeholder)
            conversion_score = 0.5  # Default moderate conversion
            score += conversion_score * self.personalization_factors['conversion_history']
            
            # Factor 5: Usage patterns diversity
            if interactions:
                unique_types = len(set(i.get('interaction_type', '') for i in interactions))
                pattern_score = min(1.0, unique_types / 5)  # 5 different types = max score
                score += pattern_score * self.personalization_factors['usage_patterns']
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating personalization score: {e}")
            return 0.0
    
    def _generate_adaptive_response(self, message_text: str, user_profile: Dict[str, Any],
                                  journey_stage: str, personalization_score: float,
                                  context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate adaptive response based on user context"""
        try:
            # Get appropriate response template
            template_key = self._select_response_template(message_text, journey_stage, context)
            template = self.response_templates.get(template_key, self.response_templates['welcome_new_user'])
            
            # Personalize the response
            personalized_message = self._personalize_message(
                template['message'], user_profile, context
            )
            
            # Adjust tone based on journey stage
            stage_info = self.user_journey_stages[journey_stage]
            tone = stage_info['messaging_tone']
            
            response = {
                'message': personalized_message,
                'tone': tone,
                'journey_stage': journey_stage,
                'personalization_score': personalization_score,
                'template_used': template_key,
                'follow_up_prompts': template.get('follow_up_prompts', []),
                'adaptive_elements': self._get_adaptive_elements(user_profile, journey_stage)
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating adaptive response: {e}")
            return self._get_fallback_response(message_text)
    
    def _generate_follow_up_suggestions(self, user_profile: Dict[str, Any], 
                                      journey_stage: str, 
                                      context: Dict[str, Any]) -> List[str]:
        """Generate smart follow-up suggestions"""
        suggestions = []
        
        stage_info = self.user_journey_stages[journey_stage]
        key_actions = stage_info['key_actions']
        
        # Suggest actions based on journey stage
        for action in key_actions[:3]:  # Top 3 suggestions
            suggestions.append(self._format_action_suggestion(action, user_profile))
        
        return suggestions
    
    def _get_meal_recommendations(self, user_profile: Dict[str, Any], 
                                interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get personalized meal recommendations"""
        preferences = user_profile.get('preferences', {})
        
        # Analyze past meal requests
        past_meals = [i for i in interactions if i.get('interaction_type') == 'meal_plan_request']
        
        recommendations = []
        
        # Base recommendations on preferences and history
        if preferences.get('diet_type') == 'vegetarian':
            recommendations.append({
                'type': 'breakfast',
                'title': 'Protein-Rich Vegetarian Breakfast',
                'description': 'Greek yogurt parfait with nuts and berries',
                'confidence': 0.9
            })
        
        if len(past_meals) > 5:
            recommendations.append({
                'type': 'dinner',
                'title': 'Based on Your Favorites',
                'description': 'Similar to your highly-rated meals',
                'confidence': 0.8
            })
        
        return recommendations
    
    def _track_interaction(self, user_phone: str, message_text: str, 
                          response: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Track interaction for personalization learning"""
        try:
            timestamp = datetime.utcnow()
            
            interaction = {
                'interaction_id': f"{user_phone}_{timestamp.timestamp()}",
                'user_phone': user_phone,
                'timestamp': timestamp.isoformat(),
                'message_text': message_text,
                'response_summary': response.get('message', '')[:200],  # Truncated
                'interaction_type': context.get('type', 'general'),
                'journey_stage': response.get('journey_stage', 'unknown'),
                'personalization_score': response.get('personalization_score', 0.0),
                'context': json.dumps(context),
                'ttl': int((timestamp + timedelta(days=180)).timestamp())
            }
            
            self.interaction_history_table.put_item(Item=interaction)
            
        except Exception as e:
            logger.error(f"Error tracking interaction: {e}")
    
    def _get_fallback_response(self, message_text: str) -> Dict[str, Any]:
        """Get fallback response when personalization fails"""
        return {
            'message': "I'm here to help with your nutrition needs! How can I assist you today?",
            'tone': 'friendly',
            'journey_stage': 'discovery',
            'personalization_score': 0.0,
            'follow_up_prompts': ['Meal planning', 'Nutrition advice', 'Recipe suggestions'],
            'fallback': True
        }
    
    # Additional helper methods would continue here...
    # (Implementing the remaining methods for brevity)
    
    def _select_response_template(self, message_text: str, journey_stage: str, 
                                context: Dict[str, Any]) -> str:
        """Select appropriate response template"""
        if 'meal plan' in message_text.lower():
            return 'meal_plan_suggestion'
        elif journey_stage == 'discovery':
            return 'welcome_new_user'
        elif context.get('type') == 'upgrade_prompt':
            return 'upgrade_gentle'
        else:
            return 'welcome_new_user'
    
    def _personalize_message(self, template: str, user_profile: Dict[str, Any], 
                           context: Dict[str, Any]) -> str:
        """Personalize message template with user data"""
        # Simple template substitution - in practice, this would be more sophisticated
        personalized = template
        
        if '{meal_type}' in template:
            personalized = personalized.replace('{meal_type}', context.get('meal_type', 'daily'))
        
        if '{primary_goal}' in template:
            goal = user_profile.get('preferences', {}).get('primary_goal', 'health')
            personalized = personalized.replace('{primary_goal}', goal)
        
        return personalized
    
    def _get_adaptive_elements(self, user_profile: Dict[str, Any], journey_stage: str) -> Dict[str, Any]:
        """Get adaptive UI/UX elements"""
        return {
            'show_onboarding_tips': journey_stage == 'discovery',
            'highlight_premium_features': journey_stage == 'engagement',
            'show_advanced_options': journey_stage in ['optimization', 'advocacy'],
            'personalization_level': user_profile.get('personalization_score', 0.0)
        }
    
    def _format_action_suggestion(self, action: str, user_profile: Dict[str, Any]) -> str:
        """Format action suggestion for user"""
        action_formats = {
            'first_meal_plan': 'Create your first personalized meal plan',
            'nutrition_query': 'Ask about nutrition for specific foods',
            'recipe_search': 'Find recipes matching your preferences',
            'weekly_meal_plans': 'Plan your entire week of meals',
            'grocery_lists': 'Generate smart grocery lists',
            'custom_meal_plans': 'Create advanced custom meal plans'
        }
        
        return action_formats.get(action, action.replace('_', ' ').title())
    
    # Placeholder implementations for remaining methods
    def _get_feature_recommendations(self, user_profile, interactions):
        return [{'feature': 'Premium Meal Plans', 'confidence': 0.8}]
    
    def _get_optimization_tips(self, user_profile, interactions):
        return [{'tip': 'Use grocery integration for better meal planning', 'impact': 'high'}]
    
    def _get_learning_recommendations(self, user_profile):
        return [{'topic': 'Meal prep basics', 'difficulty': 'beginner'}]
    
    def _analyze_user_behavior(self, interactions):
        return {'peak_usage_time': '18:00', 'preferred_meal_types': ['dinner', 'lunch']}
    
    def _identify_optimization_opportunities(self, user_profile, behavior_analysis):
        return [{'opportunity': 'Increase engagement', 'potential': 'high'}]
    
    def _generate_optimization_actions(self, opportunities):
        return [{'action': 'Send weekly meal plan reminders', 'priority': 'high'}]
    
    def _define_success_metrics(self, user_profile):
        return {'engagement_increase': '25%', 'conversion_rate': '15%'}
    
    def _create_optimization_timeline(self, opportunities):
        return {'week_1': 'Implement reminders', 'week_2': 'A/B test messaging'}
    
    def _calculate_frequency_score(self, interactions):
        return min(1.0, len(interactions) / 30.0)  # 30 interactions per month = max score
    
    def _calculate_depth_score(self, interactions):
        return 0.7  # Placeholder
    
    def _calculate_diversity_score(self, interactions):
        return 0.8  # Placeholder
    
    def _calculate_feedback_score(self, user_phone):
        return 0.6  # Placeholder
    
    def _calculate_retention_score(self, interactions):
        return 0.75  # Placeholder
    
    def _classify_engagement_level(self, score):
        if score >= 0.8:
            return 'HIGH'
        elif score >= 0.6:
            return 'MEDIUM'
        elif score >= 0.4:
            return 'LOW'
        else:
            return 'VERY_LOW'
    
    def _get_engagement_recommendations(self, overall_score, components):
        recommendations = []
        
        if components['frequency'] < 0.5:
            recommendations.append('Increase interaction frequency with daily tips')
        
        if components['diversity'] < 0.6:
            recommendations.append('Explore new features like grocery integration')
        
        return recommendations
    
    def _analyze_initial_context(self, context):
        return {'experience_level': 'beginner', 'primary_interest': 'weight_loss'}
    
    def _generate_welcome_message(self, characteristics):
        return "Welcome! I see you're interested in weight loss. Let's create a plan that works for you!"
    
    def _generate_key_questions(self, characteristics):
        return ['What are your dietary restrictions?', 'How often do you cook?']
    
    def _prioritize_features(self, characteristics):
        return ['Meal Planning', 'Calorie Tracking', 'Recipe Search']
    
    def _identify_quick_wins(self, characteristics):
        return ['Create your first meal plan in 2 minutes']
    
    def _estimate_onboarding_timeline(self, characteristics):
        return {'setup': '5 minutes', 'first_value': '10 minutes', 'full_adoption': '1 week'}
    
    def _get_default_onboarding(self):
        return {
            'welcome_message': 'Welcome to AI Nutritionist!',
            'key_questions': ['What are your nutrition goals?'],
            'feature_introduction': ['Meal Planning', 'Nutrition Analysis'],
            'quick_wins': ['Try creating a meal plan'],
            'expected_timeline': {'setup': '5 minutes'}
        }
    
    def _process_feedback_for_personalization(self, user_phone, feedback_type, feedback_value):
        """Process feedback to update user personalization"""
        try:
            # This would update the user profile based on feedback
            # For example, if user rates a meal plan highly, boost similar recommendations
            logger.info(f"Processing feedback for personalization: {feedback_type}")
        except Exception as e:
            logger.error(f"Error processing feedback for personalization: {e}")
