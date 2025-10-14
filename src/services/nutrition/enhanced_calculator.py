"""
Enhanced Edamam API Integration Service with comprehensive caching.
Updated to use the new caching system for improved performance and cost optimization.
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

# Import new caching system
from ...core.caching import (
    cached,
    invalidate_cache,
    api_response_cache,
    nutrition_cache,
    computed_results_cache
)

logger = logging.getLogger(__name__)


class EnhancedEdamamService:
    """Enhanced Edamam API integration with comprehensive caching system."""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.ssm = boto3.client('ssm')
        
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
        
        # Request limits per minute
        self.rate_limits = {
            'recipe_search': 10,
            'nutrition_analysis': 10,
            'food_database': 100
        }
        
    def _get_parameter(self, parameter_name: str) -> Optional[str]:
        """Get parameter from Systems Manager Parameter Store."""
        try:
            response = self.ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e:
            logger.error(f"Error getting parameter {parameter_name}: {e}")
            return None
    
    @cached(
        ttl=172800,  # 48 hours
        profile="api_response",
        tags=["edamam", "recipe", "search"],
        key_template="edamam:recipe_search:{query}:{meal_type}:{dietary_restrictions}"
    )
    async def enhanced_recipe_search(
        self, 
        meal_name: str, 
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Multi-criteria recipe search optimized for WhatsApp responses.
        Now uses comprehensive caching system.
        """
        if not self.recipe_api_key or not self.recipe_app_id:
            return {"error": "Recipe API credentials not configured"}
        
        try:
            # Extract user preferences
            dietary_restrictions = user_profile.get('dietary_restrictions', [])
            cuisine_preferences = user_profile.get('cuisine_preferences', ['american'])
            household_size = user_profile.get('household_size', 2)
            
            # Determine meal type from meal name
            meal_type = self._determine_meal_type(meal_name)
            
            # Build search parameters
            search_params = {
                'type': 'public',
                'q': meal_name,
                'app_id': self.recipe_app_id,
                'app_key': self.recipe_api_key,
                'mealType': meal_type,
                'dishType': meal_type,
                'time': '1-60',  # Max 60 minutes
                'yield': f"{household_size}-{household_size + 2}",
                'random': 'true'
            }
            
            # Add dietary restrictions
            if dietary_restrictions:
                search_params['health'] = dietary_restrictions
            
            # Add cuisine preferences
            if cuisine_preferences:
                search_params['cuisineType'] = cuisine_preferences[0]
            
            logger.info(f"Making Edamam recipe search for: {meal_name}")
            
            # Make API call (not cached here since decorator handles it)
            result = await self._make_edamam_request(self.recipe_search_url, search_params)
            
            if result and 'hits' in result:
                # Process and score recipes
                processed_recipes = self._process_recipe_results(result['hits'], user_profile)
                
                # Log usage for cost tracking
                await self._log_api_usage('recipe_search', 0.002, user_profile.get('user_id'))
                
                return {
                    'recipes': processed_recipes[:5],  # Top 5 recipes
                    'total_found': result.get('count', 0),
                    'search_params': search_params,
                    'cached_at': datetime.utcnow().isoformat()
                }
            
            return {"error": "No recipes found"}
            
        except Exception as e:
            logger.error(f"Error in enhanced recipe search: {str(e)}")
            return {"error": f"Recipe search failed: {str(e)}"}
    
    @cached(
        ttl=86400,  # 24 hours
        profile="computed_results",
        tags=["edamam", "nutrition", "analysis"],
        key_template="edamam:nutrition:{ingredients_hash}"
    )
    async def analyze_meal_nutrition(
        self, 
        ingredients_list: List[str], 
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze complete meal nutrition for optimization.
        Now uses comprehensive caching system.
        """
        if not self.nutrition_api_key or not self.nutrition_app_id:
            return {"error": "Nutrition API credentials not configured"}
            
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
            
            logger.info(f"Analyzing nutrition for {len(ingredients_list)} ingredients")
            
            # Make API call (caching handled by decorator)
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
                        
                        # Log usage
                        await self._log_api_usage('nutrition_analysis', 0.005, user_id)
                        
                        return processed_nutrition
                    else:
                        error_text = await response.text()
                        logger.error(f"Edamam nutrition API error: {response.status} - {error_text}")
                        return {'error': f'Nutrition analysis failed: {response.status}'}
            
        except Exception as e:
            logger.error(f"Error in nutrition analysis: {str(e)}")
            return {'error': f'Nutrition analysis failed: {str(e)}'}
    
    @cached(
        ttl=604800,  # 7 days
        profile="api_response",
        tags=["edamam", "food", "database"],
        key_template="edamam:food_db:{food_name}"
    )
    async def search_food_database(
        self, 
        food_name: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        Search Edamam food database for detailed food information.
        Uses long-term caching for static food data.
        """
        if not self.food_db_api_key or not self.food_db_app_id:
            return {"error": "Food database API credentials not configured"}
        
        try:
            params = {
                'ingr': food_name,
                'app_id': self.food_db_app_id,
                'app_key': self.food_db_api_key
            }
            
            logger.info(f"Searching food database for: {food_name}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.food_database_url,
                    params=params,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Process food data
                        processed_foods = self._process_food_database_results(result)
                        
                        # Log usage
                        await self._log_api_usage('food_database', 0.001, user_id)
                        
                        return {
                            'foods': processed_foods,
                            'search_term': food_name,
                            'cached_at': datetime.utcnow().isoformat()
                        }
                    else:
                        return {'error': f'Food database search failed: {response.status}'}
            
        except Exception as e:
            logger.error(f"Error in food database search: {str(e)}")
            return {'error': f'Food database search failed: {str(e)}'}
    
    @cached(
        ttl=3600,  # 1 hour
        profile="computed_results",
        tags=["edamam", "recipe", "details"],
        key_template="edamam:recipe_details:{recipe_uri}"
    )
    async def get_recipe_details(self, recipe_uri: str) -> Dict[str, Any]:
        """
        Get detailed recipe information by URI.
        Caches recipe details for quick access.
        """
        try:
            params = {
                'type': 'public',
                'uri': recipe_uri,
                'app_id': self.recipe_app_id,
                'app_key': self.recipe_api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.recipe_search_url,
                    params=params,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('hits'):
                            recipe = result['hits'][0]['recipe']
                            
                            return {
                                'recipe': self._format_recipe_for_display(recipe),
                                'cached_at': datetime.utcnow().isoformat()
                            }
                    
                    return {'error': 'Recipe not found'}
            
        except Exception as e:
            logger.error(f"Error getting recipe details: {str(e)}")
            return {'error': f'Failed to get recipe details: {str(e)}'}
    
    async def _make_edamam_request(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make request to Edamam API with error handling."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        logger.warning("Edamam API rate limit exceeded")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"Edamam API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error making Edamam request: {e}")
            return None
    
    def _determine_meal_type(self, meal_name: str) -> str:
        """Determine meal type from meal name."""
        meal_name_lower = meal_name.lower()
        
        breakfast_keywords = ['breakfast', 'cereal', 'oatmeal', 'pancake', 'waffle', 'toast', 'eggs']
        lunch_keywords = ['lunch', 'sandwich', 'salad', 'wrap', 'soup']
        dinner_keywords = ['dinner', 'pasta', 'chicken', 'beef', 'fish', 'steak', 'curry']
        snack_keywords = ['snack', 'smoothie', 'bar', 'nuts']
        
        if any(keyword in meal_name_lower for keyword in breakfast_keywords):
            return 'breakfast'
        elif any(keyword in meal_name_lower for keyword in lunch_keywords):
            return 'lunch'
        elif any(keyword in meal_name_lower for keyword in dinner_keywords):
            return 'dinner'
        elif any(keyword in meal_name_lower for keyword in snack_keywords):
            return 'snack'
        else:
            return 'lunch'  # Default
    
    def _process_recipe_results(self, hits: List[Dict], user_profile: Dict) -> List[Dict]:
        """Process and score recipe results based on user preferences."""
        processed_recipes = []
        
        for hit in hits:
            recipe = hit.get('recipe', {})
            
            # Calculate relevance score
            score = self._calculate_recipe_score(recipe, user_profile)
            
            # Format recipe for display
            formatted_recipe = {
                'uri': recipe.get('uri', ''),
                'label': recipe.get('label', ''),
                'image': recipe.get('image', ''),
                'source': recipe.get('source', ''),
                'url': recipe.get('url', ''),
                'yield': recipe.get('yield', 0),
                'dietLabels': recipe.get('dietLabels', []),
                'healthLabels': recipe.get('healthLabels', []),
                'cautions': recipe.get('cautions', []),
                'ingredientLines': recipe.get('ingredientLines', [])[:10],  # Limit ingredients
                'calories': round(recipe.get('calories', 0)),
                'totalTime': recipe.get('totalTime', 0),
                'cuisineType': recipe.get('cuisineType', []),
                'mealType': recipe.get('mealType', []),
                'dishType': recipe.get('dishType', []),
                'score': score
            }
            
            # Add nutrition summary
            if 'totalNutrients' in recipe:
                nutrients = recipe['totalNutrients']
                formatted_recipe['nutrition'] = {
                    'protein': round(nutrients.get('PROCNT', {}).get('quantity', 0)),
                    'fat': round(nutrients.get('FAT', {}).get('quantity', 0)),
                    'carbs': round(nutrients.get('CHOCDF', {}).get('quantity', 0)),
                    'fiber': round(nutrients.get('FIBTG', {}).get('quantity', 0)),
                    'sugar': round(nutrients.get('SUGAR', {}).get('quantity', 0)),
                    'sodium': round(nutrients.get('NA', {}).get('quantity', 0))
                }
            
            processed_recipes.append(formatted_recipe)
        
        # Sort by score (highest first)
        processed_recipes.sort(key=lambda x: x['score'], reverse=True)
        
        return processed_recipes
    
    def _calculate_recipe_score(self, recipe: Dict, user_profile: Dict) -> float:
        """Calculate relevance score for a recipe based on user preferences."""
        score = 1.0
        
        # Dietary restrictions match
        user_restrictions = set(user_profile.get('dietary_restrictions', []))
        recipe_health_labels = set(recipe.get('healthLabels', []))
        
        if user_restrictions:
            matches = len(user_restrictions.intersection(recipe_health_labels))
            score += matches * 0.3
        
        # Cuisine preference match
        user_cuisines = set(user_profile.get('cuisine_preferences', []))
        recipe_cuisines = set(recipe.get('cuisineType', []))
        
        if user_cuisines and recipe_cuisines:
            if user_cuisines.intersection(recipe_cuisines):
                score += 0.2
        
        # Cooking time preference
        total_time = recipe.get('totalTime', 0)
        if total_time > 0:
            if total_time <= 30:  # Quick meals preferred
                score += 0.2
            elif total_time > 60:  # Penalize very long recipes
                score -= 0.1
        
        # Serving size match
        recipe_yield = recipe.get('yield', 0)
        household_size = user_profile.get('household_size', 2)
        
        if recipe_yield > 0:
            size_diff = abs(recipe_yield - household_size)
            if size_diff <= 1:
                score += 0.1
        
        return round(score, 2)
    
    def _process_nutrition_data(self, nutrition_result: Dict) -> Dict[str, Any]:
        """Process nutrition analysis results."""
        try:
            total_nutrients = nutrition_result.get('totalNutrients', {})
            total_daily = nutrition_result.get('totalDaily', {})
            
            processed = {
                'calories': round(nutrition_result.get('calories', 0)),
                'servings': nutrition_result.get('yield', 1),
                'weight': round(nutrition_result.get('totalWeight', 0)),
                'nutrients': {},
                'daily_values': {},
                'diet_labels': nutrition_result.get('dietLabels', []),
                'health_labels': nutrition_result.get('healthLabels', []),
                'cautions': nutrition_result.get('cautions', []),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
            # Key nutrients
            key_nutrients = {
                'PROCNT': 'protein',
                'FAT': 'fat',
                'CHOCDF': 'carbs',
                'FIBTG': 'fiber',
                'SUGAR': 'sugar',
                'NA': 'sodium',
                'CA': 'calcium',
                'FE': 'iron',
                'MG': 'magnesium',
                'P': 'phosphorus',
                'K': 'potassium',
                'ZN': 'zinc',
                'VITA_RAE': 'vitamin_a',
                'VITC': 'vitamin_c',
                'VITD': 'vitamin_d',
                'VITB12': 'vitamin_b12'
            }
            
            for edamam_code, nutrient_name in key_nutrients.items():
                if edamam_code in total_nutrients:
                    nutrient_data = total_nutrients[edamam_code]
                    processed['nutrients'][nutrient_name] = {
                        'quantity': round(nutrient_data.get('quantity', 0), 2),
                        'unit': nutrient_data.get('unit', '')
                    }
                
                if edamam_code in total_daily:
                    daily_data = total_daily[edamam_code]
                    processed['daily_values'][nutrient_name] = round(daily_data.get('quantity', 0), 1)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing nutrition data: {e}")
            return {'error': 'Failed to process nutrition data'}
    
    def _process_food_database_results(self, result: Dict) -> List[Dict]:
        """Process food database search results."""
        foods = []
        
        for hint in result.get('hints', []):
            food = hint.get('food', {})
            
            processed_food = {
                'food_id': food.get('foodId', ''),
                'label': food.get('label', ''),
                'brand': food.get('brand', ''),
                'category': food.get('category', ''),
                'category_label': food.get('categoryLabel', ''),
                'nutrients': {}
            }
            
            # Process nutrients
            nutrients = food.get('nutrients', {})
            for nutrient_code, value in nutrients.items():
                processed_food['nutrients'][nutrient_code] = value
            
            foods.append(processed_food)
        
        return foods[:10]  # Limit to top 10 results
    
    def _format_recipe_for_display(self, recipe: Dict) -> Dict[str, Any]:
        """Format recipe for user-friendly display."""
        return {
            'name': recipe.get('label', ''),
            'image': recipe.get('image', ''),
            'source': recipe.get('source', ''),
            'url': recipe.get('url', ''),
            'servings': recipe.get('yield', 0),
            'total_time': recipe.get('totalTime', 0),
            'ingredients': recipe.get('ingredientLines', []),
            'calories': round(recipe.get('calories', 0)),
            'cuisine_type': recipe.get('cuisineType', []),
            'meal_type': recipe.get('mealType', []),
            'diet_labels': recipe.get('dietLabels', []),
            'health_labels': recipe.get('healthLabels', []),
            'cautions': recipe.get('cautions', [])
        }
    
    async def _check_usage_limits(self, user_id: str, api_type: str) -> bool:
        """Check if user has exceeded API usage limits."""
        try:
            today = datetime.utcnow().date().isoformat()
            
            response = self.usage_table.get_item(
                Key={
                    'user_id': user_id,
                    'date': today
                }
            )
            
            if 'Item' in response:
                usage = response['Item'].get(api_type, 0)
                limit = self.rate_limits.get(api_type, 10)
                
                return usage < limit
            
            return True  # No usage recorded yet
            
        except Exception as e:
            logger.error(f"Error checking usage limits: {e}")
            return True  # Allow on error
    
    async def _log_api_usage(self, api_type: str, cost_estimate: float, user_id: str = None) -> None:
        """Log API usage for cost tracking."""
        try:
            today = datetime.utcnow().date().isoformat()
            
            # Update user usage if user_id provided
            if user_id:
                self.usage_table.update_item(
                    Key={
                        'user_id': user_id,
                        'date': today
                    },
                    UpdateExpression=f'ADD {api_type} :inc, total_cost :cost',
                    ExpressionAttributeValues={
                        ':inc': 1,
                        ':cost': cost_estimate
                    }
                )
            
            # Log overall usage
            self.usage_table.update_item(
                Key={
                    'user_id': 'SYSTEM',
                    'date': today
                },
                UpdateExpression=f'ADD {api_type} :inc, total_cost :cost',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':cost': cost_estimate
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging API usage: {e}")
    
    @invalidate_cache(tags=["edamam"])
    async def clear_cache(self, cache_type: str = "all") -> Dict[str, int]:
        """
        Clear cached data by type.
        
        Args:
            cache_type: Type of cache to clear (all, recipe, nutrition, food)
            
        Returns:
            Dict with count of cleared entries by type
        """
        results = {}
        
        if cache_type in ["all", "recipe"]:
            recipe_count = await api_response_cache.cache_manager.invalidate_by_tag("recipe")
            results["recipe"] = recipe_count
        
        if cache_type in ["all", "nutrition"]:
            nutrition_count = await nutrition_cache.cache_manager.invalidate_by_tag("nutrition")
            results["nutrition"] = nutrition_count
        
        if cache_type in ["all", "food"]:
            food_count = await api_response_cache.cache_manager.invalidate_by_tag("food")
            results["food"] = food_count
        
        logger.info(f"Cache cleared: {results}")
        return results
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics."""
        try:
            # Get cache manager metrics
            cache_manager = api_response_cache.cache_manager
            metrics = cache_manager.get_metrics()
            status = cache_manager.get_status()
            
            return {
                "hit_ratio": metrics.hit_ratio,
                "total_operations": metrics.total_operations,
                "hits": metrics.hits,
                "misses": metrics.misses,
                "errors": metrics.errors,
                "backends": status["backends"],
                "cache_health": "healthy" if metrics.errors < metrics.total_operations * 0.1 else "degraded"
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": "Failed to get cache statistics"}


# Create global instance for backward compatibility
edamam_service = EnhancedEdamamService()
