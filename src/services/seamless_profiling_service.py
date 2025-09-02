"""
Seamless User Profiling Service
Progressive learning system that adapts to user preferences invisibly
No forms, no interrogations - just natural evolution through conversation
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import boto3
from decimal import Decimal

logger = logging.getLogger(__name__)

class SeamlessUserProfileService:
    """
    Progressive learning user profiling that feels invisible
    Builds rich user understanding through micro-interactions
    """
    
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.profiles_table = self.dynamodb.Table('ai-nutritionist-profiles')
        self.interactions_table = self.dynamodb.Table('ai-nutritionist-interactions')
        self.feedback_table = self.dynamodb.Table('ai-nutritionist-feedback')
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get complete user context without exposing complexity"""
        try:
            # Get base profile
            profile_response = self.profiles_table.get_item(
                Key={'user_id': user_id}
            )
            
            if 'Item' not in profile_response:
                return self.create_invisible_profile(user_id)
            
            profile = profile_response['Item']
            
            # Enrich with recent interactions and learned preferences
            enriched_profile = self._enrich_with_learned_patterns(profile)
            
            return enriched_profile
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return self.create_invisible_profile(user_id)
    
    def create_invisible_profile(self, user_id: str, platform: str = 'whatsapp') -> Dict[str, Any]:
        """Create minimal profile that learns progressively"""
        now = datetime.now()
        
        base_profile = {
            'user_id': user_id,
            'platform': platform,
            'created_at': now.isoformat(),
            'last_active': now.isoformat(),
            
            # Identity & Context (quietly gathered)
            'timezone': 'UTC',  # Will detect from conversation timing
            'locale': 'en-US',
            'lifestyle_rhythm': {
                'wake_time': None,  # Learned from "morning" messages
                'sleep_time': None,  # Learned from "late dinner" cues
                'work_schedule': 'standard',  # Detected from meal timing patterns
                'activity_level': 'moderate'  # Inferred from goals/feedback
            },
            
            # Budget & Household (inferred)
            'budget_envelope': {
                'weekly_target': None,  # Learned from "too expensive" feedback
                'price_sensitivity': 'unknown',  # high/medium/low
                'bulk_preference': False  # Detected from repeat meal acceptance
            },
            'household': {
                'size': 1,  # Updated when they mention "family dinner"
                'adults': 1,
                'children': 0,
                'dietary_restrictions': [],
                'cooking_environment': {
                    'appliances': [],  # Added when mentioned: "instant pot", "air fryer"
                    'prep_time_tolerance': 30,  # Adjusted based on "too long" feedback
                    'skill_level': 'intermediate'
                }
            },
            
            # Health Goals (evolving)
            'health_goals': {
                'primary_intent': None,  # lose fat, build muscle, maintain energy
                'nutrition_targets': {
                    'calories': None,  # Set progressively
                    'protein_grams': None,
                    'fiber_grams': None,
                    'sodium_limit': None
                },
                'preferred_strategies': {
                    'intermittent_fasting': False,
                    'time_restricted_eating': False,
                    'high_protein_focus': False,
                    'plant_forward': False,
                    'gut_health_focus': False,
                    'anti_inflammatory': False
                }
            },
            
            # Taste Intelligence (the differentiator)
            'taste_profile': {
                'cuisine_rankings': {},  # Italian: 5, Thai: 4 (learned)
                'flavor_weights': {
                    'spicy': 3,  # 1-5 scale, learned from reactions
                    'herby': 3,
                    'tangy': 3,
                    'smoky': 3,
                    'creamy': 3,
                    'crunchy': 3
                },
                'ingredient_heroes': [],  # Favorites highlighted automatically
                'hard_dislikes': [],  # "keeps rejecting broccoli"
                'repeat_tolerance': 'medium'  # high/medium/low
            },
            
            # Learning Metrics
            'learning_stage': 'discovery',  # discovery -> preference_mapping -> optimization
            'interaction_count': 0,
            'feedback_count': 0,
            'adaptation_score': 0.0  # How well we're adapting (0-1)
        }
        
        # Save to database
        self.profiles_table.put_item(Item=base_profile)
        
        return base_profile
    
    def process_conversation_cues(self, user_id: str, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract learning signals from natural conversation
        No direct questions - just intelligent observation
        """
        try:
            message_lower = message.lower()
            learned_insights = {}
            
            # Lifestyle Rhythm Cues
            if any(phrase in message_lower for phrase in ['late gym', 'evening workout', 'after work']):
                learned_insights['evening_exercise'] = True
                
            if any(phrase in message_lower for phrase in ['early morning', 'before work', '6am']):
                learned_insights['early_riser'] = True
                
            if any(phrase in message_lower for phrase in ['skip breakfast', 'no breakfast', 'just coffee']):
                learned_insights['intermittent_fasting_candidate'] = True
            
            # Budget Sensitivity
            if any(phrase in message_lower for phrase in ['too expensive', 'cheaper', 'budget', 'save money']):
                learned_insights['price_sensitive'] = True
                
            if any(phrase in message_lower for phrase in ['bulk', 'costco', 'family pack']):
                learned_insights['bulk_buyer'] = True
            
            # Household Clues
            if any(phrase in message_lower for phrase in ['family dinner', 'kids', 'children']):
                learned_insights['has_children'] = True
                
            if any(phrase in message_lower for phrase in ['roommate', 'partner', 'husband', 'wife']):
                learned_insights['multi_adult_household'] = True
            
            # Cooking Environment
            appliances = ['instant pot', 'air fryer', 'slow cooker', 'rice cooker', 'blender', 'food processor']
            for appliance in appliances:
                if appliance in message_lower:
                    learned_insights['has_appliance'] = appliance
            
            if any(phrase in message_lower for phrase in ['too long', 'quick', 'fast', 'no time']):
                learned_insights['time_constrained'] = True
            
            # Health & Strategy Interest
            if any(phrase in message_lower for phrase in ['intermittent fasting', '16:8', 'eating window']):
                learned_insights['interested_in_if'] = True
                
            if any(phrase in message_lower for phrase in ['gut health', 'probiotics', 'fermented']):
                learned_insights['gut_health_interest'] = True
                
            if any(phrase in message_lower for phrase in ['plant based', 'less meat', 'vegetarian']):
                learned_insights['plant_forward_interest'] = True
            
            # Special Contexts
            if any(phrase in message_lower for phrase in ['dinner party', 'friends over', 'entertaining']):
                learned_insights['hosting_event'] = True
                
            if any(phrase in message_lower for phrase in ['travel', 'hotel', 'vacation', 'airbnb']):
                learned_insights['travel_mode'] = True
                
            if any(phrase in message_lower for phrase in ['sick', 'feeling down', 'cold', 'tired']):
                learned_insights['recovery_mode'] = True
            
            # Apply insights to user profile
            self._update_profile_from_insights(user_id, learned_insights)
            
            # Log interaction for pattern analysis
            self._log_interaction(user_id, message, learned_insights)
            
            return learned_insights
            
        except Exception as e:
            logger.error(f"Error processing conversation cues: {e}")
            return {}
    
    def process_meal_feedback(self, user_id: str, meal_id: str, rating: int, emoji: str = None, comment: str = None) -> None:
        """
        Process feedback to improve taste and preference understanding
        Quick 1-5 tap + optional emoji tells us everything
        """
        try:
            feedback_data = {
                'user_id': user_id,
                'meal_id': meal_id,
                'rating': rating,
                'emoji': emoji,
                'comment': comment,
                'timestamp': datetime.now().isoformat()
            }
            
            # Save feedback
            self.feedback_table.put_item(Item=feedback_data)
            
            # Extract learning signals
            if rating >= 4:  # Loved it
                self._reinforce_positive_elements(user_id, meal_id)
            elif rating <= 2:  # Disliked
                self._identify_negative_elements(user_id, meal_id)
            
            # Update adaptation score
            self._update_adaptation_score(user_id, rating)
            
        except Exception as e:
            logger.error(f"Error processing meal feedback: {e}")
    
    def generate_micro_prompt(self, user_id: str, context: str = 'general') -> Optional[str]:
        """
        Generate contextual micro-prompts for progressive learning
        Feels natural, not interrogating
        """
        try:
            profile = self.get_user_context(user_id)
            learning_stage = profile.get('learning_stage', 'discovery')
            interaction_count = profile.get('interaction_count', 0)
            
            # Don't prompt too frequently
            if interaction_count < 3:
                return None
            
            prompts = []
            
            # Spice level adjustment
            spice_level = profile.get('taste_profile', {}).get('flavor_weights', {}).get('spicy', 3)
            recent_spicy_feedback = self._get_recent_spicy_feedback(user_id)
            if recent_spicy_feedback and recent_spicy_feedback['avg_rating'] >= 4:
                prompts.append("🔥 loved those spicy flavors — want me to kick things up a notch?")
            
            # Intermittent fasting suggestion
            if profile.get('health_goals', {}).get('preferred_strategies', {}).get('intermittent_fasting') == False:
                if self._detect_breakfast_skipping_pattern(user_id):
                    prompts.append("noticed you often skip breakfast — want to try 16:8 eating windows? could work well for you!")
            
            # Budget optimization
            if profile.get('budget_envelope', {}).get('price_sensitivity') == 'high':
                prompts.append("budget tight this week? i can emphasize beans, bulk grains, and seasonal veggies 💰")
            
            # Family context
            if profile.get('household', {}).get('children') > 0:
                prompts.append("kids' activities crazy this week? i can plan 15-min dinners for busy nights ⚡")
            
            # Gut health interest
            if profile.get('health_goals', {}).get('preferred_strategies', {}).get('gut_health_focus') == False:
                prompts.append("want to experiment with gut-friendly foods? kimchi, kefir, and fermented goodness 🦠")
            
            # Plant-forward nudge
            if profile.get('health_goals', {}).get('preferred_strategies', {}).get('plant_forward') == False:
                prompts.append("swap 1 meat dinner for lentils this week? still high protein, but $4 cheaper & planet-friendly 🌱")
            
            # Return random prompt if any available
            if prompts:
                import random
                return random.choice(prompts)
                
            return None
            
        except Exception as e:
            logger.error(f"Error generating micro-prompt: {e}")
            return None
    
    def detect_special_context(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        """
        Detect special contexts that need different meal planning
        """
        message_lower = message.lower()
        
        # Dinner party context
        if any(phrase in message_lower for phrase in ['dinner party', 'friends over', 'entertaining', 'guests']):
            return {
                'type': 'dinner_party',
                'prompts': [
                    "how many guests?",
                    "casual or more formal vibe?",
                    "any dietary restrictions i should know about?"
                ]
            }
        
        # Travel context
        if any(phrase in message_lower for phrase in ['travel', 'hotel', 'airbnb', 'vacation']):
            return {
                'type': 'travel',
                'meal_style': 'minimal_prep',
                'suggestions': ['no-cook meals', 'microwave-friendly', 'grab-and-go snacks']
            }
        
        # Sick/recovery context
        if any(phrase in message_lower for phrase in ['sick', 'not feeling well', 'cold', 'tired']):
            return {
                'type': 'recovery',
                'meal_style': 'comfort',
                'suggestions': ['soups', 'broths', 'easy-to-digest foods']
            }
        
        return None
    
    def _enrich_with_learned_patterns(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich profile with learned patterns and insights"""
        user_id = profile['user_id']
        
        # Add recent feedback patterns
        profile['recent_patterns'] = {
            'favorite_cuisines': self._get_top_cuisines(user_id),
            'successful_ingredients': self._get_successful_ingredients(user_id),
            'time_preferences': self._get_time_preferences(user_id),
            'budget_trends': self._get_budget_trends(user_id)
        }
        
        return profile
    
    def _update_profile_from_insights(self, user_id: str, insights: Dict[str, Any]) -> None:
        """Update user profile based on conversation insights"""
        try:
            updates = {}
            
            if insights.get('price_sensitive'):
                updates['budget_envelope.price_sensitivity'] = 'high'
            
            if insights.get('bulk_buyer'):
                updates['budget_envelope.bulk_preference'] = True
            
            if insights.get('has_children'):
                updates['household.children'] = 1  # Will be refined later
            
            if insights.get('time_constrained'):
                updates['household.cooking_environment.prep_time_tolerance'] = 15
            
            if insights.get('interested_in_if'):
                updates['health_goals.preferred_strategies.intermittent_fasting'] = True
            
            if insights.get('gut_health_interest'):
                updates['health_goals.preferred_strategies.gut_health_focus'] = True
            
            if insights.get('plant_forward_interest'):
                updates['health_goals.preferred_strategies.plant_forward'] = True
            
            # Apply updates to profile
            if updates:
                self._apply_profile_updates(user_id, updates)
                
        except Exception as e:
            logger.error(f"Error updating profile from insights: {e}")
    
    def _log_interaction(self, user_id: str, message: str, insights: Dict[str, Any]) -> None:
        """Log interaction for pattern analysis"""
        try:
            interaction_data = {
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'message_hash': hashlib.md5(message.encode()).hexdigest()[:8],
                'message_length': len(message),
                'insights_extracted': len(insights),
                'insights': insights
            }
            
            self.interactions_table.put_item(Item=interaction_data)
            
            # Increment interaction count
            self.profiles_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='ADD interaction_count :inc SET last_active = :now',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':now': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging interaction: {e}")
    
    def _apply_profile_updates(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Apply updates to user profile"""
        try:
            update_expression_parts = []
            expression_values = {}
            
            for key, value in updates.items():
                if '.' in key:
                    # Handle nested updates
                    parts = key.split('.')
                    expr = f"SET {parts[0]}.{parts[1]} = :{parts[1].replace('_', '')}"
                    update_expression_parts.append(expr)
                    expression_values[f":{parts[1].replace('_', '')}"] = value
                else:
                    expr = f"SET {key} = :{key.replace('_', '')}"
                    update_expression_parts.append(expr)
                    expression_values[f":{key.replace('_', '')}"] = value
            
            if update_expression_parts:
                self.profiles_table.update_item(
                    Key={'user_id': user_id},
                    UpdateExpression=' '.join(update_expression_parts),
                    ExpressionAttributeValues=expression_values
                )
                
        except Exception as e:
            logger.error(f"Error applying profile updates: {e}")
    
    def _get_recent_spicy_feedback(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get recent feedback on spicy meals"""
        # Implementation would query feedback for spicy meals
        return None
    
    def _detect_breakfast_skipping_pattern(self, user_id: str) -> bool:
        """Detect if user often skips breakfast"""
        # Implementation would analyze meal request patterns
        return False
    
    def _get_top_cuisines(self, user_id: str) -> List[str]:
        """Get user's favorite cuisines based on feedback"""
        return []
    
    def _get_successful_ingredients(self, user_id: str) -> List[str]:
        """Get ingredients that get consistently good ratings"""
        return []
    
    def _get_time_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get preferred meal timing patterns"""
        return {}
    
    def _get_budget_trends(self, user_id: str) -> Dict[str, Any]:
        """Get budget preference trends"""
        return {}
    
    def _reinforce_positive_elements(self, user_id: str, meal_id: str) -> None:
        """Learn from highly rated meals"""
        # Implementation would analyze meal components and reinforce them
        pass
    
    def _identify_negative_elements(self, user_id: str, meal_id: str) -> None:
        """Learn what to avoid from poorly rated meals"""
        # Implementation would identify problematic elements
        pass
    
    def _update_adaptation_score(self, user_id: str, rating: int) -> None:
        """Update how well we're adapting to user preferences"""
        try:
            # Simple adaptation score based on recent ratings
            weight = 0.1  # Learning rate
            score_contribution = (rating - 3) / 2  # Convert 1-5 to -1 to 1
            
            self.profiles_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='ADD adaptation_score :delta, feedback_count :inc',
                ExpressionAttributeValues={
                    ':delta': Decimal(str(score_contribution * weight)),
                    ':inc': 1
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating adaptation score: {e}")
