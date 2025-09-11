"""
Consolidated AI & Nutrition Service
Combines AI-powered meal planning, nutrition analysis, user profiling, and tracking
Provides unified interface for all AI and nutrition-related functionality
"""

import json
import logging
import os
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from decimal import Decimal
import random

import boto3
import requests
import aiohttp
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class DayNutrition:
    """Daily nutrition and wellness tracking"""
    date: str
    kcal: float = 0
    protein: float = 0
    carbs: float = 0
    fat: float = 0
    fiber: float = 0
    sodium: float = 0
    sugar_added: float = 0
    water_cups: float = 0
    steps: Optional[int] = None
    mood: Optional[str] = None  # 😞 😐 🙂 😄
    energy: Optional[str] = None  # 💤 ⚡
    digestion: Optional[str] = None  # 😣 🙂 👍
    sleep_quality: Optional[str] = None  # 😴😴😴
    
    # Meal tracking
    meals_ate: List[str] = None
    meals_skipped: List[str] = None
    meals_modified: List[str] = None
    snacks: List[str] = None
    
    def __post_init__(self):
        if self.meals_ate is None:
            self.meals_ate = []
        if self.meals_skipped is None:
            self.meals_skipped = []
        if self.meals_modified is None:
            self.meals_modified = []
        if self.snacks is None:
            self.snacks = []


@dataclass
class UserProfile:
    """Comprehensive user profile for nutrition and meal planning"""
    user_id: str
    dietary_restrictions: List[str] = None
    allergies: List[str] = None
    household_size: int = 2
    weekly_budget: float = 75.0
    fitness_goals: str = 'maintenance'
    daily_calories: int = 2000
    health_conditions: List[str] = None
    cooking_skill: str = 'intermediate'
    meal_preferences: Dict[str, Any] = None
    nutrition_goals: Dict[str, float] = None
    
    def __post_init__(self):
        if self.dietary_restrictions is None:
            self.dietary_restrictions = []
        if self.allergies is None:
            self.allergies = []
        if self.health_conditions is None:
            self.health_conditions = []
        if self.meal_preferences is None:
            self.meal_preferences = {}
        if self.nutrition_goals is None:
            self.nutrition_goals = {
                'protein': 120,
                'fiber': 30,
                'sodium': 2000
            }


