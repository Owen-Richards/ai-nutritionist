"""
AI Service for AWS Bedrock integration
Handles AI-powered meal plan generation and nutrition advice with prompt caching
"""

import json
import logging
import os
import hashlib
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import boto3
import requests
from botocore.exceptions import ClientError

from .edamam_service import EdamamService

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered nutrition assistance using AWS Bedrock"""
    
    def __init__(self):
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.dynamodb = boto3.resource('dynamodb')
        self.model_id = "amazon.titan-text-express-v1"  # Cost-effective model as specified
        
        # Prompt cache table for cost optimization
        self.cache_table = self.dynamodb.Table(os.getenv('PROMPT_CACHE_TABLE', 'ai-nutritionist-prompt-cache-dev'))
        
        # Enhanced Edamam service integration
        self.edamam_service = EdamamService()
        
        # Legacy recipe API integration (keeping for backward compatibility)
        self.recipe_api_key = self._get_parameter('/ai-nutritionist/edamam/api-key')
        self.recipe_app_id = self._get_parameter('/ai-nutritionist/edamam/app-id')
        
    def _get_parameter(self, parameter_name: str) -> Optional[str]:
        """Get parameter from Systems Manager Parameter Store"""
        try:
            ssm = boto3.client('ssm')
            response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Could not get parameter {parameter_name}: {e}")
            return None
        
    def generate_meal_plan(self, user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a weekly meal plan based on user profile and preferences
        Uses prompt caching for cost optimization as specified in AI Context
        """
        try:
            # Check cache first for cost optimization
            cache_key = self._generate_cache_key(user_profile)
            cached_plan = self._get_cached_response(cache_key)
            
            if cached_plan:
                logger.info(f"Returning cached meal plan for user {user_profile.get('user_id', 'unknown')}")
                return cached_plan
            
            prompt = self._build_meal_plan_prompt(user_profile)
            
            logger.info(f"Generating new meal plan for user {user_profile.get('user_id', 'unknown')}")
            
            response = self._invoke_model_with_cache(prompt, cache_key, max_tokens=3000)
            if response:
                meal_plan = self._parse_meal_plan_response(response)
                
                # Enrich with enhanced recipe data and nutrition analysis
                if meal_plan:
                    meal_plan = asyncio.run(self._enrich_with_enhanced_recipes(meal_plan, user_profile))
                
                return meal_plan
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            return None
    
    def get_nutrition_advice(self, question: str, user_profile: Dict[str, Any]) -> str:
        """
        Get AI-powered nutrition advice for general questions
        Uses caching for repeated questions
        """
        try:
            # Create cache key for nutrition questions
            cache_key = f"nutrition_{hashlib.md5(question.lower().encode()).hexdigest()}"
            cached_response = self._get_cached_response(cache_key)
            
            if cached_response:
                return cached_response.get('advice', '')
            
            prompt = self._build_nutrition_advice_prompt(question, user_profile)
            
            response = self._invoke_model_with_cache(prompt, cache_key, max_tokens=500)
            if response:
                advice = response.strip()
                # Cache nutrition advice
                self._cache_response(cache_key, {'advice': advice}, ttl_hours=24)
                return advice
            
            return "I'd be happy to help with nutrition questions! Please try rephrasing your question."
            
        except Exception as e:
            logger.error(f"Error getting nutrition advice: {str(e)}")
            return "I'm having trouble right now. Please try asking your question again in a moment."

    async def get_enhanced_nutrition_analysis(self, ingredients: List[str], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get enhanced nutrition analysis using Edamam API with AI insights
        """
        try:
            # Get detailed nutrition analysis
            nutrition_data = await self.edamam_service.analyze_meal_nutrition(
                ingredients, user_profile.get('user_id')
            )
            
            if 'error' in nutrition_data:
                return {
                    'success': False,
                    'message': nutrition_data['error'],
                    'fallback_advice': await self._get_ai_nutrition_fallback(ingredients, user_profile)
                }
            
            # Generate AI-powered insights based on nutrition data
            user_goals = {
                'daily_calories': user_profile.get('daily_calories', 2000),
                'fitness_goal': user_profile.get('fitness_goal', 'maintenance'),
                'dietary_restrictions': user_profile.get('dietary_restrictions', []),
                'health_conditions': user_profile.get('health_conditions', [])
            }
            
            ai_insights = await self._generate_ai_nutrition_insights(nutrition_data, user_goals)
            
            # Format for WhatsApp
            whatsapp_summary = self._format_detailed_nutrition_for_whatsapp(nutrition_data, ai_insights)
            
            return {
                'success': True,
                'nutrition_data': nutrition_data,
                'ai_insights': ai_insights,
                'whatsapp_summary': whatsapp_summary,
                'recommendations': await self._get_nutrition_recommendations(nutrition_data, user_goals)
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced nutrition analysis: {e}")
            return {
                'success': False,
                'message': 'Unable to analyze nutrition right now',
                'fallback_advice': "Focus on balanced meals with vegetables, proteins, and whole grains."
            }

    async def _generate_ai_nutrition_insights(self, nutrition_data: Dict, user_goals: Dict) -> List[str]:
        """Generate AI-powered nutrition insights"""
        try:
            # Build AI prompt for nutrition insights
            prompt = f"""
            Based on this nutrition analysis and user goals, provide 3-5 actionable insights:
            
            Nutrition Data:
            - Calories: {nutrition_data.get('calories', 0)}
            - Protein: {nutrition_data.get('macros', {}).get('protein', 0)}g
            - Carbs: {nutrition_data.get('macros', {}).get('carbs', 0)}g
            - Fat: {nutrition_data.get('macros', {}).get('fat', 0)}g
            - Fiber: {nutrition_data.get('macros', {}).get('fiber', 0)}g
            
            User Goals:
            - Target calories: {user_goals.get('daily_calories', 2000)}
            - Fitness goal: {user_goals.get('fitness_goal', 'maintenance')}
            - Dietary restrictions: {user_goals.get('dietary_restrictions', [])}
            
            Provide insights as a bulleted list focusing on:
            1. How well this meal aligns with their goals
            2. Specific nutrients that are high/low
            3. Actionable recommendations for improvement
            4. Meal timing suggestions if relevant
            
            Keep each insight under 25 words and actionable.
            """
            
            response = self._invoke_model(prompt, max_tokens=300)
            if response:
                # Parse AI response into list
                insights = [line.strip() for line in response.split('\n') if line.strip() and ('•' in line or '-' in line)]
                return insights[:5]  # Limit to 5 insights
            
            return ["Unable to generate personalized insights at this time."]
            
        except Exception as e:
            logger.error(f"Error generating AI nutrition insights: {e}")
            return ["Focus on balanced nutrition with adequate protein and fiber."]

    async def _get_ai_nutrition_fallback(self, ingredients: List[str], user_profile: Dict) -> str:
        """Get AI-generated nutrition advice when API fails"""
        try:
            ingredients_text = ', '.join(ingredients[:10])
            
            prompt = f"""
            Provide nutrition advice for a meal with these ingredients: {ingredients_text}
            
            User context:
            - Dietary restrictions: {user_profile.get('dietary_restrictions', [])}
            - Fitness goal: {user_profile.get('fitness_goal', 'maintenance')}
            
            Give a brief, encouraging assessment focusing on:
            1. Overall nutritional quality
            2. Key nutrients likely present
            3. One improvement suggestion
            
            Keep response under 100 words, friendly and actionable.
            """
            
            response = self._invoke_model(prompt, max_tokens=150)
            return response.strip() if response else "This looks like a nutritious meal choice!"
            
        except Exception as e:
            logger.error(f"Error in AI nutrition fallback: {e}")
            return "This appears to be a balanced meal with good nutritional value."

    def _format_detailed_nutrition_for_whatsapp(self, nutrition_data: Dict, ai_insights: List[str]) -> str:
        """Format detailed nutrition analysis for WhatsApp"""
        try:
            calories = int(nutrition_data.get('calories', 0))
            macros = nutrition_data.get('macros', {})
            vitamins = nutrition_data.get('vitamins', {})
            minerals = nutrition_data.get('minerals', {})
            
            # Build comprehensive summary
            summary = f"""📊 **Detailed Nutrition Analysis**

🔥 **Energy & Macros:**
Calories: {calories}
Protein: {int(macros.get('protein', 0))}g
Carbohydrates: {int(macros.get('carbs', 0))}g
Fat: {int(macros.get('fat', 0))}g
Fiber: {int(macros.get('fiber', 0))}g

💊 **Key Vitamins:**
Vitamin C: {int(vitamins.get('vitamin_c', 0))}mg
Vitamin D: {int(vitamins.get('vitamin_d', 0))}μg

🪨 **Important Minerals:**
Calcium: {int(minerals.get('calcium', 0))}mg
Iron: {int(minerals.get('iron', 0))}mg
Sodium: {int(minerals.get('sodium', 0))}mg

🎯 **AI Insights:**"""

            for i, insight in enumerate(ai_insights[:3], 1):
                summary += f"\n{i}. {insight}"
            
            summary += "\n\n💡 *Ask 'meal suggestions' for similar healthy options*"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error formatting detailed nutrition: {e}")
            return "Detailed nutrition analysis unavailable"

    async def _get_nutrition_recommendations(self, nutrition_data: Dict, user_goals: Dict) -> List[str]:
        """Get specific nutrition recommendations based on analysis"""
        try:
            recommendations = []
            
            calories = nutrition_data.get('calories', 0)
            macros = nutrition_data.get('macros', {})
            target_calories = user_goals.get('daily_calories', 2000)
            
            # Calorie recommendations
            if calories < target_calories * 0.3:  # Less than 30% of daily needs
                recommendations.append("Consider adding healthy snacks like nuts or fruit")
            elif calories > target_calories * 0.5:  # More than 50% of daily needs
                recommendations.append("This is quite filling - pair with lighter meals today")
            
            # Protein recommendations
            protein = macros.get('protein', 0)
            if protein < 15:
                recommendations.append("Add protein sources like eggs, beans, or lean meat")
            elif protein > 40:
                recommendations.append("Great protein content! Perfect for post-workout")
            
            # Fiber recommendations
            fiber = macros.get('fiber', 0)
            if fiber < 5:
                recommendations.append("Boost fiber with vegetables or whole grains")
            
            # Sodium recommendations
            sodium = nutrition_data.get('minerals', {}).get('sodium', 0)
            if sodium > 800:  # High sodium for a single meal
                recommendations.append("Watch sodium intake for the rest of the day")
            
            return recommendations[:3]  # Limit to top 3 recommendations
            
        except Exception as e:
            logger.error(f"Error getting nutrition recommendations: {e}")
            return ["Focus on balanced nutrition throughout the day"]
    
    def _generate_cache_key(self, user_profile: Dict[str, Any]) -> str:
        """Generate cache key for meal plans based on user preferences"""
        # Create hash of relevant user preferences for caching
        cache_data = {
            'dietary_restrictions': user_profile.get('dietary_restrictions', []),
            'budget': user_profile.get('budget', 75),
            'household_size': user_profile.get('household_size', 1),
            'fitness_goal': user_profile.get('fitness_goal', 'maintenance'),
            'week': datetime.now().strftime('%Y-W%U')  # Weekly cache
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"meal_plan_{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response from DynamoDB"""
        try:
            response = self.cache_table.get_item(Key={'cache_key': cache_key})
            
            if 'Item' in response:
                item = response['Item']
                # Check if not expired
                if datetime.now().timestamp() < item.get('expires_at', 0):
                    return item.get('data')
                
        except Exception as e:
            logger.warning(f"Error getting cached response: {e}")
            
        return None
    
    def _cache_response(self, cache_key: str, data: Dict[str, Any], ttl_hours: int = 168) -> None:
        """Cache response in DynamoDB with TTL"""
        try:
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            
            self.cache_table.put_item(
                Item={
                    'cache_key': cache_key,
                    'data': data,
                    'expires_at': int(expires_at.timestamp()),
                    'ttl': int(expires_at.timestamp())  # DynamoDB TTL
                }
            )
            
        except Exception as e:
            logger.warning(f"Error caching response: {e}")
    
    def _enrich_with_recipes(self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich meal plan with real recipe data from external APIs
        Uses Edamam API as suggested in the AI Context specifications
        """
        if not self.recipe_api_key or not self.recipe_app_id:
            return meal_plan
            
        try:
            # Extract dietary restrictions for API filtering
            diet_labels = []
            health_labels = []
            
            restrictions = user_profile.get('dietary_restrictions', [])
            if 'vegetarian' in restrictions:
                diet_labels.append('vegetarian')
            if 'vegan' in restrictions:
                diet_labels.append('vegan')
            if 'gluten-free' in restrictions:
                health_labels.append('gluten-free')
            if 'dairy-free' in restrictions:
                health_labels.append('dairy-free')
            
            # Enrich each day's meals
            enriched_plan = meal_plan.copy()
            
            for day_key, day_data in meal_plan.get('days', {}).items():
                for meal_type in ['breakfast', 'lunch', 'dinner']:
                    meal = day_data.get(meal_type)
                    if meal and isinstance(meal, dict):
                        recipe_data = self._fetch_recipe_data(
                            meal.get('name', ''),
                            diet_labels,
                            health_labels
                        )
                        
                        if recipe_data:
                            meal['recipe_url'] = recipe_data.get('url')
                            meal['prep_time'] = recipe_data.get('prep_time')
                            meal['servings'] = recipe_data.get('servings')
                            meal['verified_ingredients'] = recipe_data.get('ingredients', [])
            
            return enriched_plan
            
        except Exception as e:
            logger.warning(f"Error enriching with recipes: {e}")
            return meal_plan

    async def _enrich_with_enhanced_recipes(self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced meal plan enrichment with Edamam optimization and nutrition analysis
        """
        try:
            enriched_plan = meal_plan.copy()
            
            # Process each day's meals
            for day_key, day_data in meal_plan.get('days', {}).items():
                daily_ingredients = []
                
                for meal_type in ['breakfast', 'lunch', 'dinner', 'snacks']:
                    meal = day_data.get(meal_type)
                    if meal and isinstance(meal, dict):
                        meal_name = meal.get('name', '')
                        
                        # Enhanced recipe search
                        recipe_results = await self.edamam_service.enhanced_recipe_search(
                            meal_name, user_profile
                        )
                        
                        if recipe_results and recipe_results.get('recipes'):
                            # Use the best recipe (first one after scoring)
                            best_recipe = recipe_results['recipes'][0]
                            
                            # Enrich meal with detailed recipe data
                            meal['recipe_data'] = {
                                'url': best_recipe.get('url'),
                                'shareAs': best_recipe.get('shareAs'),
                                'image': best_recipe.get('image'),
                                'prep_time': best_recipe.get('totalTime', 30),
                                'servings': best_recipe.get('yield', 4),
                                'difficulty': best_recipe.get('difficulty', 3),
                                'calories_per_serving': int(best_recipe.get('calories', 0) / max(best_recipe.get('yield', 4), 1)),
                                'diet_labels': best_recipe.get('dietLabels', []),
                                'health_labels': best_recipe.get('healthLabels', [])
                            }
                            
                            # Format for WhatsApp if needed
                            meal['whatsapp_format'] = self.edamam_service.format_recipe_for_whatsapp(best_recipe)
                            
                            # Collect ingredients for nutrition analysis
                            ingredients = best_recipe.get('ingredients', [])
                            ingredient_texts = [ing.get('text', '') if isinstance(ing, dict) else str(ing) 
                                              for ing in ingredients]
                            daily_ingredients.extend(ingredient_texts)
                            
                            # Add ingredient substitutions if dietary restrictions
                            if user_profile.get('dietary_restrictions'):
                                substitutions = {}
                                for ingredient_data in ingredients[:5]:  # Check top 5 ingredients
                                    ingredient_text = ingredient_data.get('text', '') if isinstance(ingredient_data, dict) else str(ingredient_data)
                                    if ingredient_text:
                                        subs = await self.edamam_service.suggest_substitutions(
                                            ingredient_text, user_profile.get('dietary_restrictions', [])
                                        )
                                        if subs:
                                            substitutions[ingredient_text] = subs
                                
                                if substitutions:
                                    meal['substitution_suggestions'] = substitutions
                
                # Analyze daily nutrition if we have ingredients
                if daily_ingredients:
                    daily_nutrition = await self.edamam_service.analyze_meal_nutrition(
                        daily_ingredients, user_profile.get('user_id')
                    )
                    
                    if daily_nutrition and 'error' not in daily_nutrition:
                        # Add nutrition insights
                        user_goals = {
                            'daily_calories': user_profile.get('daily_calories', 2000),
                            'fitness_goal': user_profile.get('fitness_goal', 'maintenance')
                        }
                        
                        insights = self.edamam_service._generate_nutrition_insights(
                            daily_nutrition, user_goals
                        )
                        
                        enriched_plan['days'][day_key]['nutrition_analysis'] = daily_nutrition
                        enriched_plan['days'][day_key]['nutrition_insights'] = insights
                        
                        # Add nutrition summary for WhatsApp
                        nutrition_summary = self._format_nutrition_summary(daily_nutrition)
                        enriched_plan['days'][day_key]['nutrition_summary'] = nutrition_summary
            
            return enriched_plan
            
        except Exception as e:
            logger.error(f"Error in enhanced recipe enrichment: {e}")
            return meal_plan

    def _format_nutrition_summary(self, nutrition_data: Dict) -> str:
        """Format nutrition data for WhatsApp display"""
        try:
            calories = int(nutrition_data.get('calories', 0))
            macros = nutrition_data.get('macros', {})
            
            protein = int(macros.get('protein', 0))
            carbs = int(macros.get('carbs', 0))
            fat = int(macros.get('fat', 0))
            fiber = int(macros.get('fiber', 0))
            
            return f"""📊 **Daily Nutrition Summary**
🔥 Calories: {calories}
💪 Protein: {protein}g
🌾 Carbs: {carbs}g
🥑 Fat: {fat}g
🌿 Fiber: {fiber}g

*Reply "nutrition details" for complete breakdown*"""
            
        except Exception as e:
            logger.error(f"Error formatting nutrition summary: {e}")
            return "Nutrition summary unavailable"
    
    def _fetch_recipe_data(self, meal_name: str, diet_labels: List[str], health_labels: List[str]) -> Optional[Dict[str, Any]]:
        """Fetch recipe data from Edamam API"""
        try:
            # Check recipe cache first
            recipe_cache_key = f"recipe_{hashlib.md5(meal_name.lower().encode()).hexdigest()}"
            cached_recipe = self._get_cached_response(recipe_cache_key)
            
            if cached_recipe:
                return cached_recipe
            
            # Build API request
            params = {
                'type': 'public',
                'q': meal_name,
                'app_id': self.recipe_app_id,
                'app_key': self.recipe_api_key,
                'from': 0,
                'to': 3,  # Get top 3 results
                'random': 'true'
            }
            
            # Add dietary filters
            if diet_labels:
                params['diet'] = diet_labels
            if health_labels:
                params['health'] = health_labels
            
            response = requests.get(
                'https://api.edamam.com/search',
                params=params,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get('hits', [])
                
                if hits:
                    recipe = hits[0]['recipe']  # Use first result
                    recipe_data = {
                        'url': recipe.get('url'),
                        'prep_time': recipe.get('totalTime', 30),
                        'servings': recipe.get('yield', 4),
                        'ingredients': [ing['text'] for ing in recipe.get('ingredients', [])][:10]  # Limit ingredients
                    }
                    
                    # Cache for 7 days
                    self._cache_response(recipe_cache_key, recipe_data, ttl_hours=168)
                    
                    return recipe_data
                    
        except Exception as e:
            logger.warning(f"Error fetching recipe for {meal_name}: {e}")
            
        return None
    
    def generate_grocery_list(self, meal_plan: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate grocery list from meal plan
        """
        try:
            prompt = self._build_grocery_list_prompt(meal_plan)
            
            response = self._invoke_model(prompt, max_tokens=1000)
            if response:
                return self._parse_grocery_list_response(response)
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating grocery list: {str(e)}")
            return []
    
    def _invoke_model_with_cache(self, prompt: str, cache_key: str, max_tokens: int = 1000) -> Optional[str]:
        """
        Invoke Bedrock model with cost optimization and caching
        """
        try:
            # Track usage for cost monitoring
            self._track_bedrock_usage(len(prompt.split()))
            
            # Prepare the request body for Titan Text Express
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": 0.3,  # Lower temperature for more consistent responses
                    "topP": 0.9,
                    "stopSequences": ["Human:", "Assistant:"]
                }
            })
            
            # Invoke the model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text from Titan response
            generated_text = None
            if 'results' in response_body and len(response_body['results']) > 0:
                generated_text = response_body['results'][0]['outputText'].strip()
                
                # Cache successful responses for cost optimization
                if generated_text:
                    self._cache_response(cache_key, {'response': generated_text})
            
            return generated_text
            
        except ClientError as e:
            logger.error(f"Error invoking Bedrock model: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None
    
    def _track_bedrock_usage(self, token_count: int) -> None:
        """Track Bedrock API usage for cost monitoring"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            usage_key = f"bedrock_usage_{today}"
            
            # Get current usage
            response = self.cache_table.get_item(Key={'cache_key': usage_key})
            
            current_usage = 0
            if 'Item' in response:
                current_usage = response['Item'].get('data', {}).get('token_count', 0)
            
            # Update usage
            new_usage = current_usage + token_count
            
            self.cache_table.put_item(
                Item={
                    'cache_key': usage_key,
                    'data': {'token_count': new_usage},
                    'ttl': int((datetime.now() + timedelta(days=7)).timestamp())
                }
            )
            
        except Exception as e:
            logger.warning(f"Error tracking Bedrock usage: {e}")

    def _invoke_model(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """
        Invoke AWS Bedrock model with the given prompt
        """
        try:
            # Prepare the request body for Titan Text Express
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": 0.7,
                    "topP": 0.9,
                    "stopSequences": ["Human:", "Assistant:"]
                }
            })
            
            # Invoke the model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text from Titan response
            if 'results' in response_body and len(response_body['results']) > 0:
                return response_body['results'][0]['outputText']
            
            return None
            
        except ClientError as e:
            logger.error(f"Error invoking Bedrock model: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None
    
    def _build_meal_plan_prompt(self, user_profile: Dict[str, Any]) -> str:
        """
        Build optimized prompt for meal plan generation
        """
        # Extract user preferences
        dietary_restrictions = user_profile.get('dietary_restrictions', [])
        household_size = user_profile.get('household_size', 2)
        budget = user_profile.get('weekly_budget', 75)
        fitness_goals = user_profile.get('fitness_goals', 'maintenance')
        allergies = user_profile.get('allergies', [])
        
        # Build the prompt
        prompt = f"""You are a professional nutritionist creating a weekly meal plan. 

User Profile:
- Household size: {household_size} people
- Weekly food budget: ${budget}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Allergies: {', '.join(allergies) if allergies else 'None'}
- Fitness goals: {fitness_goals}

Requirements:
1. Create a 7-day meal plan (Monday-Sunday)
2. Include breakfast, lunch, and dinner for each day
3. Focus on budget-friendly, nutritious ingredients
4. Ensure meals are practical and not too complex
5. Consider batch cooking and leftovers to save money
6. Aim for balanced nutrition supporting the fitness goals
7. Respect all dietary restrictions and allergies

Please format your response as JSON with this structure:
{{
    "days": [
        {{
            "day": "Monday",
            "breakfast": "Meal name and brief description",
            "lunch": "Meal name and brief description", 
            "dinner": "Meal name and brief description"
        }}
    ],
    "estimated_cost": 75,
    "nutrition_notes": "Brief weekly nutrition summary",
    "prep_tips": "Time-saving preparation suggestions"
}}

Generate the meal plan now:"""

        return prompt
    
    def _build_nutrition_advice_prompt(self, question: str, user_profile: Dict[str, Any]) -> str:
        """
        Build prompt for general nutrition advice
        """
        dietary_restrictions = user_profile.get('dietary_restrictions', [])
        fitness_goals = user_profile.get('fitness_goals', 'maintenance')
        
        prompt = f"""You are a knowledgeable nutritionist providing helpful, evidence-based advice.

User context:
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Fitness goals: {fitness_goals}

User question: "{question}"

Please provide a helpful, accurate response that:
1. Is concise but informative (2-3 sentences max)
2. Considers the user's dietary restrictions and goals
3. Focuses on practical, actionable advice
4. Avoids medical claims or diagnosis
5. Includes a brief disclaimer if giving health advice

Response:"""

        return prompt
    
    def _build_grocery_list_prompt(self, meal_plan: Dict[str, Any]) -> str:
        """
        Build prompt for grocery list generation
        """
        meal_plan_text = json.dumps(meal_plan, indent=2)
        
        prompt = f"""Based on this meal plan, create a comprehensive grocery shopping list:

{meal_plan_text}

Requirements:
1. List all ingredients needed for the meals
2. Combine duplicate items and estimate quantities
3. Organize by grocery store sections
4. Focus on budget-friendly options
5. Include basic pantry staples if mentioned

Format as JSON:
{{
    "items": [
        {{
            "name": "Item name with estimated quantity",
            "category": "Produce/Dairy/Meat/Pantry/etc"
        }}
    ]
}}

Generate the grocery list:"""

        return prompt
    
    def _parse_meal_plan_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse AI response and extract meal plan data
        """
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                meal_plan = json.loads(json_str)
                
                # Validate required fields
                if 'days' in meal_plan and isinstance(meal_plan['days'], list):
                    return meal_plan
            
            # Fallback: create structured plan from text
            return self._parse_text_meal_plan(response)
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON meal plan, attempting text parsing")
            return self._parse_text_meal_plan(response)
        except Exception as e:
            logger.error(f"Error parsing meal plan response: {str(e)}")
            return None
    
    def _parse_text_meal_plan(self, response: str) -> Dict[str, Any]:
        """
        Fallback parser for text-based meal plan responses
        """
        try:
            days = []
            lines = response.split('\n')
            current_day = None
            
            for line in lines:
                line = line.strip()
                if any(day in line.lower() for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                    if current_day:
                        days.append(current_day)
                    current_day = {'day': line.split(':')[0].strip()}
                elif current_day and ('breakfast' in line.lower() or 'lunch' in line.lower() or 'dinner' in line.lower()):
                    meal_type = 'breakfast' if 'breakfast' in line.lower() else ('lunch' if 'lunch' in line.lower() else 'dinner')
                    meal_desc = line.split(':', 1)[1].strip() if ':' in line else line
                    current_day[meal_type] = meal_desc
            
            if current_day:
                days.append(current_day)
            
            return {
                'days': days,
                'estimated_cost': 75,
                'nutrition_notes': 'Balanced weekly nutrition plan',
                'prep_tips': 'Consider meal prep on weekends'
            }
            
        except Exception as e:
            logger.error(f"Error parsing text meal plan: {str(e)}")
            return {
                'days': [],
                'estimated_cost': 75,
                'nutrition_notes': 'Please try generating the plan again',
                'prep_tips': ''
            }
    
    def _parse_grocery_list_response(self, response: str) -> List[Dict[str, str]]:
        """
        Parse grocery list from AI response
        """
        try:
            # Try to extract JSON
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                grocery_data = json.loads(json_str)
                
                if 'items' in grocery_data:
                    return grocery_data['items']
            
            # Fallback: parse text list
            return self._parse_text_grocery_list(response)
            
        except json.JSONDecodeError:
            return self._parse_text_grocery_list(response)
        except Exception as e:
            logger.error(f"Error parsing grocery list: {str(e)}")
            return []
    
    def _parse_text_grocery_list(self, response: str) -> List[Dict[str, str]]:
        """
        Parse grocery list from plain text
        """
        items = []
        lines = response.split('\n')
        current_category = 'Other'
        
        for line in lines:
            line = line.strip()
            if line and ':' in line and not line.startswith('•') and not line.startswith('-'):
                # Likely a category header
                current_category = line.replace(':', '').strip()
            elif line and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                # List item
                item_name = line[1:].strip()
                if item_name:
                    items.append({
                        'name': item_name,
                        'category': current_category
                    })
        
        return items
