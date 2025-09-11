"""
Adaptive Meal Planning Service
Uses seamless user profiling to create progressively better meal plans
Incorporates latest nutrition science and trends naturally
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import random

from ..personalization.learning import SeamlessUserProfileService
from ..infrastructure.ai import AIService

logger = logging.getLogger(__name__)

class AdaptiveMealPlanningService:
    """
    Intelligent meal planning that adapts to user preferences invisibly
    Incorporates modern nutrition strategies without being pushy
    """
    
    def __init__(self, dynamodb_resource=None):
        self.profiling_service = SeamlessUserProfileService(dynamodb_resource)
        self.ai_service = AIService()
        
        # Modern nutrition strategies database
        self.nutrition_strategies = {
            'intermittent_fasting': {
                'name': 'Intermittent Fasting',
                'description': '16:8 eating windows for metabolic benefits',
                'meal_timing': {'breakfast': None, 'lunch': '12:00', 'dinner': '19:00'},
                'benefits': ['metabolic flexibility', 'weight management', 'cellular repair']
            },
            'time_restricted_eating': {
                'name': 'Time-Restricted Eating',
                'description': 'Align eating with circadian rhythms',
                'meal_timing': {'breakfast': '07:00', 'lunch': '12:00', 'dinner': '18:00'},
                'benefits': ['better sleep', 'improved digestion', 'stable energy']
            },
            'gut_health_focus': {
                'name': 'Gut Health Optimization',
                'description': 'Fermented foods and prebiotic fibers',
                'key_foods': ['kimchi', 'kefir', 'sauerkraut', 'prebiotic fibers', 'diverse plants'],
                'benefits': ['improved immunity', 'better mood', 'enhanced digestion']
            },
            'plant_forward': {
                'name': 'Plant-Forward Eating',
                'description': 'Emphasize plants without eliminating meat',
                'approach': 'reduce meat frequency, increase plant proteins',
                'benefits': ['lower inflammation', 'environmental impact', 'cost savings']
            },
            'anti_inflammatory': {
                'name': 'Anti-Inflammatory Foods',
                'description': 'Foods that reduce systemic inflammation',
                'key_foods': ['olive oil', 'fatty fish', 'leafy greens', 'berries', 'spices'],
                'benefits': ['reduced inflammation', 'joint health', 'heart health']
            }
        }
    
    def generate_adaptive_meal_plan(self, user_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate meal plan that adapts to user's evolving preferences
        """
        try:
            # Get comprehensive user context
            user_profile = self.profiling_service.get_user_context(user_id)
            
            # Detect special contexts
            special_context = self._detect_planning_context(user_profile, context)
            
            # Build adaptive prompt incorporating user insights
            prompt = self._build_adaptive_prompt(user_profile, special_context)
            
            # Generate base meal plan
            meal_plan = self.ai_service.generate_meal_plan(user_profile)
            
            if meal_plan:
                # Apply progressive enhancements
                enhanced_plan = self._apply_progressive_enhancements(meal_plan, user_profile)
                
                # Add micro-nudges for new strategies
                enhanced_plan = self._add_strategy_nudges(enhanced_plan, user_profile)
                
                # Personalize presentation
                enhanced_plan = self._personalize_presentation(enhanced_plan, user_profile)
                
                return enhanced_plan
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating adaptive meal plan: {e}")
            return None
    
    def _detect_planning_context(self, user_profile: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Detect special planning contexts"""
        planning_context = {
            'type': 'standard',
            'modifications': []
        }
        
        # Check for special situations from user profile
        if context:
            if context.get('dinner_party'):
                planning_context = {
                    'type': 'entertaining',
                    'guest_count': context.get('guest_count', 4),
                    'formality': context.get('formality', 'casual'),
                    'modifications': ['impressive_presentation', 'make_ahead_friendly']
                }
            
            elif context.get('travel'):
                planning_context = {
                    'type': 'travel',
                    'kitchen_access': context.get('kitchen_access', 'limited'),
                    'modifications': ['minimal_prep', 'portable', 'no_fresh_ingredients']
                }
            
            elif context.get('recovery'):
                planning_context = {
                    'type': 'recovery',
                    'modifications': ['comfort_foods', 'easy_digest', 'immune_support']
                }
        
        # Check for implicit contexts from user patterns
        lifestyle = user_profile.get('lifestyle_rhythm', {})
        if lifestyle.get('work_schedule') == 'night_shift':
            planning_context['modifications'].append('inverted_meal_timing')
        
        cooking_env = user_profile.get('household', {}).get('cooking_environment', {})
        if cooking_env.get('prep_time_tolerance', 30) <= 15:
            planning_context['modifications'].append('quick_prep')
        
        return planning_context
    
    def _build_adaptive_prompt(self, user_profile: Dict[str, Any], special_context: Dict[str, Any]) -> str:
        """Build AI prompt that incorporates learned preferences"""
        
        # Base user info
        household_size = user_profile.get('household', {}).get('size', 1)
        budget_level = user_profile.get('budget_envelope', {}).get('price_sensitivity', 'medium')
        
        # Taste preferences
        taste_profile = user_profile.get('taste_profile', {})
        flavor_weights = taste_profile.get('flavor_weights', {})
        cuisine_rankings = taste_profile.get('cuisine_rankings', {})
        ingredient_heroes = taste_profile.get('ingredient_heroes', [])
        hard_dislikes = taste_profile.get('hard_dislikes', [])
        
        # Health strategies
        health_goals = user_profile.get('health_goals', {})
        strategies = health_goals.get('preferred_strategies', {})
        
        # Build dynamic prompt
        prompt_parts = [
            f"Create a weekly meal plan for {household_size} people.",
        ]
        
        # Budget considerations
        if budget_level == 'high':
            prompt_parts.append("Focus on budget-friendly options with bulk ingredients and seasonal produce.")
        elif budget_level == 'low':
            prompt_parts.append("Include some premium ingredients for special meals.")
        
        # Taste preferences
        if cuisine_rankings:
            top_cuisines = sorted(cuisine_rankings.items(), key=lambda x: x[1], reverse=True)[:3]
            prompt_parts.append(f"Emphasize {', '.join([c[0] for c in top_cuisines])} flavors.")
        
        if ingredient_heroes:
            prompt_parts.append(f"Highlight these favorite ingredients: {', '.join(ingredient_heroes[:5])}.")
        
        if hard_dislikes:
            prompt_parts.append(f"Avoid these ingredients: {', '.join(hard_dislikes)}.")
        
        # Flavor intensity
        spice_level = flavor_weights.get('spicy', 3)
        if spice_level >= 4:
            prompt_parts.append("Include bold, spicy flavors.")
        elif spice_level <= 2:
            prompt_parts.append("Keep spices mild and approachable.")
        
        # Health strategies (only if user has shown interest)
        if strategies.get('intermittent_fasting'):
            prompt_parts.append("Structure for 16:8 intermittent fasting (lunch at 12pm, dinner by 8pm).")
        
        if strategies.get('gut_health_focus'):
            prompt_parts.append("Include gut-friendly foods: fermented vegetables, kefir, prebiotic-rich foods.")
        
        if strategies.get('plant_forward'):
            prompt_parts.append("Emphasize plant proteins and reduce meat frequency (2-3 plant-based dinners).")
        
        if strategies.get('anti_inflammatory'):
            prompt_parts.append("Focus on anti-inflammatory ingredients: olive oil, fatty fish, colorful vegetables, spices.")
        
        # Special context modifications
        if special_context['type'] == 'entertaining':
            prompt_parts.append(f"Design for entertaining {special_context.get('guest_count', 4)} guests.")
            prompt_parts.append("Include make-ahead options and impressive presentation.")
        
        elif special_context['type'] == 'travel':
            prompt_parts.append("Focus on minimal-prep meals suitable for limited kitchen access.")
        
        elif special_context['type'] == 'recovery':
            prompt_parts.append("Emphasize comforting, easy-to-digest foods that support recovery.")
        
        # Time considerations
        if 'quick_prep' in special_context.get('modifications', []):
            prompt_parts.append("All meals should be preparable in 15 minutes or less.")
        
        return " ".join(prompt_parts)
    
    def _apply_progressive_enhancements(self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Apply enhancements based on user's learning stage"""
        
        learning_stage = user_profile.get('learning_stage', 'discovery')
        
        if learning_stage == 'discovery':
            # Focus on discovering preferences
            meal_plan['discovery_note'] = "I'm learning your tastes - let me know what you love! 🎯"
            
        elif learning_stage == 'preference_mapping':
            # Start introducing variety within preferences
            meal_plan['variety_note'] = "Trying some new combinations based on what you've enjoyed! 🌟"
            
        elif learning_stage == 'optimization':
            # Fine-tune for perfect fit
            meal_plan['optimization_note'] = "Dialed in to your perfect flavor profile! 🎯"
        
        # Add cost awareness if user is price-sensitive
        price_sensitivity = user_profile.get('budget_envelope', {}).get('price_sensitivity')
        if price_sensitivity == 'high':
            meal_plan['budget_note'] = f"Total estimated cost: ${self._estimate_meal_cost(meal_plan):.0f}"
        
        return meal_plan
    
    def _add_strategy_nudges(self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Add gentle nudges for beneficial nutrition strategies"""
        
        strategies = user_profile.get('health_goals', {}).get('preferred_strategies', {})
        interaction_count = user_profile.get('interaction_count', 0)
        
        # Only suggest strategies after user has used system a few times
        if interaction_count < 5:
            return meal_plan
        
        nudges = []
        
        # Intermittent fasting nudge (if they skip breakfast often)
        if not strategies.get('intermittent_fasting') and self._detect_breakfast_skipping(user_profile):
            nudges.append({
                'type': 'intermittent_fasting',
                'message': "💡 Notice you often skip breakfast - want to try 16:8 eating windows? Could work perfectly for your routine!",
                'benefit': 'metabolic flexibility and weight management'
            })
        
        # Gut health nudge (if they haven't explored it)
        if not strategies.get('gut_health_focus') and interaction_count >= 10:
            nudges.append({
                'type': 'gut_health',
                'message': "🦠 Want to try some gut-friendly foods this week? Kimchi, kefir, and fermented goodness can boost mood and immunity!",
                'benefit': 'improved digestion and immune function'
            })
        
        # Plant-forward nudge (if they eat meat frequently)
        if not strategies.get('plant_forward') and self._detect_heavy_meat_consumption(user_profile):
            nudges.append({
                'type': 'plant_forward',
                'message': "🌱 How about swapping 1-2 meat dinners for plant proteins this week? Still high protein, but easier on budget and planet!",
                'benefit': 'cost savings and environmental impact'
            })
        
        # Anti-inflammatory nudge (if they mention joint pain or inflammation)
        if not strategies.get('anti_inflammatory') and self._detect_inflammation_concerns(user_profile):
            nudges.append({
                'type': 'anti_inflammatory',
                'message': "🔥 Want to try more anti-inflammatory foods? Olive oil, fatty fish, and colorful veggies can help reduce inflammation!",
                'benefit': 'reduced inflammation and joint health'
            })
        
        # Add one random nudge (not overwhelming)
        if nudges and random.random() < 0.3:  # 30% chance
            chosen_nudge = random.choice(nudges)
            meal_plan['strategy_nudge'] = chosen_nudge
        
        return meal_plan
    
    def _personalize_presentation(self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Personalize how the meal plan is presented"""
        
        # Add personal touches based on user patterns
        taste_profile = user_profile.get('taste_profile', {})
        interaction_count = user_profile.get('interaction_count', 0)
        
        # Personalized intro messages
        intro_messages = []
        
        if interaction_count < 5:
            intro_messages = [
                "Here's your personalized meal plan! 🍽️",
                "I've put together something delicious for you! ✨",
                "Ready for a week of tasty, healthy meals? 🌟"
            ]
        else:
            # More personalized after learning preferences
            hero_ingredients = taste_profile.get('ingredient_heroes', [])
            if hero_ingredients:
                intro_messages.append(f"Loaded this plan with your favorites: {', '.join(hero_ingredients[:2])}! 🎯")
            
            cuisine_rankings = taste_profile.get('cuisine_rankings', {})
            if cuisine_rankings:
                top_cuisine = max(cuisine_rankings.items(), key=lambda x: x[1])[0]
                intro_messages.append(f"Heavy on the {top_cuisine} flavors you love! 🔥")
            
            intro_messages.extend([
                "Dialed in to your taste profile! 🎯",
                "Custom-crafted based on what you've loved! ⭐",
                "Your perfect flavor week ahead! 🚀"
            ])
        
        meal_plan['personalized_intro'] = random.choice(intro_messages)
        
        # Add contextual tips
        tips = []
        
        cooking_env = user_profile.get('household', {}).get('cooking_environment', {})
        appliances = cooking_env.get('appliances', [])
        
        if 'instant pot' in appliances:
            tips.append("💡 I've marked meals perfect for your Instant Pot!")
        
        if 'air fryer' in appliances:
            tips.append("✨ Some of these will be amazing in your air fryer!")
        
        prep_tolerance = cooking_env.get('prep_time_tolerance', 30)
        if prep_tolerance <= 15:
            tips.append("⚡ All meals under 15 minutes, perfect for your busy schedule!")
        
        if tips:
            meal_plan['contextual_tips'] = tips
        
        return meal_plan
    
    def process_meal_feedback(self, user_id: str, meal_id: str, rating: int, emoji: str = None, comment: str = None) -> Dict[str, Any]:
        """Process feedback and return insights"""
        
        # Pass to profiling service for learning
        self.profiling_service.process_meal_feedback(user_id, meal_id, rating, emoji, comment)
        
        # Generate immediate response based on feedback
        response = {}
        
        if rating >= 4:
            responses = [
                "So glad you loved it! 🎉",
                "Yes! That's exactly what I was going for! ⭐",
                "Perfect! I'll remember this combo! 🎯"
            ]
            response['message'] = random.choice(responses)
            response['action'] = 'reinforce_elements'
            
        elif rating <= 2:
            responses = [
                "Good to know - I'll adjust for next time! 👍",
                "Thanks for the feedback! Learning your preferences! 📝",
                "Got it - I'll steer away from that style! ✅"
            ]
            response['message'] = random.choice(responses)
            response['action'] = 'avoid_elements'
            
        else:  # Rating 3
            responses = [
                "Thanks for the feedback! 👍",
                "Good to know - I'll keep tweaking! ⚙️"
            ]
            response['message'] = random.choice(responses)
            response['action'] = 'minor_adjustment'
        
        return response
    
    def generate_micro_prompt(self, user_id: str) -> Optional[str]:
        """Generate contextual micro-prompt for progressive learning"""
        return self.profiling_service.generate_micro_prompt(user_id)
    
    def _estimate_meal_cost(self, meal_plan: Dict[str, Any]) -> float:
        """Estimate total cost of meal plan"""
        # Simple estimation - would be more sophisticated in production
        meals_count = len(meal_plan.get('days', {})) * 3  # 3 meals per day
        return meals_count * 3.50  # Average $3.50 per meal
    
    def _detect_breakfast_skipping(self, user_profile: Dict[str, Any]) -> bool:
        """Detect if user often skips breakfast"""
        # Would analyze interaction patterns in production
        return False
    
    def _detect_heavy_meat_consumption(self, user_profile: Dict[str, Any]) -> bool:
        """Detect if user eats meat very frequently"""
        # Would analyze meal history in production
        return False
    
    def _detect_inflammation_concerns(self, user_profile: Dict[str, Any]) -> bool:
        """Detect if user has mentioned inflammation/joint issues"""
        # Would analyze conversation history in production
        return False