class ConsolidatedAINutritionService:
    """
    Unified service for all AI and nutrition functionality including:
    - AI-powered meal planning with AWS Bedrock
    - Nutrition analysis with Edamam integration
    - User profiling and adaptive learning
    - Nutrition tracking and wellness monitoring
    - Recipe enrichment and substitution suggestions
    """
    
    def __init__(self):
        # AWS Services
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.dynamodb = boto3.resource('dynamodb')
        self.model_id = "amazon.titan-text-express-v1"
        
        # DynamoDB Tables
        self.cache_table = self.dynamodb.Table(
            os.getenv('PROMPT_CACHE_TABLE', 'ai-nutritionist-prompt-cache-dev')
        )
        self.user_table = self.dynamodb.Table(
            os.getenv('USER_TABLE', 'ai-nutritionist-users-dev')
        )
        self.nutrition_table = self.dynamodb.Table(
            os.getenv('NUTRITION_TABLE', 'ai-nutritionist-nutrition-dev')
        )
        
        # Edamam API Configuration
        self.edamam_app_id = self._get_parameter('/ai-nutritionist/edamam/app-id')
        self.edamam_app_key = self._get_parameter('/ai-nutritionist/edamam/app-key')
        self.recipe_search_url = "https://api.edamam.com/api/recipes/v2"
        self.nutrition_analysis_url = "https://api.edamam.com/api/nutrition-details"
        
        # Nutrition Targets
        self.default_nutrition_targets = {
            'kcal': 2000,
            'protein': 120,
            'fiber': 30,
            'sodium': 2000,
            'water_cups': 8
        }
        
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
                'ratio': '75% plants, 25% animal products',
                'benefits': ['environmental sustainability', 'increased fiber', 'diverse nutrients']
            }
        }

    def _get_parameter(self, parameter_name: str) -> Optional[str]:
        """Get parameter from Systems Manager Parameter Store"""
        try:
            ssm = boto3.client('ssm')
            response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Could not get parameter {parameter_name}: {e}")
            return None

    # =============================================================================
    # AI MEAL PLANNING METHODS
    # =============================================================================

    def generate_meal_plan(self, user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate AI-powered weekly meal plan with enhanced nutrition analysis
        """
        try:
            # Check cache first for cost optimization
            cache_key = self._generate_cache_key(user_profile)
            cached_plan = self._get_cached_response(cache_key)
            
            if cached_plan:
                logger.info(f"Returning cached meal plan for user {user_profile.get('user_id', 'unknown')}")
                return cached_plan
            
            # Build enhanced prompt with user profiling
            prompt = self._build_meal_plan_prompt(user_profile)
            
            logger.info(f"Generating new meal plan for user {user_profile.get('user_id', 'unknown')}")
            
            response = self._invoke_model_with_cache(prompt, cache_key, max_tokens=3000)
            if response:
                meal_plan = self._parse_meal_plan_response(response)
                
                if meal_plan:
                    # Enrich with enhanced recipe data and nutrition analysis
                    meal_plan = asyncio.run(self._enrich_with_enhanced_recipes(meal_plan, user_profile))
                
                return meal_plan
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            return None

    def _build_meal_plan_prompt(self, user_profile: Dict[str, Any]) -> str:
        """Build optimized prompt for meal plan generation with adaptive strategies"""
        
        # Extract user preferences and apply adaptive strategies
        dietary_restrictions = user_profile.get('dietary_restrictions', [])
        household_size = user_profile.get('household_size', 2)
        budget = user_profile.get('weekly_budget', 75)
        fitness_goals = user_profile.get('fitness_goals', 'maintenance')
        allergies = user_profile.get('allergies', [])
        cooking_skill = user_profile.get('cooking_skill', 'intermediate')
        
        # Apply intelligent nutrition strategy if user shows readiness
        suggested_strategy = self._suggest_nutrition_strategy(user_profile)
        
        prompt = f"""You are a professional nutritionist creating a personalized weekly meal plan.

User Profile:
- Household size: {household_size} people
- Weekly food budget: ${budget}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Allergies: {', '.join(allergies) if allergies else 'None'}
- Fitness goals: {fitness_goals}
- Cooking skill level: {cooking_skill}

{self._get_strategy_guidance(suggested_strategy) if suggested_strategy else ''}

Requirements:
1. Create a 7-day meal plan (Monday-Sunday)
2. Include breakfast, lunch, dinner, and one snack per day
3. Each meal should be realistic, budget-friendly, and nutritionally balanced
4. Consider prep time and cooking skill level
5. Aim for variety across the week
6. Include estimated calories per meal

Format as JSON:
{{
  "days": {{
    "monday": {{
      "breakfast": {{"name": "Meal name", "prep_time": "15 min", "calories": 350}},
      "lunch": {{"name": "Meal name", "prep_time": "20 min", "calories": 450}},
      "dinner": {{"name": "Meal name", "prep_time": "30 min", "calories": 550}},
      "snack": {{"name": "Snack name", "prep_time": "5 min", "calories": 150}}
    }},
    ... continue for all 7 days
  }},
  "weekly_budget": {budget},
  "total_estimated_cost": "calculated estimate",
  "nutrition_highlights": ["key nutritional benefits"],
  "cooking_tips": ["helpful preparation tips"]
}}

Focus on whole foods, seasonal ingredients, and meals that can be prepped efficiently."""

        return prompt

    def _suggest_nutrition_strategy(self, user_profile: Dict[str, Any]) -> Optional[str]:
        """Intelligently suggest nutrition strategies based on user readiness"""
        
        # Analyze user readiness for different strategies
        fitness_goal = user_profile.get('fitness_goals', '').lower()
        health_conditions = user_profile.get('health_conditions', [])
        current_habits = user_profile.get('meal_preferences', {})
        
        # Digestive issues or gut health focus (highest priority)
        if any(condition in ['ibs', 'digestive', 'gut'] for condition in health_conditions):
            return 'gut_health_focus'
        
        # Weight loss + no major restrictions -> intermittent fasting
        if 'weight' in fitness_goal and 'loss' in fitness_goal:
            if not any(condition in ['diabetes', 'eating_disorder'] for condition in health_conditions):
                return 'intermittent_fasting'
        
        # Environmental consciousness indicators
        if 'plant' in str(current_habits).lower() or 'vegetarian' in user_profile.get('dietary_restrictions', []):
            return 'plant_forward'
        
        # Default for most users - gentle time restriction
        return 'time_restricted_eating'

    def _get_strategy_guidance(self, strategy: str) -> str:
        """Get meal planning guidance for a specific nutrition strategy"""
        if strategy not in self.nutrition_strategies:
            return ""
        
        strategy_data = self.nutrition_strategies[strategy]
        
        if strategy == 'intermittent_fasting':
            return """
Special Consideration - Intermittent Fasting Approach:
- Focus on lunch and dinner only (skip breakfast)
- Ensure meals are nutrient-dense and satisfying
- Include healthy fats and protein for satiety
- First meal around noon, last meal by 8 PM
"""
        elif strategy == 'gut_health_focus':
            return f"""
Special Focus - Gut Health Optimization:
- Include fermented foods: {', '.join(strategy_data['key_foods'][:3])}
- Emphasize fiber-rich vegetables and prebiotic foods
- Consider anti-inflammatory ingredients
- Variety of plant foods for microbiome diversity
"""
        elif strategy == 'plant_forward':
            return """
Plant-Forward Approach:
- 75% of plate should be plant-based foods
- Include diverse vegetables, legumes, whole grains
- Quality animal proteins in smaller portions
- Focus on colorful, seasonal produce
"""
        else:  # time_restricted_eating
            return """
Circadian-Aligned Eating:
- Plan meals within a 12-hour window (7 AM - 7 PM)
- Larger breakfast and lunch, lighter dinner
- Focus on foods that support natural energy rhythms
"""

    async def _enrich_with_enhanced_recipes(self, meal_plan: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced meal plan enrichment with Edamam optimization and nutrition analysis"""
        try:
            enriched_plan = meal_plan.copy()
            
            # Process each day's meals
            for day_key, day_data in meal_plan.get('days', {}).items():
                daily_ingredients = []
                
                for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
                    meal = day_data.get(meal_type)
                    if meal and isinstance(meal, dict):
                        meal_name = meal.get('name', '')
                        
                        # Enhanced recipe search
                        recipe_results = await self.enhanced_recipe_search(meal_name, user_profile)
                        
                        if recipe_results and recipe_results.get('recipes'):
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
                            meal['whatsapp_format'] = self.format_recipe_for_whatsapp(best_recipe)
                            
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
                                        subs = await self.suggest_substitutions(
                                            ingredient_text, user_profile.get('dietary_restrictions', [])
                                        )
                                        if subs:
                                            substitutions[ingredient_text] = subs
                                
                                if substitutions:
                                    meal['substitution_suggestions'] = substitutions
                
                # Analyze daily nutrition if we have ingredients
                if daily_ingredients:
                    daily_nutrition = await self.analyze_meal_nutrition(
                        daily_ingredients, user_profile.get('user_id')
                    )
                    
                    if daily_nutrition and 'error' not in daily_nutrition:
                        # Add nutrition insights
                        user_goals = {
                            'daily_calories': user_profile.get('daily_calories', 2000),
                            'fitness_goal': user_profile.get('fitness_goals', 'maintenance')
                        }
                        
                        insights = self._generate_nutrition_insights(daily_nutrition, user_goals)
                        
                        enriched_plan['days'][day_key]['nutrition_analysis'] = daily_nutrition
                        enriched_plan['days'][day_key]['nutrition_insights'] = insights
                        
                        # Add nutrition summary for WhatsApp
                        nutrition_summary = self._format_nutrition_summary(daily_nutrition)
                        enriched_plan['days'][day_key]['nutrition_summary'] = nutrition_summary
            
            return enriched_plan
            
        except Exception as e:
            logger.error(f"Error in enhanced recipe enrichment: {e}")
            return meal_plan

    # =============================================================================
    # NUTRITION ANALYSIS METHODS  
    # =============================================================================

    async def analyze_meal_nutrition(self, ingredients_list: List[str], user_id: str = None) -> Dict:
        """Comprehensive meal nutrition analysis using Edamam API"""
        try:
            # Check cache first
            cache_key = f"nutrition_{hashlib.md5(''.join(sorted(ingredients_list)).encode()).hexdigest()}"
            cached_result = await self._get_from_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Prepare ingredients data for Edamam
            ingredients_data = {
                'ingredients': [{'text': ingredient} for ingredient in ingredients_list]
            }
            
            headers = {'Content-Type': 'application/json'}
            params = {
                'app_id': self.edamam_app_id,
                'app_key': self.edamam_app_key
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
                        processed_nutrition = self._process_nutrition_data(result)
                        
                        # Cache successful results
                        await self._cache_result(cache_key, processed_nutrition, ttl_hours=24)
                        
                        return processed_nutrition
                    else:
                        error_msg = f"Edamam API error: {response.status}"
                        logger.error(error_msg)
                        return {'error': error_msg}
                        
        except Exception as e:
            logger.error(f"Error in nutrition analysis: {e}")
            return {'error': str(e)}

    def _process_nutrition_data(self, raw_data: Dict) -> Dict:
        """Process and standardize nutrition data from Edamam"""
        try:
            total_nutrients = raw_data.get('totalNutrients', {})
            total_daily = raw_data.get('totalDaily', {})
            
            return {
                'calories': round(raw_data.get('calories', 0)),
                'total_weight': round(raw_data.get('totalWeight', 0)),
                'macros': {
                    'protein': round(total_nutrients.get('PROCNT', {}).get('quantity', 0), 1),
                    'carbs': round(total_nutrients.get('CHOCDF', {}).get('quantity', 0), 1),
                    'fat': round(total_nutrients.get('FAT', {}).get('quantity', 0), 1),
                    'fiber': round(total_nutrients.get('FIBTG', {}).get('quantity', 0), 1),
                },
                'vitamins': {
                    'vitamin_c': round(total_nutrients.get('VITC', {}).get('quantity', 0), 1),
                    'vitamin_d': round(total_nutrients.get('VITD', {}).get('quantity', 0), 1),
                    'folate': round(total_nutrients.get('FOLDFE', {}).get('quantity', 0), 1),
                },
                'minerals': {
                    'calcium': round(total_nutrients.get('CA', {}).get('quantity', 0), 1),
                    'iron': round(total_nutrients.get('FE', {}).get('quantity', 0), 1),
                    'sodium': round(total_nutrients.get('NA', {}).get('quantity', 0), 1),
                    'potassium': round(total_nutrients.get('K', {}).get('quantity', 0), 1),
                },
                'daily_values': {
                    'protein_pct': round(total_daily.get('PROCNT', {}).get('quantity', 0), 1),
                    'vitamin_c_pct': round(total_daily.get('VITC', {}).get('quantity', 0), 1),
                    'calcium_pct': round(total_daily.get('CA', {}).get('quantity', 0), 1),
                    'iron_pct': round(total_daily.get('FE', {}).get('quantity', 0), 1),
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing nutrition data: {e}")
            return {}

    async def get_enhanced_nutrition_analysis(self, ingredients: List[str], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive nutrition analysis with AI insights"""
        try:
            # Get detailed nutrition analysis
            nutrition_data = await self.analyze_meal_nutrition(ingredients, user_profile.get('user_id'))
            
            if 'error' in nutrition_data:
                return {
                    'success': False,
                    'message': nutrition_data['error'],
                    'fallback_advice': await self._get_ai_nutrition_fallback(ingredients, user_profile)
                }
            
            # Generate AI-powered insights
            user_goals = {
                'daily_calories': user_profile.get('daily_calories', 2000),
                'fitness_goal': user_profile.get('fitness_goals', 'maintenance'),
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

    # =============================================================================
    # RECIPE SEARCH AND ENHANCEMENT
    # =============================================================================

    async def enhanced_recipe_search(self, query: str, user_profile: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
        """Enhanced recipe search with user preference optimization"""
        try:
            # Build search parameters based on user profile
            params = {
                'type': 'public',
                'q': query,
                'app_id': self.edamam_app_id,
                'app_key': self.edamam_app_key,
                'from': 0,
                'to': limit,
                'random': 'true'  # Add variety
            }
            
            # Add diet and health labels based on user profile
            diet_labels = self._extract_diet_labels(user_profile)
            health_labels = self._extract_health_labels(user_profile)
            
            if diet_labels:
                params['diet'] = diet_labels
            if health_labels:
                params['health'] = health_labels
            
            # Add calorie range if specified
            if user_profile.get('daily_calories'):
                calorie_per_meal = user_profile['daily_calories'] // 4  # Rough estimate per meal
                params['calories'] = f"{calorie_per_meal - 150}-{calorie_per_meal + 150}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.recipe_search_url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Process and score recipes
                        recipes = []
                        for hit in data.get('hits', [])[:limit]:
                            recipe = hit['recipe']
                            
                            # Calculate user preference score
                            score = self._calculate_recipe_score(recipe, user_profile)
                            recipe['user_score'] = score
                            recipe['difficulty'] = self._calculate_recipe_difficulty(recipe, user_profile.get('cooking_skill', 'intermediate'))
                            
                            recipes.append(recipe)
                        
                        # Sort by user score
                        recipes.sort(key=lambda x: x.get('user_score', 0), reverse=True)
                        
                        return {
                            'recipes': recipes,
                            'total_results': len(recipes),
                            'search_query': query
                        }
                    else:
                        logger.error(f"Recipe search error: {response.status}")
                        return {'error': f"Recipe search failed: {response.status}"}
                        
        except Exception as e:
            logger.error(f"Error in recipe search: {e}")
            return {'error': str(e)}

    def _extract_diet_labels(self, user_profile: Dict) -> List[str]:
        """Extract Edamam diet labels from user profile"""
        diet_labels = []
        restrictions = user_profile.get('dietary_restrictions', [])
        
        mapping = {
            'vegetarian': 'vegetarian',
            'vegan': 'vegan',
            'paleo': 'paleo',
            'keto': 'keto-friendly',
            'low-carb': 'low-carb'
        }
        
        for restriction in restrictions:
            if restriction.lower() in mapping:
                diet_labels.append(mapping[restriction.lower()])
                
        return diet_labels

    def _extract_health_labels(self, user_profile: Dict) -> List[str]:
        """Extract Edamam health labels from user profile"""
        health_labels = []
        
        # From allergies
        allergies = user_profile.get('allergies', [])
        allergy_mapping = {
            'gluten': 'gluten-free',
            'dairy': 'dairy-free',
            'nuts': 'tree-nut-free',
            'soy': 'soy-free',
            'eggs': 'egg-free'
        }
        
        for allergy in allergies:
            if allergy.lower() in allergy_mapping:
                health_labels.append(allergy_mapping[allergy.lower()])
        
        # From health conditions
        conditions = user_profile.get('health_conditions', [])
        if 'diabetes' in conditions:
            health_labels.append('low-sugar')
        if 'hypertension' in conditions:
            health_labels.append('low-sodium')
            
        return health_labels

    # =============================================================================
    # NUTRITION TRACKING METHODS
    # =============================================================================

    def track_daily_nutrition(self, user_id: str, nutrition_data: DayNutrition) -> Dict[str, Any]:
        """Track daily nutrition and wellness data"""
        try:
            # Store in DynamoDB
            item = {
                'user_id': user_id,
                'date': nutrition_data.date,
                'nutrition_data': json.dumps(asdict(nutrition_data), default=str),
                'timestamp': datetime.utcnow().isoformat(),
                'ttl': int((datetime.utcnow() + timedelta(days=365)).timestamp())
            }
            
            self.nutrition_table.put_item(Item=item)
            
            # Analyze trends and provide insights
            insights = self._analyze_nutrition_trends(user_id, nutrition_data)
            
            return {
                'success': True,
                'insights': insights,
                'daily_summary': self._format_daily_summary(nutrition_data),
                'recommendations': self._get_daily_recommendations(nutrition_data)
            }
            
        except Exception as e:
            logger.error(f"Error tracking nutrition: {e}")
            return {'success': False, 'error': str(e)}

    def get_nutrition_history(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get nutrition history for trend analysis"""
        try:
            from boto3.dynamodb.conditions import Key
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            response = self.nutrition_table.query(
                KeyConditionExpression=Key('user_id').eq(user_id),
                FilterExpression=Key('date').between(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                ),
                ScanIndexForward=False,
                Limit=days
            )
            
            history = []
            for item in response['Items']:
                nutrition_data = json.loads(item['nutrition_data'])
                history.append(DayNutrition(**nutrition_data))
            
            # Calculate trends and insights
            trends = self._calculate_nutrition_trends(history)
            
            return {
                'success': True,
                'history': [asdict(day) for day in history],
                'trends': trends,
                'weekly_summary': self._format_weekly_summary(history)
            }
            
        except Exception as e:
            logger.error(f"Error getting nutrition history: {e}")
            return {'success': False, 'error': str(e)}

    # =============================================================================
    # AI INSIGHT GENERATION
    # =============================================================================

    async def _generate_ai_nutrition_insights(self, nutrition_data: Dict, user_goals: Dict) -> List[str]:
        """Generate AI-powered nutrition insights"""
        try:
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
            else:
                return ["Unable to generate personalized insights at this time."]
                
        except Exception as e:
            logger.error(f"Error generating AI nutrition insights: {e}")
            return ["Focus on balanced nutrition with adequate protein and fiber."]

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def _invoke_model(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Invoke AWS Bedrock model"""
        try:
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": max_tokens,
                    "temperature": 0.7,
                    "topP": 0.9,
                    "stopSequences": []
                }
            })
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            return response_body.get('results', [{}])[0].get('outputText', '').strip()
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock model: {e}")
            return None

    def _invoke_model_with_cache(self, prompt: str, cache_key: str, max_tokens: int = 1000) -> Optional[str]:
        """Invoke model with caching for cost optimization"""
        try:
            # Check cache first
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                return cached_response.get('response')
            
            # Generate new response
            response = self._invoke_model(prompt, max_tokens)
            
            if response:
                # Cache the response
                self._cache_response(cache_key, {'response': response}, ttl_hours=168)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in cached model invocation: {e}")
            return None

    def _generate_cache_key(self, user_profile: Dict[str, Any]) -> str:
        """Generate cache key for meal plans based on user preferences"""
        # Create deterministic key from user preferences
        key_data = {
            'dietary_restrictions': sorted(user_profile.get('dietary_restrictions', [])),
            'household_size': user_profile.get('household_size', 2),
            'weekly_budget': user_profile.get('weekly_budget', 75),
            'fitness_goals': user_profile.get('fitness_goals', 'maintenance'),
            'allergies': sorted(user_profile.get('allergies', []))
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response from DynamoDB"""
        try:
            response = self.cache_table.get_item(Key={'cache_key': cache_key})
            
            if 'Item' in response:
                item = response['Item']
                
                # Check if not expired
                if 'expires_at' in item:
                    expires_at = datetime.fromisoformat(item['expires_at'])
                    if expires_at > datetime.utcnow():
                        return json.loads(item['data'])
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting cached response: {e}")
            return None

    def _cache_response(self, cache_key: str, data: Dict[str, Any], ttl_hours: int = 168) -> None:
        """Cache response in DynamoDB with TTL"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            item = {
                'cache_key': cache_key,
                'data': json.dumps(data, default=str),
                'expires_at': expires_at.isoformat(),
                'ttl': int(expires_at.timestamp())
            }
            
            self.cache_table.put_item(Item=item)
            
        except Exception as e:
            logger.warning(f"Error caching response: {e}")

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get item from cache (async version)"""
        return self._get_cached_response(cache_key)

    async def _cache_result(self, cache_key: str, data: Dict, ttl_hours: int = 24) -> None:
        """Cache result (async version)"""
        self._cache_response(cache_key, data, ttl_hours)

    def _parse_meal_plan_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse AI response and extract meal plan data"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                meal_plan = json.loads(json_str)
                
                # Validate required fields
                if 'days' in meal_plan and isinstance(meal_plan['days'], dict):
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
        """Fallback parser for text-based meal plan responses"""
        # Implementation for parsing text-based responses
        # This is a simplified version - in practice would be more sophisticated
        return {
            "days": {
                "monday": {
                    "breakfast": {"name": "Parsed breakfast", "prep_time": "15 min", "calories": 350},
                    "lunch": {"name": "Parsed lunch", "prep_time": "20 min", "calories": 450},
                    "dinner": {"name": "Parsed dinner", "prep_time": "30 min", "calories": 550}
                }
            },
            "weekly_budget": 75,
            "parsing_note": "Fallback text parsing used"
        }

    def format_recipe_for_whatsapp(self, recipe: Dict) -> str:
        """Format recipe data for WhatsApp display"""
        try:
            name = recipe.get('label', 'Recipe')
            prep_time = recipe.get('totalTime', 30)
            servings = recipe.get('yield', 4)
            calories = int(recipe.get('calories', 0) / servings) if servings else 0
            
            return f"""🍽️ *{name}*
⏱️ {prep_time} minutes | 👥 {servings} servings
🔥 {calories} calories per serving

📱 Get recipe: {recipe.get('url', 'Recipe link not available')}"""
            
        except Exception as e:
            logger.error(f"Error formatting recipe: {e}")
            return "Recipe formatting error"

    def _format_nutrition_summary(self, nutrition_data: Dict) -> str:
        """Format nutrition data for WhatsApp display"""
        try:
            macros = nutrition_data.get('macros', {})
            return f"""📊 *Nutrition Summary*
🔥 {nutrition_data.get('calories', 0)} calories
🥩 {macros.get('protein', 0)}g protein
🍞 {macros.get('carbs', 0)}g carbs  
🥑 {macros.get('fat', 0)}g fat
🌾 {macros.get('fiber', 0)}g fiber"""
            
        except Exception as e:
            logger.error(f"Error formatting nutrition summary: {e}")
            return "Nutrition data unavailable"

    async def suggest_substitutions(self, ingredient: str, dietary_restrictions: List[str]) -> List[str]:
        """Suggest ingredient substitutions based on dietary restrictions"""
        substitutions = []
        
        # Common substitution mappings
        substitution_map = {
            'milk': {
                'dairy-free': ['almond milk', 'oat milk', 'coconut milk'],
                'vegan': ['soy milk', 'oat milk', 'cashew milk']
            },
            'butter': {
                'dairy-free': ['coconut oil', 'olive oil', 'vegan butter'],
                'vegan': ['coconut oil', 'avocado oil', 'vegan butter']
            },
            'eggs': {
                'vegan': ['flax eggs', 'chia eggs', 'applesauce'],
                'egg-free': ['aquafaba', 'banana', 'commercial egg replacer']
            }
        }
        
        ingredient_lower = ingredient.lower()
        for restriction in dietary_restrictions:
            restriction_key = restriction.lower().replace(' ', '-')
            
            for base_ingredient, subs in substitution_map.items():
                if base_ingredient in ingredient_lower and restriction_key in subs:
                    substitutions.extend(subs[restriction_key])
        
        return list(set(substitutions))  # Remove duplicates

    def _calculate_recipe_score(self, recipe: Dict, user_profile: Dict) -> float:
        """Calculate recipe preference score based on user profile"""
        score = 0.0
        
        # Dietary restrictions match
        diet_labels = recipe.get('dietLabels', [])
        user_restrictions = user_profile.get('dietary_restrictions', [])
        for restriction in user_restrictions:
            if restriction.lower() in [label.lower() for label in diet_labels]:
                score += 10
        
        # Cooking time preference (assuming most users prefer shorter times)
        total_time = recipe.get('totalTime', 60)
        if total_time <= 30:
            score += 5
        elif total_time <= 45:
            score += 3
        
        # Calorie alignment
        target_calories = user_profile.get('daily_calories', 2000) // 4  # Per meal estimate
        recipe_calories = recipe.get('calories', 0) / max(recipe.get('yield', 1), 1)
        calorie_diff = abs(target_calories - recipe_calories)
        if calorie_diff <= 100:
            score += 5
        elif calorie_diff <= 200:
            score += 2
        
        return score

    def _calculate_recipe_difficulty(self, recipe: Dict, cooking_skill: str) -> int:
        """Calculate recipe difficulty (1-5 scale)"""
        difficulty = 3  # Default medium
        
        # Adjust based on cooking time
        total_time = recipe.get('totalTime', 30)
        if total_time <= 15:
            difficulty = 1
        elif total_time <= 30:
            difficulty = 2
        elif total_time <= 60:
            difficulty = 3
        elif total_time <= 90:
            difficulty = 4
        else:
            difficulty = 5
        
        # Adjust based on ingredient count
        ingredient_count = len(recipe.get('ingredients', []))
        if ingredient_count > 15:
            difficulty += 1
        elif ingredient_count < 5:
            difficulty -= 1
        
        return max(1, min(5, difficulty))  # Clamp between 1-5

    def _analyze_nutrition_trends(self, user_id: str, current_day: DayNutrition) -> List[str]:
        """Analyze nutrition trends and provide insights"""
        insights = []
        
        # Simple trend analysis (would be more sophisticated in practice)
        if current_day.kcal < 1200:
            insights.append("🚨 Very low calorie intake - consider adding healthy snacks")
        elif current_day.kcal > 3000:
            insights.append("⚠️ High calorie intake - consider portion control")
        
        if current_day.protein < 50:
            insights.append("🥩 Low protein - add lean meats, beans, or protein powder")
        
        if current_day.fiber < 15:
            insights.append("🌾 Low fiber - add more vegetables, fruits, and whole grains")
        
        if current_day.water_cups < 6:
            insights.append("💧 Increase water intake for better hydration")
        
        return insights

    def _format_daily_summary(self, nutrition_data: DayNutrition) -> str:
        """Format daily nutrition summary"""
        return f"""📅 Daily Summary - {nutrition_data.date}
🔥 {nutrition_data.kcal} calories
🥩 {nutrition_data.protein}g protein
🌾 {nutrition_data.fiber}g fiber
💧 {nutrition_data.water_cups} cups water
😊 Mood: {nutrition_data.mood or 'Not tracked'}"""

    def _get_daily_recommendations(self, nutrition_data: DayNutrition) -> List[str]:
        """Get daily recommendations based on nutrition data"""
        recommendations = []
        
        targets = self.default_nutrition_targets
        
        if nutrition_data.protein < targets['protein'] * 0.8:
            recommendations.append("Add a protein-rich snack like Greek yogurt or nuts")
        
        if nutrition_data.fiber < targets['fiber'] * 0.5:
            recommendations.append("Include more vegetables or fruits in your next meal")
        
        if nutrition_data.water_cups < targets['water_cups'] * 0.7:
            recommendations.append("Drink more water throughout the day")
        
        return recommendations

    def _calculate_nutrition_trends(self, history: List[DayNutrition]) -> Dict[str, Any]:
        """Calculate nutrition trends from history"""
        if not history:
            return {}
        
        # Calculate averages
        avg_calories = sum(day.kcal for day in history) / len(history)
        avg_protein = sum(day.protein for day in history) / len(history)
        avg_fiber = sum(day.fiber for day in history) / len(history)
        avg_water = sum(day.water_cups for day in history) / len(history)
        
        return {
            'avg_calories': round(avg_calories),
            'avg_protein': round(avg_protein, 1),
            'avg_fiber': round(avg_fiber, 1),
            'avg_water': round(avg_water, 1),
            'trend_direction': 'stable'  # Would calculate actual trends
        }

    def _format_weekly_summary(self, history: List[DayNutrition]) -> str:
        """Format weekly nutrition summary"""
        if not history:
            return "No nutrition data available"
        
        trends = self._calculate_nutrition_trends(history)
        return f"""📊 Weekly Summary
📈 Avg: {trends['avg_calories']} cal, {trends['avg_protein']}g protein
🌊 Hydration: {trends['avg_water']} cups/day
🌾 Fiber: {trends['avg_fiber']}g/day"""

    async def _get_ai_nutrition_fallback(self, ingredients: List[str], user_profile: Dict) -> str:
        """Get AI-generated nutrition advice when API fails"""
        try:
            prompt = f"""
            Provide brief nutrition advice for a meal with these ingredients: {', '.join(ingredients[:5])}
            
            User context: {user_profile.get('fitness_goals', 'general health')}
            
            Give 2-3 actionable tips in under 100 words.
            """
            
            response = self._invoke_model(prompt, max_tokens=200)
            return response or "Focus on balanced nutrition with adequate protein, fiber, and hydration."
            
        except Exception as e:
            logger.error(f"Error in AI nutrition fallback: {e}")
            return "Eat a balanced diet with plenty of vegetables, lean proteins, and whole grains."

    def _format_detailed_nutrition_for_whatsapp(self, nutrition_data: Dict, ai_insights: List[str]) -> str:
        """Format detailed nutrition analysis for WhatsApp"""
        try:
            macros = nutrition_data.get('macros', {})
            minerals = nutrition_data.get('minerals', {})
            
            summary = f"""📊 *Detailed Nutrition Analysis*

🔥 *Calories:* {nutrition_data.get('calories', 0)}
⚖️ *Total Weight:* {nutrition_data.get('total_weight', 0)}g

🍖 *Macronutrients:*
• Protein: {macros.get('protein', 0)}g
• Carbs: {macros.get('carbs', 0)}g  
• Fat: {macros.get('fat', 0)}g
• Fiber: {macros.get('fiber', 0)}g

🧂 *Key Minerals:*
• Sodium: {minerals.get('sodium', 0)}mg
• Calcium: {minerals.get('calcium', 0)}mg
• Iron: {minerals.get('iron', 0)}mg

🤖 *AI Insights:*"""
            
            for i, insight in enumerate(ai_insights[:3], 1):
                summary += f"\n{i}. {insight}"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error formatting detailed nutrition: {e}")
            return "Nutrition analysis formatting error"

    async def _get_nutrition_recommendations(self, nutrition_data: Dict, user_goals: Dict) -> List[str]:
        """Get specific nutrition recommendations based on analysis"""
        try:
            recommendations = []
            macros = nutrition_data.get('macros', {})
            
            # Protein recommendations
            protein = macros.get('protein', 0)
            target_protein = user_goals.get('daily_calories', 2000) * 0.15 / 4  # 15% of calories
            
            if protein < target_protein * 0.7:
                recommendations.append("Add more protein sources like lean meats, eggs, or legumes")
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

    def _generate_nutrition_insights(self, nutrition_data: Dict, user_goals: Dict) -> List[str]:
        """Generate nutrition insights (synchronous version for compatibility)"""
        try:
            # Run async method in sync context
            return asyncio.run(self._generate_ai_nutrition_insights(nutrition_data, user_goals))
        except Exception as e:
            logger.error(f"Error generating nutrition insights: {e}")
            return ["Focus on balanced nutrition with variety"]
