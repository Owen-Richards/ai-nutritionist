"""
Enhanced Edamam API Integration Service
Optimized for WhatsApp/SMS AI nutritionist bot with smart caching and cost management
"""

import json
import logging
import hashlib
import asyncio
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

import boto3
import requests
import aiohttp
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class EdamamService:
    """Enhanced Edamam API integration with smart caching and cost optimization"""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.ssm = boto3.client('ssm')
        
        # Initialize cache table
        self.cache_table = self.dynamodb.Table(os.getenv('CACHE_TABLE_NAME', 'ai-nutritionist-cache-dev'))
        
        # API credentials
        self.recipe_api_key = self._get_parameter('/ai-nutritionist/edamam/recipe-api-key')
        self.recipe_app_id = self._get_parameter('/ai-nutritionist/edamam/recipe-app-id')
        self.nutrition_api_key = self._get_parameter('/ai-nutritionist/edamam/nutrition-api-key')
        self.nutrition_app_id = self._get_parameter('/ai-nutritionist/edamam/nutrition-app-id')
        self.food_db_api_key = self._get_parameter('/ai-nutritionist/edamam/food-db-api-key')
        self.food_db_app_id = self._get_parameter('/ai-nutritionist/edamam/food-db-app-id')
        
        # API endpoints
        self.recipe_search_url = "https://api.edamam.com/api/recipes/v2"
        self.nutrition_analysis_url = "https://api.edamam.com/api/nutrition-details"
        self.food_database_url = "https://api.edamam.com/api/food-database/v2/parser"
        
        # Usage tracking table
        self.usage_table = self.dynamodb.Table(os.getenv('API_USAGE_TABLE_NAME', 'ai-nutritionist-api-usage-dev'))
        
    def _get_parameter(self, parameter_name: str) -> Optional[str]:
        """Get parameter from Systems Manager Parameter Store"""
        try:
            response = self.ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Could not get parameter {parameter_name}: {e}")
            return None

    async def enhanced_recipe_search(self, meal_name: str, user_profile: Dict) -> Dict:
        """
        Multi-criteria recipe search optimized for WhatsApp responses
        """
        if not self.recipe_api_key or not self.recipe_app_id:
            return {}
            
        try:
            # Build search parameters
            search_params = {
                'type': 'public',
                'q': meal_name,
                'app_id': self.recipe_app_id,
                'app_key': self.recipe_api_key,
                'from': 0,
                'to': 5,
                'random': 'true',
                'imageSize': 'SMALL',  # Faster loading for WhatsApp
                'field': [
                    'uri', 'label', 'images', 'totalTime', 'yield', 
                    'ingredients', 'calories', 'dietLabels', 'healthLabels',
                    'url', 'shareAs'
                ]
            }
            
            # Add user-specific filters
            diet_labels = self._extract_diet_labels(user_profile)
            health_labels = self._extract_health_labels(user_profile)
            
            if diet_labels:
                search_params['diet'] = diet_labels
            if health_labels:
                search_params['health'] = health_labels
                
            # Add time and calorie constraints
            max_prep_time = user_profile.get('max_prep_time', 45)
            min_calories = user_profile.get('min_calories', 200)
            max_calories = user_profile.get('max_calories', 800)
            
            search_params['time'] = f"1-{max_prep_time}"
            search_params['calories'] = f"{min_calories}-{max_calories}"
            
            # Check cache first (48-hour TTL for recipes)
            cache_key = f"recipe_search:{hashlib.md5(json.dumps(search_params, sort_keys=True).encode()).hexdigest()}"
            cached_result = await self._get_from_cache(cache_key)
            
            if cached_result:
                logger.info(f"Returning cached recipe search for: {meal_name}")
                return cached_result
            
            # Make API call
            result = await self._make_edamam_request(self.recipe_search_url, search_params)
            
            if result and 'hits' in result:
                # Process and score recipes
                processed_recipes = self._process_recipe_results(result['hits'], user_profile)
                
                # Cache result for 48 hours
                await self._cache_result(cache_key, processed_recipes, 48)
                
                # Log usage
                await self._log_api_usage('recipe_search', 0.002)  # Estimated cost per call
                
                return processed_recipes
                
            return {}
            
        except Exception as e:
            logger.error(f"Error in enhanced recipe search: {e}")
            return {}

    async def analyze_meal_nutrition(self, ingredients_list: List[str], user_id: str = None) -> Dict:
        """
        Analyze complete meal nutrition for optimization
        """
        if not self.nutrition_api_key or not self.nutrition_app_id:
            return {}
            
        try:
            # Check usage limits first
            if user_id and not await self._check_usage_limits(user_id, 'nutrition_analysis'):
                logger.warning(f"User {user_id} exceeded nutrition analysis limits")
                return {'error': 'Daily nutrition analysis limit reached'}
            
            # Prepare ingredients for analysis
            ingredients_data = {
                'title': 'Meal Nutrition Analysis',
                'ingr': ingredients_list[:20]  # Limit to 20 ingredients
            }
            
            # Check cache first (24-hour TTL)
            cache_key = f"nutrition_analysis:{hashlib.md5(json.dumps(ingredients_list, sort_keys=True).encode()).hexdigest()}"
            cached_result = await self._get_from_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Make API call
            headers = {
                'Content-Type': 'application/json',
            }
            
            params = {
                'app_id': self.nutrition_app_id,
                'app_key': self.nutrition_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.nutrition_analysis_url,
                    json=ingredients_data,
                    params=params,
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Process nutrition data
                        processed_nutrition = self._process_nutrition_data(result)
                        
                        # Cache for 24 hours
                        await self._cache_result(cache_key, processed_nutrition, 24)
                        
                        # Log usage
                        await self._log_api_usage('nutrition_analysis', 0.005, user_id)
                        
                        return processed_nutrition
                    else:
                        logger.error(f"Nutrition API error: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Error in nutrition analysis: {e}")
            return {}

    async def validate_ingredients(self, ingredient_text: str) -> Dict:
        """
        Parse and validate ingredients for accurate nutrition
        """
        if not self.food_db_api_key or not self.food_db_app_id:
            return {}
            
        try:
            # Check cache first (7-day TTL for ingredient parsing)
            cache_key = f"ingredient_validation:{hashlib.md5(ingredient_text.lower().encode()).hexdigest()}"
            cached_result = await self._get_from_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            params = {
                'app_id': self.food_db_app_id,
                'app_key': self.food_db_api_key,
                'ingr': ingredient_text,
                'nutrition-type': 'cooking'
            }
            
            result = await self._make_edamam_request(self.food_database_url, params)
            
            if result and 'parsed' in result:
                processed_ingredients = self._process_ingredient_data(result)
                
                # Cache for 7 days
                await self._cache_result(cache_key, processed_ingredients, 168)
                
                # Log usage
                await self._log_api_usage('food_database', 0.001)
                
                return processed_ingredients
                
            return {}
            
        except Exception as e:
            logger.error(f"Error validating ingredients: {e}")
            return {}

    def format_recipe_for_whatsapp(self, recipe_data: Dict) -> str:
        """
        Format Edamam recipe data for optimal WhatsApp display
        """
        if not recipe_data:
            return ""
            
        try:
            name = recipe_data.get('label', 'Delicious Recipe')
            time = recipe_data.get('totalTime', 'Quick')
            servings = recipe_data.get('yield', 2)
            calories = int(recipe_data.get('calories', 0))
            
            # Format ingredients list
            ingredients = recipe_data.get('ingredients', [])
            ingredients_text = self._format_ingredients_list(ingredients[:8])  # Limit for WhatsApp
            
            # Get short URL
            recipe_url = recipe_data.get('shareAs', recipe_data.get('url', ''))
            if len(recipe_url) > 50:
                recipe_url = recipe_url[:47] + "..."
            
            return f"""🍽️ **{name}**
⏱️ {time} mins | 👥 Serves {servings}
🔥 {calories} calories

📝 **Ingredients:**
{ingredients_text}

🔗 Recipe: {recipe_url}

💡 *Reply with "nutrition" for detailed analysis*"""
            
        except Exception as e:
            logger.error(f"Error formatting recipe for WhatsApp: {e}")
            return "Recipe details unavailable"

    def add_nutrition_insights(self, meal_plan: Dict, user_goals: Dict) -> Dict:
        """
        Enhance AI meal plans with Edamam nutrition analysis
        """
        try:
            enhanced_plan = meal_plan.copy()
            
            # Collect all ingredients from the day
            daily_ingredients = []
            
            for day_key, day_data in meal_plan.get('days', {}).items():
                day_ingredients = []
                
                for meal_type in ['breakfast', 'lunch', 'dinner', 'snacks']:
                    meal = day_data.get(meal_type)
                    if meal and isinstance(meal, dict):
                        ingredients = meal.get('ingredients', [])
                        day_ingredients.extend(ingredients)
                
                # Analyze daily nutrition (would need async context in real usage)
                if day_ingredients:
                    # This would be called asynchronously in practice
                    daily_nutrition = {}  # Placeholder for nutrition analysis
                    
                    # Generate insights
                    insights = self._generate_nutrition_insights(daily_nutrition, user_goals)
                    
                    enhanced_plan['days'][day_key]['nutrition_insights'] = insights
                    enhanced_plan['days'][day_key]['daily_totals'] = daily_nutrition
            
            return enhanced_plan
            
        except Exception as e:
            logger.error(f"Error adding nutrition insights: {e}")
            return meal_plan

    async def suggest_substitutions(self, ingredient: str, dietary_restrictions: List[str]) -> List[str]:
        """
        Use Food Database API to suggest suitable ingredient substitutions
        """
        try:
            # Validate original ingredient
            original_data = await self.validate_ingredients(ingredient)
            
            if not original_data:
                return []
            
            # Build substitution search based on dietary restrictions
            substitutions = []
            
            # Common substitution mappings
            substitution_map = {
                'dairy-free': {
                    'milk': ['almond milk', 'oat milk', 'coconut milk'],
                    'butter': ['coconut oil', 'olive oil', 'vegan butter'],
                    'cheese': ['nutritional yeast', 'cashew cheese', 'almond cheese']
                },
                'gluten-free': {
                    'flour': ['almond flour', 'rice flour', 'coconut flour'],
                    'bread': ['gluten-free bread', 'lettuce wraps', 'rice cakes'],
                    'pasta': ['rice pasta', 'quinoa pasta', 'zucchini noodles']
                },
                'vegan': {
                    'eggs': ['flax eggs', 'chia eggs', 'applesauce'],
                    'honey': ['maple syrup', 'agave syrup', 'date syrup'],
                    'meat': ['tofu', 'tempeh', 'seitan', 'lentils']
                }
            }
            
            # Find substitutions based on restrictions
            for restriction in dietary_restrictions:
                if restriction in substitution_map:
                    for food_type, subs in substitution_map[restriction].items():
                        if food_type.lower() in ingredient.lower():
                            substitutions.extend(subs)
            
            return substitutions[:3]  # Return top 3 suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting substitutions: {e}")
            return []

    def calculate_recipe_difficulty(self, recipe: Dict, user_skill: str) -> int:
        """
        Score recipe difficulty based on ingredients, time, and techniques
        """
        try:
            difficulty_score = 1  # Base difficulty (1-5 scale)
            
            # Factor in cooking time
            total_time = recipe.get('totalTime', 30)
            if total_time > 60:
                difficulty_score += 2
            elif total_time > 30:
                difficulty_score += 1
            
            # Factor in number of ingredients
            ingredients_count = len(recipe.get('ingredients', []))
            if ingredients_count > 15:
                difficulty_score += 2
            elif ingredients_count > 10:
                difficulty_score += 1
            
            # Factor in cooking techniques (based on ingredient descriptions)
            ingredients_text = ' '.join([ing.get('text', '') for ing in recipe.get('ingredients', [])])
            complex_techniques = ['marinate', 'braise', 'sauté', 'julienne', 'emulsify', 'fold', 'temper']
            
            for technique in complex_techniques:
                if technique in ingredients_text.lower():
                    difficulty_score += 1
            
            # Adjust for user skill level
            skill_adjustments = {
                'beginner': 0,
                'intermediate': -1,
                'advanced': -2
            }
            
            difficulty_score += skill_adjustments.get(user_skill, 0)
            
            # Ensure score stays within 1-5 range
            return max(1, min(5, difficulty_score))
            
        except Exception as e:
            logger.error(f"Error calculating recipe difficulty: {e}")
            return 3  # Default medium difficulty

    # Helper methods
    
    def _extract_diet_labels(self, user_profile: Dict) -> List[str]:
        """Extract Edamam diet labels from user profile"""
        diet_labels = []
        restrictions = user_profile.get('dietary_restrictions', [])
        
        mapping = {
            'vegetarian': 'vegetarian',
            'vegan': 'vegan',
            'low-carb': 'low-carb',
            'high-protein': 'high-protein',
            'keto': 'low-carb'
        }
        
        for restriction in restrictions:
            if restriction.lower() in mapping:
                diet_labels.append(mapping[restriction.lower()])
        
        return diet_labels

    def _extract_health_labels(self, user_profile: Dict) -> List[str]:
        """Extract Edamam health labels from user profile"""
        health_labels = []
        restrictions = user_profile.get('dietary_restrictions', [])
        allergies = user_profile.get('allergies', [])
        
        mapping = {
            'gluten-free': 'gluten-free',
            'dairy-free': 'dairy-free',
            'nut-free': 'tree-nut-free',
            'egg-free': 'egg-free',
            'soy-free': 'soy-free',
            'low-sodium': 'low-sodium'
        }
        
        for item in restrictions + allergies:
            if item.lower() in mapping:
                health_labels.append(mapping[item.lower()])
        
        return health_labels

    def _process_recipe_results(self, hits: List[Dict], user_profile: Dict) -> Dict:
        """Process and score recipe results"""
        processed_recipes = []
        
        for hit in hits[:3]:  # Top 3 recipes
            recipe = hit.get('recipe', {})
            
            # Calculate relevance score
            difficulty = self.calculate_recipe_difficulty(recipe, user_profile.get('cooking_skill', 'intermediate'))
            
            processed_recipe = {
                'label': recipe.get('label'),
                'url': recipe.get('url'),
                'shareAs': recipe.get('shareAs'),
                'image': recipe.get('image'),
                'totalTime': recipe.get('totalTime', 30),
                'yield': recipe.get('yield', 4),
                'calories': recipe.get('calories', 0),
                'ingredients': recipe.get('ingredients', [])[:10],  # Limit ingredients
                'difficulty': difficulty,
                'dietLabels': recipe.get('dietLabels', []),
                'healthLabels': recipe.get('healthLabels', [])
            }
            
            processed_recipes.append(processed_recipe)
        
        return {
            'recipes': processed_recipes,
            'total_found': len(processed_recipes),
            'search_timestamp': datetime.now().isoformat()
        }

    def _process_nutrition_data(self, nutrition_result: Dict) -> Dict:
        """Process nutrition analysis result"""
        try:
            nutrition = nutrition_result.get('totalNutrients', {})
            daily_values = nutrition_result.get('totalDaily', {})
            
            processed = {
                'calories': nutrition_result.get('calories', 0),
                'totalWeight': nutrition_result.get('totalWeight', 0),
                'macros': {
                    'protein': nutrition.get('PROCNT', {}).get('quantity', 0),
                    'carbs': nutrition.get('CHOCDF', {}).get('quantity', 0),
                    'fat': nutrition.get('FAT', {}).get('quantity', 0),
                    'fiber': nutrition.get('FIBTG', {}).get('quantity', 0)
                },
                'vitamins': {
                    'vitamin_c': nutrition.get('VITC', {}).get('quantity', 0),
                    'vitamin_d': nutrition.get('VITD', {}).get('quantity', 0),
                    'vitamin_b12': nutrition.get('VITB12', {}).get('quantity', 0)
                },
                'minerals': {
                    'calcium': nutrition.get('CA', {}).get('quantity', 0),
                    'iron': nutrition.get('FE', {}).get('quantity', 0),
                    'sodium': nutrition.get('NA', {}).get('quantity', 0)
                },
                'daily_values': {
                    'protein': daily_values.get('PROCNT', {}).get('quantity', 0),
                    'vitamin_c': daily_values.get('VITC', {}).get('quantity', 0),
                    'calcium': daily_values.get('CA', {}).get('quantity', 0)
                }
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing nutrition data: {e}")
            return {}

    def _process_ingredient_data(self, food_db_result: Dict) -> Dict:
        """Process food database result"""
        try:
            parsed = food_db_result.get('parsed', [])
            hints = food_db_result.get('hints', [])
            
            processed = {
                'parsed_ingredients': [],
                'suggestions': []
            }
            
            for item in parsed:
                food = item.get('food', {})
                processed['parsed_ingredients'].append({
                    'label': food.get('label'),
                    'known': True,
                    'calories': food.get('nutrients', {}).get('ENERC_KCAL', 0),
                    'protein': food.get('nutrients', {}).get('PROCNT', 0),
                    'carbs': food.get('nutrients', {}).get('CHOCDF', 0)
                })
            
            for hint in hints[:3]:  # Top 3 suggestions
                food = hint.get('food', {})
                processed['suggestions'].append({
                    'label': food.get('label'),
                    'category': food.get('category'),
                    'calories': food.get('nutrients', {}).get('ENERC_KCAL', 0)
                })
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing ingredient data: {e}")
            return {}

    def _format_ingredients_list(self, ingredients: List[Dict]) -> str:
        """Format ingredients list for WhatsApp"""
        if not ingredients:
            return "No ingredients listed"
        
        formatted = []
        for i, ingredient in enumerate(ingredients[:8], 1):  # Limit to 8 for WhatsApp
            text = ingredient.get('text', '') if isinstance(ingredient, dict) else str(ingredient)
            if text:
                formatted.append(f"{i}. {text}")
        
        return '\n'.join(formatted)

    def _generate_nutrition_insights(self, daily_nutrition: Dict, user_goals: Dict) -> List[str]:
        """Generate actionable nutrition insights"""
        insights = []
        
        if not daily_nutrition:
            return ["Nutrition analysis unavailable"]
        
        try:
            calories = daily_nutrition.get('calories', 0)
            target_calories = user_goals.get('daily_calories', 2000)
            
            # Calorie insights
            if calories < target_calories * 0.8:
                insights.append(f"⚠️ Low calories ({int(calories)}/{target_calories}). Consider adding healthy snacks.")
            elif calories > target_calories * 1.2:
                insights.append(f"⚠️ High calories ({int(calories)}/{target_calories}). Consider smaller portions.")
            else:
                insights.append(f"✅ Good calorie balance ({int(calories)}/{target_calories})")
            
            # Macro insights
            macros = daily_nutrition.get('macros', {})
            protein = macros.get('protein', 0)
            
            if protein < 50:
                insights.append("💪 Consider adding more protein sources")
            
            fiber = macros.get('fiber', 0)
            if fiber < 25:
                insights.append("🌾 Add more fiber with vegetables and whole grains")
            
            return insights[:3]  # Limit to 3 insights
            
        except Exception as e:
            logger.error(f"Error generating nutrition insights: {e}")
            return ["Nutrition insights unavailable"]

    async def _make_edamam_request(self, url: str, params: Dict) -> Optional[Dict]:
        """Make async request to Edamam API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Edamam API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error making Edamam request: {e}")
            return None

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get cached result from DynamoDB"""
        try:
            response = self.cache_table.get_item(Key={'cache_key': cache_key})
            
            if 'Item' in response:
                item = response['Item']
                # Check if not expired
                if datetime.now().timestamp() < item.get('expires_at', 0):
                    return item.get('data')
                    
        except Exception as e:
            logger.warning(f"Error getting from cache: {e}")
            
        return None

    async def _cache_result(self, cache_key: str, data: Dict, ttl_hours: int) -> None:
        """Cache result in DynamoDB with TTL"""
        try:
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            
            self.cache_table.put_item(
                Item={
                    'cache_key': cache_key,
                    'data': data,
                    'expires_at': int(expires_at.timestamp()),
                    'ttl': int(expires_at.timestamp())
                }
            )
            
        except Exception as e:
            logger.warning(f"Error caching result: {e}")

    async def _check_usage_limits(self, user_id: str, api_type: str) -> bool:
        """Check if user has exceeded API usage limits"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            usage_key = f"{user_id}#{api_type}#{today}"
            
            response = self.usage_table.get_item(Key={'usage_key': usage_key})
            
            if 'Item' in response:
                current_usage = response['Item'].get('count', 0)
                
                # Define limits per API type per day
                limits = {
                    'recipe_search': 50,
                    'nutrition_analysis': 20,
                    'food_database': 100
                }
                
                return current_usage < limits.get(api_type, 10)
            
            return True  # No usage recorded yet
            
        except Exception as e:
            logger.error(f"Error checking usage limits: {e}")
            return True  # Allow on error

    async def _log_api_usage(self, api_type: str, cost_estimate: float, user_id: str = None) -> None:
        """Log API usage for cost tracking"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Log overall usage
            overall_key = f"system#{api_type}#{today}"
            
            # Update overall usage
            self.usage_table.update_item(
                Key={'usage_key': overall_key},
                UpdateExpression='ADD #count :inc, #cost :cost',
                ExpressionAttributeNames={
                    '#count': 'count',
                    '#cost': 'total_cost'
                },
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':cost': cost_estimate
                }
            )
            
            # Log user-specific usage if user_id provided
            if user_id:
                user_key = f"{user_id}#{api_type}#{today}"
                self.usage_table.update_item(
                    Key={'usage_key': user_key},
                    UpdateExpression='ADD #count :inc',
                    ExpressionAttributeNames={'#count': 'count'},
                    ExpressionAttributeValues={':inc': 1}
                )
                
        except Exception as e:
            logger.warning(f"Error logging API usage: {e}")


class EdamamUsageTracker:
    """
    Track and manage Edamam API usage for cost optimization
    """
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.usage_table = self.dynamodb.Table(os.getenv('API_USAGE_TABLE_NAME', 'ai-nutritionist-api-usage-dev'))
        
    async def get_daily_usage_summary(self, date: str = None) -> Dict:
        """Get usage summary for a specific date"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
            
        try:
            response = self.usage_table.query(
                IndexName='DateIndex',  # Assumes GSI on date
                KeyConditionExpression='begins_with(usage_key, :prefix)',
                ExpressionAttributeValues={':prefix': f'system#'}
            )
            
            summary = {
                'date': date,
                'api_calls': {},
                'total_cost': 0.0,
                'top_users': []
            }
            
            for item in response.get('Items', []):
                if date in item['usage_key']:
                    api_type = item['usage_key'].split('#')[1]
                    summary['api_calls'][api_type] = item.get('count', 0)
                    summary['total_cost'] += item.get('total_cost', 0.0)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting usage summary: {e}")
            return {}

    async def check_budget_alerts(self, monthly_budget: float = 50.0) -> List[str]:
        """Check if approaching budget limits and return alerts"""
        alerts = []
        
        try:
            # Get current month usage
            current_month = datetime.now().strftime('%Y-%m')
            # This would need to aggregate monthly data
            
            # Simplified alert logic
            daily_summary = await self.get_daily_usage_summary()
            daily_cost = daily_summary.get('total_cost', 0)
            
            if daily_cost > monthly_budget / 30:  # Rough daily budget
                alerts.append(f"⚠️ Daily API cost (${daily_cost:.2f}) exceeds recommended budget")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking budget alerts: {e}")
            return []
