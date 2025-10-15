"""
Pure domain service for nutrition calculation logic
Separated from infrastructure concerns following hexagonal architecture
"""

import logging
import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from packages.core.src.interfaces.repositories import NutritionRepository, CacheRepository
from packages.core.src.interfaces.services import NutritionAPIService, ConfigurationService
from packages.core.src.interfaces.domain import (
    Recipe, 
    NutritionProfile, 
    DietaryRestriction, 
    NutritionDomainService
)

logger = logging.getLogger(__name__)


class NutritionCalculationService(NutritionDomainService):
    """Pure domain service for nutrition calculations - no infrastructure dependencies"""
    
    def __init__(
        self,
        nutrition_api: NutritionAPIService,
        nutrition_repo: NutritionRepository,
        cache_repo: CacheRepository,
        config_service: ConfigurationService
    ):
        self.nutrition_api = nutrition_api
        self.nutrition_repo = nutrition_repo
        self.cache = cache_repo
        self.config = config_service
    
    def validate_business_rules(self, data: Dict[str, Any]) -> bool:
        """Validate nutrition-specific business rules"""
        # Validate calorie targets
        if 'calorie_target' in data:
            calorie_target = data['calorie_target']
            if calorie_target and (calorie_target < 800 or calorie_target > 4000):
                return False
        
        # Validate prep time constraints
        if 'max_prep_time' in data:
            prep_time = data['max_prep_time']
            if prep_time and (prep_time < 5 or prep_time > 240):
                return False
        
        return True
    
    def calculate_nutrition_score(self, meal_plan: Any, profile: NutritionProfile) -> float:
        """Calculate how well a meal plan matches nutrition profile"""
        score = 1.0
        
        # Check dietary restrictions compliance
        if hasattr(meal_plan, 'dietary_tags'):
            required_tags = [dr.value for dr in profile.dietary_restrictions]
            missing_tags = set(required_tags) - set(meal_plan.dietary_tags)
            score -= len(missing_tags) * 0.2
        
        # Check calorie target compliance
        if profile.calorie_target and hasattr(meal_plan, 'total_calories'):
            calorie_diff = abs(meal_plan.total_calories - profile.calorie_target)
            calorie_variance = calorie_diff / profile.calorie_target
            if calorie_variance > 0.2:  # More than 20% off
                score -= calorie_variance * 0.3
        
        # Check prep time compliance
        if hasattr(meal_plan, 'total_prep_time'):
            if meal_plan.total_prep_time > profile.max_prep_time:
                score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def suggest_recipe_alternatives(self, recipe: Recipe, restrictions: List[DietaryRestriction]) -> List[Recipe]:
        """Suggest alternative recipes that meet restrictions"""
        # Domain logic for suggesting alternatives
        # This would typically involve analyzing recipe characteristics
        # and finding similar recipes that meet the restrictions
        
        alternatives = []
        restriction_values = [r.value for r in restrictions]
        
        # Basic matching logic - in real implementation, this would be more sophisticated
        if recipe.matches_dietary_restrictions(restrictions):
            return [recipe]  # Current recipe already matches
        
        # For now, return empty list - real implementation would search for alternatives
        return alternatives
    
    async def enhanced_recipe_search(self, meal_name: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced recipe search with caching and optimization"""
        try:
            # Build search parameters using domain logic
            search_filters = self._build_search_filters(meal_name, user_profile)
            
            # Generate cache key
            cache_key = self._generate_cache_key(meal_name, search_filters)
            
            # Check cache first
            cached_result = await self.nutrition_repo.get_cached_recipe_search(cache_key)
            if cached_result:
                logger.info(f"Cache hit for recipe search: {meal_name}")
                return cached_result
            
            # Search via external API
            search_result = await self.nutrition_api.search_recipes(meal_name, search_filters)
            
            if search_result:
                # Cache the result
                await self.nutrition_repo.cache_recipe_search(cache_key, search_result, ttl_hours=48)
                logger.info(f"Cached recipe search result for: {meal_name}")
            
            return search_result
        
        except Exception as e:
            logger.error(f"Error in enhanced recipe search: {e}")
            return {}
    
    async def analyze_nutrition_content(self, ingredients: List[str]) -> Dict[str, Any]:
        """Analyze nutritional content using domain rules"""
        try:
            # Validate ingredients using domain rules
            if not self._validate_ingredients(ingredients):
                return {'error': 'Invalid ingredients provided'}
            
            # Use external API for analysis
            nutrition_data = await self.nutrition_api.analyze_nutrition(ingredients)
            
            if nutrition_data:
                # Apply domain-specific processing
                processed_data = self._process_nutrition_data(nutrition_data)
                return processed_data
            
            return {}
        
        except Exception as e:
            logger.error(f"Error analyzing nutrition content: {e}")
            return {}
    
    async def calculate_daily_nutrition_goals(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate daily nutrition goals based on user profile"""
        try:
            # Extract user characteristics
            age = user_profile.get('age', 30)
            gender = user_profile.get('gender', 'unknown')
            activity_level = user_profile.get('activity_level', 'moderate')
            health_goals = user_profile.get('health_goals', [])
            
            # Calculate base metabolic rate using domain logic
            bmr = self._calculate_bmr(age, gender, user_profile.get('weight'), user_profile.get('height'))
            
            # Adjust for activity level
            activity_multipliers = {
                'sedentary': 1.2,
                'light': 1.375,
                'moderate': 1.55,
                'active': 1.725,
                'very_active': 1.9
            }
            
            total_calories = bmr * activity_multipliers.get(activity_level, 1.55)
            
            # Adjust for health goals
            if 'weight_loss' in health_goals:
                total_calories *= 0.85  # 15% deficit
            elif 'weight_gain' in health_goals:
                total_calories *= 1.15  # 15% surplus
            
            # Calculate macronutrient distribution
            protein_calories = total_calories * 0.25  # 25% protein
            fat_calories = total_calories * 0.30  # 30% fat
            carb_calories = total_calories * 0.45  # 45% carbs
            
            return {
                'total_calories': int(total_calories),
                'protein_grams': int(protein_calories / 4),  # 4 cal/gram
                'fat_grams': int(fat_calories / 9),  # 9 cal/gram
                'carb_grams': int(carb_calories / 4),  # 4 cal/gram
                'fiber_grams': max(25, int(total_calories / 1000 * 14)),  # 14g per 1000 cal
                'calculation_method': 'domain_based_bmr'
            }
        
        except Exception as e:
            logger.error(f"Error calculating nutrition goals: {e}")
            return {}
    
    def _build_search_filters(self, meal_name: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Build search filters using domain logic"""
        filters = {
            'from': 0,
            'to': 5
        }
        
        # Extract dietary restrictions
        dietary_restrictions = user_profile.get('dietary_restrictions', [])
        if dietary_restrictions:
            filters['dietary_restrictions'] = dietary_restrictions
        
        # Extract health labels
        health_labels = user_profile.get('health_labels', [])
        if health_labels:
            filters['health_labels'] = health_labels
        
        # Time and calorie constraints
        max_prep_time = user_profile.get('max_prep_time', 45)
        min_calories = user_profile.get('min_calories', 200)
        max_calories = user_profile.get('max_calories', 800)
        
        filters['max_prep_time'] = max_prep_time
        filters['calorie_range'] = f"{min_calories}-{max_calories}"
        
        return filters
    
    def _generate_cache_key(self, meal_name: str, filters: Dict[str, Any]) -> str:
        """Generate cache key for recipe search"""
        cache_data = f"{meal_name}:{json.dumps(filters, sort_keys=True)}"
        return f"recipe_search:{hashlib.md5(cache_data.encode()).hexdigest()}"
    
    def _validate_ingredients(self, ingredients: List[str]) -> bool:
        """Validate ingredients list using domain rules"""
        if not ingredients or len(ingredients) == 0:
            return False
        
        # Check for valid ingredient format
        for ingredient in ingredients:
            if not isinstance(ingredient, str) or len(ingredient.strip()) < 2:
                return False
        
        return True
    
    def _process_nutrition_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw nutrition data using domain logic"""
        processed = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0,
            'fiber': 0,
            'sodium': 0,
            'vitamins': {},
            'minerals': {}
        }
        
        # Extract and normalize nutrition information
        if 'totalNutrients' in raw_data:
            nutrients = raw_data['totalNutrients']
            
            processed['calories'] = nutrients.get('ENERC_KCAL', {}).get('quantity', 0)
            processed['protein'] = nutrients.get('PROCNT', {}).get('quantity', 0)
            processed['carbs'] = nutrients.get('CHOCDF', {}).get('quantity', 0)
            processed['fat'] = nutrients.get('FAT', {}).get('quantity', 0)
            processed['fiber'] = nutrients.get('FIBTG', {}).get('quantity', 0)
            processed['sodium'] = nutrients.get('NA', {}).get('quantity', 0)
        
        return processed
    
    def _calculate_bmr(self, age: int, gender: str, weight: Optional[float], height: Optional[float]) -> float:
        """Calculate Basal Metabolic Rate using Mifflin-St Jeor equation"""
        # Default values if not provided
        if not weight:
            weight = 70.0  # kg
        if not height:
            height = 170.0  # cm
        
        # Mifflin-St Jeor equation
        if gender.lower() == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:  # female or unknown
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
        return max(1200, bmr)  # Minimum 1200 calories for safety
