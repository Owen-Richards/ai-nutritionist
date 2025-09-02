"""
Enhanced Universal Message Handler with Edamam Integration
Handles nutrition queries, recipe searches, and ingredient analysis
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional

from src.services.ai_service import AIService
from src.services.edamam_service import EdamamService
from src.services.user_service import UserService
from src.services.messaging_service import UniversalMessagingService

logger = logging.getLogger(__name__)


class EnhancedNutritionHandler:
    """Enhanced handler for nutrition-related queries with Edamam integration"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.edamam_service = EdamamService()
        self.user_service = UserService()
        self.messaging_service = UniversalMessagingService()
        
        # Define nutrition-related keywords
        self.nutrition_keywords = [
            'nutrition', 'nutritional', 'calories', 'protein', 'carbs', 'fat', 
            'vitamins', 'minerals', 'fiber', 'sodium', 'sugar', 'macro', 'micro'
        ]
        
        self.recipe_keywords = [
            'recipe', 'cooking', 'ingredients', 'prepare', 'make', 'cook',
            'how to', 'instructions', 'directions'
        ]
        
        self.substitution_keywords = [
            'substitute', 'replace', 'alternative', 'instead of', 'swap',
            'dairy-free', 'gluten-free', 'vegan', 'allergic'
        ]
    
    async def handle_message(self, message_text: str, user_profile: Dict[str, Any], 
                           platform: str = 'whatsapp') -> Dict[str, Any]:
        """
        Enhanced message handling with Edamam integration
        """
        try:
            message_lower = message_text.lower()
            
            # Determine message type and route appropriately
            if self._is_nutrition_query(message_lower):
                return await self._handle_nutrition_query(message_text, user_profile, platform)
            
            elif self._is_recipe_request(message_lower):
                return await self._handle_recipe_request(message_text, user_profile, platform)
            
            elif self._is_substitution_request(message_lower):
                return await self._handle_substitution_request(message_text, user_profile, platform)
            
            elif self._is_ingredient_analysis(message_lower):
                return await self._handle_ingredient_analysis(message_text, user_profile, platform)
            
            elif self._is_meal_plan_request(message_lower):
                return await self._handle_enhanced_meal_plan(message_text, user_profile, platform)
            
            else:
                # Fall back to standard AI service
                response = self.ai_service.get_nutrition_advice(message_text, user_profile)
                return {
                    'response': response,
                    'type': 'general_advice',
                    'platform_optimized': self._optimize_for_platform(response, platform)
                }
        
        except Exception as e:
            logger.error(f"Error handling enhanced message: {e}")
            return {
                'response': "I'm having trouble processing your request right now. Please try again in a moment.",
                'type': 'error',
                'platform_optimized': True
            }

    async def _handle_nutrition_query(self, message: str, user_profile: Dict, platform: str) -> Dict:
        """Handle detailed nutrition analysis queries"""
        try:
            # Extract ingredients from message if present
            ingredients = self._extract_ingredients_from_message(message)
            
            if ingredients:
                # Get enhanced nutrition analysis
                nutrition_result = await self.ai_service.get_enhanced_nutrition_analysis(
                    ingredients, user_profile
                )
                
                if nutrition_result['success']:
                    response_text = nutrition_result['whatsapp_summary']
                    
                    # Add personalized recommendations
                    if nutrition_result.get('recommendations'):
                        response_text += "\n\n🎯 **Recommendations:**\n"
                        for i, rec in enumerate(nutrition_result['recommendations'][:3], 1):
                            response_text += f"{i}. {rec}\n"
                    
                    return {
                        'response': response_text,
                        'type': 'nutrition_analysis',
                        'data': nutrition_result['nutrition_data'],
                        'platform_optimized': True
                    }
                else:
                    return {
                        'response': nutrition_result['fallback_advice'],
                        'type': 'nutrition_fallback',
                        'platform_optimized': True
                    }
            else:
                # General nutrition advice
                advice = self.ai_service.get_nutrition_advice(message, user_profile)
                return {
                    'response': advice,
                    'type': 'general_nutrition',
                    'platform_optimized': self._optimize_for_platform(advice, platform)
                }
                
        except Exception as e:
            logger.error(f"Error handling nutrition query: {e}")
            return {
                'response': "I can help with nutrition questions! Try asking about specific foods or meals.",
                'type': 'error'
            }

    async def _handle_recipe_request(self, message: str, user_profile: Dict, platform: str) -> Dict:
        """Handle recipe search and recommendations"""
        try:
            # Extract meal name from message
            meal_name = self._extract_meal_name_from_message(message)
            
            if not meal_name:
                return {
                    'response': "What type of recipe are you looking for? Try asking like 'show me a recipe for chicken stir fry'",
                    'type': 'clarification'
                }
            
            # Search for recipes using enhanced Edamam service
            recipe_results = await self.edamam_service.enhanced_recipe_search(
                meal_name, user_profile
            )
            
            if recipe_results and recipe_results.get('recipes'):
                # Format multiple recipe options
                response_text = f"🍽️ **Recipe Options for {meal_name.title()}:**\n\n"
                
                for i, recipe in enumerate(recipe_results['recipes'][:3], 1):
                    recipe_summary = self.edamam_service.format_recipe_for_whatsapp(recipe)
                    response_text += f"**Option {i}:**\n{recipe_summary}\n\n"
                
                response_text += "💡 *Reply with the option number for detailed instructions*"
                
                return {
                    'response': response_text,
                    'type': 'recipe_search',
                    'data': recipe_results,
                    'platform_optimized': True
                }
            else:
                # Fall back to AI-generated recipe
                ai_recipe = self.ai_service.get_nutrition_advice(
                    f"Please provide a simple recipe for {meal_name} considering my dietary restrictions", 
                    user_profile
                )
                
                return {
                    'response': f"🤖 **AI-Generated Recipe:**\n\n{ai_recipe}\n\n💡 *This is an AI-generated recipe. Double-check ingredients for allergies.*",
                    'type': 'ai_recipe',
                    'platform_optimized': True
                }
                
        except Exception as e:
            logger.error(f"Error handling recipe request: {e}")
            return {
                'response': "I'm having trouble finding recipes right now. Try describing what you'd like to cook!",
                'type': 'error'
            }

    async def _handle_substitution_request(self, message: str, user_profile: Dict, platform: str) -> Dict:
        """Handle ingredient substitution requests"""
        try:
            # Extract ingredient to substitute
            ingredient = self._extract_ingredient_for_substitution(message)
            
            if not ingredient:
                return {
                    'response': "What ingredient would you like to substitute? For example: 'What can I use instead of eggs?'",
                    'type': 'clarification'
                }
            
            # Get substitution suggestions
            substitutions = await self.edamam_service.suggest_substitutions(
                ingredient, user_profile.get('dietary_restrictions', [])
            )
            
            if substitutions:
                response_text = f"🔄 **Substitutes for {ingredient.title()}:**\n\n"
                
                for i, sub in enumerate(substitutions, 1):
                    response_text += f"{i}. {sub}\n"
                
                response_text += f"\n💡 *Based on your dietary restrictions: {', '.join(user_profile.get('dietary_restrictions', ['None']))}*"
                
                return {
                    'response': response_text,
                    'type': 'substitution',
                    'platform_optimized': True
                }
            else:
                # Fall back to AI suggestions
                ai_subs = self.ai_service.get_nutrition_advice(
                    f"What are good substitutes for {ingredient} considering my dietary restrictions?",
                    user_profile
                )
                
                return {
                    'response': f"🤖 **AI Suggestions:**\n\n{ai_subs}",
                    'type': 'ai_substitution',
                    'platform_optimized': True
                }
                
        except Exception as e:
            logger.error(f"Error handling substitution request: {e}")
            return {
                'response': "I can help you find ingredient substitutions! What would you like to replace?",
                'type': 'error'
            }

    async def _handle_ingredient_analysis(self, message: str, user_profile: Dict, platform: str) -> Dict:
        """Handle ingredient validation and analysis"""
        try:
            ingredients = self._extract_ingredients_from_message(message)
            
            if not ingredients:
                return {
                    'response': "Please list the ingredients you'd like me to analyze.",
                    'type': 'clarification'
                }
            
            # Validate ingredients using Food Database API
            results = []
            for ingredient in ingredients[:5]:  # Limit to 5 ingredients
                validation_result = await self.edamam_service.validate_ingredients(ingredient)
                results.append({
                    'ingredient': ingredient,
                    'validation': validation_result
                })
            
            # Format response
            response_text = "🔍 **Ingredient Analysis:**\n\n"
            
            for result in results:
                ingredient = result['ingredient']
                validation = result['validation']
                
                if validation.get('parsed_ingredients'):
                    parsed = validation['parsed_ingredients'][0]  # First match
                    response_text += f"✅ **{ingredient.title()}** - Recognized\n"
                    response_text += f"   Calories: {int(parsed.get('calories', 0))}/100g\n"
                    response_text += f"   Protein: {int(parsed.get('protein', 0))}g\n\n"
                else:
                    response_text += f"❓ **{ingredient.title()}** - Check spelling\n\n"
            
            response_text += "💡 *Reply 'nutrition analysis' for complete meal breakdown*"
            
            return {
                'response': response_text,
                'type': 'ingredient_analysis',
                'data': results,
                'platform_optimized': True
            }
            
        except Exception as e:
            logger.error(f"Error handling ingredient analysis: {e}")
            return {
                'response': "I can analyze ingredients for you! Just list them in your message.",
                'type': 'error'
            }

    async def _handle_enhanced_meal_plan(self, message: str, user_profile: Dict, platform: str) -> Dict:
        """Handle meal plan requests with enhanced recipe integration"""
        try:
            # Generate meal plan using AI service
            meal_plan = self.ai_service.generate_meal_plan(user_profile)
            
            if not meal_plan:
                return {
                    'response': "I'm having trouble creating your meal plan right now. Please try again.",
                    'type': 'error'
                }
            
            # Format meal plan for WhatsApp with enhanced features
            response_text = self._format_enhanced_meal_plan_for_whatsapp(meal_plan, user_profile)
            
            return {
                'response': response_text,
                'type': 'meal_plan',
                'data': meal_plan,
                'platform_optimized': True
            }
            
        except Exception as e:
            logger.error(f"Error handling enhanced meal plan: {e}")
            return {
                'response': "Let me create a personalized meal plan for you!",
                'type': 'error'
            }

    def _format_enhanced_meal_plan_for_whatsapp(self, meal_plan: Dict, user_profile: Dict) -> str:
        """Format enhanced meal plan with nutrition insights for WhatsApp"""
        try:
            response = f"🌟 **Your Personalized Weekly Meal Plan**\n"
            response += f"Budget: ${meal_plan.get('weekly_budget', 75)} | "
            response += f"Serves: {meal_plan.get('household_size', 1)}\n\n"
            
            # Show first 2 days with enhanced details
            days_shown = 0
            for day_key, day_data in meal_plan.get('days', {}).items():
                if days_shown >= 2:
                    break
                    
                response += f"📅 **{day_key.title()}**\n"
                
                for meal_type in ['breakfast', 'lunch', 'dinner']:
                    meal = day_data.get(meal_type)
                    if meal:
                        response += f"🍽️ {meal_type.title()}: {meal.get('name', 'TBD')}\n"
                        
                        # Add recipe info if available
                        if meal.get('recipe_data'):
                            recipe_data = meal['recipe_data']
                            response += f"   ⏱️ {recipe_data.get('prep_time', 30)} mins | "
                            response += f"🔥 {recipe_data.get('calories_per_serving', 0)} cal\n"
                
                # Add nutrition insights if available
                if day_data.get('nutrition_insights'):
                    insights = day_data['nutrition_insights'][:2]  # First 2 insights
                    response += "📊 Insights:\n"
                    for insight in insights:
                        response += f"   • {insight}\n"
                
                response += "\n"
                days_shown += 1
            
            # Add weekly summary
            if meal_plan.get('weekly_nutrition_summary'):
                response += "📈 **Weekly Nutrition Goals:**\n"
                summary = meal_plan['weekly_nutrition_summary']
                response += f"Avg Daily Calories: {summary.get('avg_calories', 'TBD')}\n"
                response += f"Protein Goal: {summary.get('protein_goal', 'TBD')}g/day\n\n"
            
            response += "📱 **Quick Actions:**\n"
            response += "• Reply 'full plan' for complete week\n"
            response += "• Reply 'grocery list' for shopping list\n"
            response += "• Reply 'nutrition day 1' for detailed analysis\n"
            response += "• Reply 'recipe [meal name]' for cooking instructions"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting enhanced meal plan: {e}")
            return "Meal plan generated! Reply 'full plan' to see all details."

    def _is_nutrition_query(self, message: str) -> bool:
        """Check if message is a nutrition-related query"""
        return any(keyword in message for keyword in self.nutrition_keywords)
    
    def _is_recipe_request(self, message: str) -> bool:
        """Check if message is requesting a recipe"""
        return any(keyword in message for keyword in self.recipe_keywords)
    
    def _is_substitution_request(self, message: str) -> bool:
        """Check if message is requesting ingredient substitutions"""
        return any(keyword in message for keyword in self.substitution_keywords)
    
    def _is_ingredient_analysis(self, message: str) -> bool:
        """Check if message is requesting ingredient analysis"""
        analysis_keywords = ['analyze', 'check', 'validate', 'what is', 'tell me about']
        return any(keyword in message for keyword in analysis_keywords) and \
               any(keyword in message for keyword in ['ingredient', 'food', 'nutrition'])
    
    def _is_meal_plan_request(self, message: str) -> bool:
        """Check if message is requesting a meal plan"""
        plan_keywords = ['meal plan', 'weekly plan', 'menu', 'what should i eat', 'plan my meals']
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in plan_keywords)
    
    def _extract_ingredients_from_message(self, message: str) -> list:
        """Extract ingredients from user message"""
        # Simple extraction - in production, would use NLP
        common_ingredients = [
            'chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna', 'eggs', 'milk', 'cheese',
            'rice', 'pasta', 'bread', 'potato', 'tomato', 'onion', 'garlic', 'carrot',
            'broccoli', 'spinach', 'apple', 'banana', 'orange', 'beans', 'lentils'
        ]
        
        found_ingredients = []
        message_lower = message.lower()
        
        for ingredient in common_ingredients:
            if ingredient in message_lower:
                found_ingredients.append(ingredient)
        
        return found_ingredients[:10]  # Limit to 10 ingredients
    
    def _extract_meal_name_from_message(self, message: str) -> Optional[str]:
        """Extract meal name from recipe request"""
        # Simple extraction - look for patterns like "recipe for X" or "how to make X"
        patterns = [
            'recipe for ', 'make ', 'cook ', 'prepare ', 'how to make '
        ]
        
        message_lower = message.lower()
        
        for pattern in patterns:
            if pattern in message_lower:
                start_idx = message_lower.find(pattern) + len(pattern)
                meal_part = message[start_idx:].strip()
                # Take first part (until punctuation or new sentence)
                meal_name = meal_part.split('?')[0].split('.')[0].split(',')[0].strip()
                if meal_name and len(meal_name) > 2:
                    return meal_name
        
        return None
    
    def _extract_ingredient_for_substitution(self, message: str) -> Optional[str]:
        """Extract ingredient to substitute from message"""
        patterns = [
            'substitute for ', 'instead of ', 'replace ', 'alternative to '
        ]
        
        message_lower = message.lower()
        
        for pattern in patterns:
            if pattern in message_lower:
                start_idx = message_lower.find(pattern) + len(pattern)
                ingredient_part = message[start_idx:].strip()
                ingredient = ingredient_part.split('?')[0].split('.')[0].split(',')[0].strip()
                if ingredient and len(ingredient) > 1:
                    return ingredient
        
        return None
    
    def _optimize_for_platform(self, response: str, platform: str) -> bool:
        """Check if response is already optimized for platform"""
        if platform == 'whatsapp':
            # Check if response has emoji and proper formatting
            return '🍽️' in response or '📊' in response or '💡' in response
        
        return False


# Lambda handler integration
def lambda_handler(event, context):
    """Enhanced Lambda handler with Edamam integration"""
    try:
        handler = EnhancedNutritionHandler()
        
        # Extract message details from event
        message_text = event.get('message', '')
        user_id = event.get('user_id', '')
        platform = event.get('platform', 'whatsapp')
        
        # Get user profile
        user_service = UserService()
        user_profile = user_service.get_user_profile(user_id)
        
        # Handle message asynchronously
        response_data = asyncio.run(
            handler.handle_message(message_text, user_profile, platform)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'response': response_data['response'],
                'type': response_data['type'],
                'user_id': user_id
            })
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced lambda handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'response': "I'm experiencing technical difficulties. Please try again in a moment.",
                'type': 'error'
            })
        }
