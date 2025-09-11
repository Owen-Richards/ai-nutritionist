"""
Variety Manager - Meal variety and rotation enforcement
Consolidates: meal_variety_service.py, rotation_service.py
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import random

logger = logging.getLogger(__name__)

@dataclass
class VarietyMetrics:
    """Metrics for measuring meal variety"""
    ingredient_diversity: float
    cuisine_diversity: float
    cooking_method_diversity: float
    protein_source_diversity: float
    repetition_score: float
    overall_variety_score: float

class VarietyManager:
    """
    Manages meal variety and rotation to prevent monotony and ensure
    nutritional diversity in meal plans.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.variety_rules = self._initialize_variety_rules()
        self.cuisine_categories = self._initialize_cuisine_categories()
        self.cooking_methods = self._initialize_cooking_methods()
        self.protein_sources = self._initialize_protein_sources()
    
    def ensure_meal_variety(
        self, 
        meal_plan: Dict[str, Any], 
        variety_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Ensure adequate variety in a meal plan
        
        Args:
            meal_plan: Meal plan to analyze and improve
            variety_preferences: User preferences for variety level
            
        Returns:
            Meal plan with improved variety
        """
        try:
            self.logger.info("Analyzing and improving meal plan variety")
            
            # Analyze current variety
            variety_analysis = self.analyze_meal_variety(meal_plan)
            
            # Determine if variety improvement is needed
            if variety_analysis["overall_variety_score"] < 70:  # Score below 70/100
                self.logger.info(f"Variety score {variety_analysis['overall_variety_score']:.1f} below threshold, improving...")
                improved_plan = self._improve_meal_variety(meal_plan, variety_analysis)
            else:
                improved_plan = meal_plan.copy()
                self.logger.info(f"Variety score {variety_analysis['overall_variety_score']:.1f} is adequate")
            
            # Add variety metadata
            final_variety = self.analyze_meal_variety(improved_plan)
            improved_plan["variety_analysis"] = final_variety
            improved_plan["variety_improvements"] = {
                "original_score": variety_analysis["overall_variety_score"],
                "improved_score": final_variety["overall_variety_score"],
                "improvement": final_variety["overall_variety_score"] - variety_analysis["overall_variety_score"]
            }
            
            return improved_plan
            
        except Exception as e:
            self.logger.error(f"Error ensuring meal variety: {str(e)}")
            return meal_plan
    
    def analyze_meal_variety(self, meal_plan: Dict[str, Any]) -> VarietyMetrics:
        """
        Analyze the variety metrics of a meal plan
        
        Args:
            meal_plan: Meal plan to analyze
            
        Returns:
            Comprehensive variety metrics
        """
        try:
            ingredients_used = set()
            cuisines_used = set()
            cooking_methods_used = set()
            protein_sources_used = set()
            meal_names = []
            
            # Extract data from all meals
            for meal_day in meal_plan.get('meals', []):
                for meal_time, meal_data in meal_day.items():
                    if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks'] and isinstance(meal_data, dict):
                        # Collect ingredients
                        ingredients = meal_data.get('ingredients', [])
                        ingredients_used.update(ing.lower() for ing in ingredients)
                        
                        # Collect cuisine types
                        cuisine = meal_data.get('cuisine_type', 'unknown')
                        cuisines_used.add(cuisine.lower())
                        
                        # Collect cooking methods
                        cooking_method = meal_data.get('cooking_method', 'unknown')
                        cooking_methods_used.add(cooking_method.lower())
                        
                        # Collect protein sources
                        proteins = self._extract_protein_sources(ingredients)
                        protein_sources_used.update(proteins)
                        
                        # Collect meal names for repetition analysis
                        meal_name = meal_data.get('name', 'unknown')
                        meal_names.append(meal_name.lower())
            
            # Calculate diversity scores
            total_meals = len(meal_names)
            if total_meals == 0:
                return VarietyMetrics(0, 0, 0, 0, 0, 0)
            
            ingredient_diversity = min(100, (len(ingredients_used) / total_meals) * 20)
            cuisine_diversity = min(100, (len(cuisines_used) / max(total_meals // 3, 1)) * 100)
            cooking_method_diversity = min(100, (len(cooking_methods_used) / max(total_meals // 2, 1)) * 100)
            protein_source_diversity = min(100, (len(protein_sources_used) / max(total_meals // 2, 1)) * 100)
            
            # Calculate repetition score (lower is better, then inverted)
            repetition_count = len(meal_names) - len(set(meal_names))
            repetition_score = max(0, 100 - (repetition_count / total_meals) * 100)
            
            # Calculate overall variety score
            overall_variety_score = (
                ingredient_diversity * 0.3 +
                cuisine_diversity * 0.2 +
                cooking_method_diversity * 0.2 +
                protein_source_diversity * 0.2 +
                repetition_score * 0.1
            )
            
            return VarietyMetrics(
                ingredient_diversity=ingredient_diversity,
                cuisine_diversity=cuisine_diversity,
                cooking_method_diversity=cooking_method_diversity,
                protein_source_diversity=protein_source_diversity,
                repetition_score=repetition_score,
                overall_variety_score=overall_variety_score
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing meal variety: {str(e)}")
            return VarietyMetrics(0, 0, 0, 0, 0, 0)
    
    def enforce_rotation_rules(
        self, 
        meal_plan: Dict[str, Any], 
        previous_meals: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enforce meal rotation rules to prevent excessive repetition
        
        Args:
            meal_plan: Current meal plan
            previous_meals: Previously consumed meals for rotation context
            
        Returns:
            Meal plan with rotation rules enforced
        """
        try:
            self.logger.info("Enforcing meal rotation rules")
            
            rotated_plan = meal_plan.copy()
            rotation_violations = []
            
            # Build history of recent meals
            recent_meals = self._build_meal_history(previous_meals or [])
            
            # Check each meal against rotation rules
            for day_idx, meal_day in enumerate(rotated_plan.get('meals', [])):
                for meal_time, meal_data in meal_day.items():
                    if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks'] and isinstance(meal_data, dict):
                        violation = self._check_rotation_violation(
                            meal_data, recent_meals, day_idx, meal_time
                        )
                        
                        if violation:
                            rotation_violations.append(violation)
                            # Replace with alternative meal
                            alternative = self._find_rotation_alternative(
                                meal_data, recent_meals, violation
                            )
                            if alternative:
                                meal_day[meal_time] = alternative
                                self.logger.info(f"Replaced {meal_data.get('name')} with {alternative.get('name')} for variety")
            
            # Add rotation metadata
            rotated_plan["rotation_analysis"] = {
                "violations_found": len(rotation_violations),
                "violations_fixed": len([v for v in rotation_violations if v.get('fixed', False)]),
                "rotation_rules_applied": list(self.variety_rules.keys())
            }
            
            return rotated_plan
            
        except Exception as e:
            self.logger.error(f"Error enforcing rotation rules: {str(e)}")
            return meal_plan
    
    def suggest_variety_improvements(
        self, 
        meal_plan: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Suggest specific improvements to increase meal variety
        
        Args:
            meal_plan: Meal plan to analyze
            
        Returns:
            List of specific variety improvement suggestions
        """
        try:
            variety_analysis = self.analyze_meal_variety(meal_plan)
            suggestions = []
            
            # Analyze ingredient variety
            if variety_analysis.ingredient_diversity < 60:
                suggestions.append({
                    "type": "ingredient_diversity",
                    "priority": "high",
                    "suggestion": "Add more diverse ingredients to increase nutritional variety",
                    "specific_actions": [
                        "Include more colorful vegetables",
                        "Try different protein sources",
                        "Experiment with various grains and legumes"
                    ]
                })
            
            # Analyze cuisine variety
            if variety_analysis.cuisine_diversity < 50:
                suggestions.append({
                    "type": "cuisine_diversity",
                    "priority": "medium",
                    "suggestion": "Incorporate different cuisine styles for cultural variety",
                    "specific_actions": [
                        "Add Mediterranean dishes",
                        "Include Asian-inspired meals",
                        "Try Latin American flavors"
                    ]
                })
            
            # Analyze cooking method variety
            if variety_analysis.cooking_method_diversity < 60:
                suggestions.append({
                    "type": "cooking_method_diversity",
                    "priority": "medium",
                    "suggestion": "Use different cooking methods for texture variety",
                    "specific_actions": [
                        "Include grilled options",
                        "Add steamed vegetables",
                        "Try roasted and baked dishes"
                    ]
                })
            
            # Analyze protein variety
            if variety_analysis.protein_source_diversity < 70:
                suggestions.append({
                    "type": "protein_diversity",
                    "priority": "high",
                    "suggestion": "Diversify protein sources for complete amino acid profile",
                    "specific_actions": [
                        "Alternate between animal and plant proteins",
                        "Include fish and seafood",
                        "Try different legumes and nuts"
                    ]
                })
            
            # Analyze repetition
            if variety_analysis.repetition_score < 80:
                suggestions.append({
                    "type": "repetition_reduction",
                    "priority": "high",
                    "suggestion": "Reduce meal repetition to prevent monotony",
                    "specific_actions": [
                        "Replace repeated meals with alternatives",
                        "Modify recipes with different seasonings",
                        "Use rotation scheduling"
                    ]
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating variety suggestions: {str(e)}")
            return []
    
    def generate_seasonal_variety(
        self, 
        meal_plan: Dict[str, Any], 
        current_season: str = None
    ) -> Dict[str, Any]:
        """
        Adjust meal plan to include seasonal variety
        
        Args:
            meal_plan: Meal plan to adjust
            current_season: Current season for seasonal adjustments
            
        Returns:
            Seasonally adjusted meal plan
        """
        try:
            if not current_season:
                current_season = self._get_current_season()
            
            self.logger.info(f"Adding seasonal variety for {current_season}")
            
            seasonal_plan = meal_plan.copy()
            seasonal_ingredients = self._get_seasonal_ingredients(current_season)
            seasonal_recipes = self._get_seasonal_recipes(current_season)
            
            # Replace some meals with seasonal alternatives
            for meal_day in seasonal_plan.get('meals', []):
                for meal_time, meal_data in meal_day.items():
                    if meal_time in ['breakfast', 'lunch', 'dinner'] and isinstance(meal_data, dict):
                        # 30% chance to replace with seasonal alternative
                        if random.random() < 0.3:
                            seasonal_alternative = self._find_seasonal_alternative(
                                meal_data, seasonal_recipes, seasonal_ingredients
                            )
                            if seasonal_alternative:
                                meal_day[meal_time] = seasonal_alternative
            
            # Add seasonal metadata
            seasonal_plan["seasonal_adjustments"] = {
                "season": current_season,
                "seasonal_ingredients_featured": seasonal_ingredients[:10],
                "adjustments_made": True
            }
            
            return seasonal_plan
            
        except Exception as e:
            self.logger.error(f"Error generating seasonal variety: {str(e)}")
            return meal_plan
    
    def _improve_meal_variety(
        self, 
        meal_plan: Dict[str, Any], 
        variety_analysis: VarietyMetrics
    ) -> Dict[str, Any]:
        """Implement specific variety improvements"""
        improved_plan = meal_plan.copy()
        
        # Identify meals that need replacement
        meals_to_replace = self._identify_monotonous_meals(improved_plan)
        
        for meal_location in meals_to_replace:
            day_idx, meal_time = meal_location
            current_meal = improved_plan['meals'][day_idx][meal_time]
            
            # Find a more varied alternative
            alternative = self._find_variety_alternative(current_meal, improved_plan)
            if alternative:
                improved_plan['meals'][day_idx][meal_time] = alternative
        
        return improved_plan
    
    def _extract_protein_sources(self, ingredients: List[str]) -> List[str]:
        """Extract protein sources from ingredient list"""
        protein_sources = []
        
        for ingredient in ingredients:
            ingredient_lower = ingredient.lower()
            for protein_category, proteins in self.protein_sources.items():
                if any(protein in ingredient_lower for protein in proteins):
                    protein_sources.append(protein_category)
                    break
        
        return protein_sources
    
    def _build_meal_history(self, previous_meals: List[Dict[str, Any]]) -> Dict[str, int]:
        """Build a history of recent meals for rotation analysis"""
        meal_history = {}
        
        for meal in previous_meals[-21:]:  # Last 21 meals (about a week)
            meal_name = meal.get('name', '').lower()
            if meal_name:
                meal_history[meal_name] = meal_history.get(meal_name, 0) + 1
        
        return meal_history
    
    def _check_rotation_violation(
        self, 
        meal_data: Dict[str, Any], 
        recent_meals: Dict[str, int], 
        day_idx: int, 
        meal_time: str
    ) -> Optional[Dict[str, Any]]:
        """Check if a meal violates rotation rules"""
        meal_name = meal_data.get('name', '').lower()
        
        # Check if meal was used too recently
        if meal_name in recent_meals:
            frequency = recent_meals[meal_name]
            
            # Apply rotation rules
            for rule_name, rule in self.variety_rules.items():
                if rule['applies_to'](meal_data) and frequency >= rule['max_frequency']:
                    return {
                        "meal_name": meal_name,
                        "rule_violated": rule_name,
                        "frequency": frequency,
                        "max_allowed": rule['max_frequency'],
                        "day": day_idx,
                        "meal_time": meal_time
                    }
        
        return None
    
    def _find_rotation_alternative(
        self, 
        original_meal: Dict[str, Any], 
        recent_meals: Dict[str, int], 
        violation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find an alternative meal that doesn't violate rotation rules"""
        # Simple alternative generation
        alternative = original_meal.copy()
        alternative['name'] = f"Alternative {original_meal.get('name', 'Meal')}"
        alternative['is_rotation_alternative'] = True
        violation['fixed'] = True
        
        return alternative
    
    def _identify_monotonous_meals(self, meal_plan: Dict[str, Any]) -> List[Tuple[int, str]]:
        """Identify meals that contribute to monotony"""
        meal_counts = {}
        meal_locations = []
        
        # Count meal repetitions and track locations
        for day_idx, meal_day in enumerate(meal_plan.get('meals', [])):
            for meal_time, meal_data in meal_day.items():
                if meal_time in ['breakfast', 'lunch', 'dinner'] and isinstance(meal_data, dict):
                    meal_name = meal_data.get('name', '').lower()
                    if meal_name:
                        if meal_name not in meal_counts:
                            meal_counts[meal_name] = []
                        meal_counts[meal_name].append((day_idx, meal_time))
        
        # Identify repeated meals
        monotonous_meals = []
        for meal_name, locations in meal_counts.items():
            if len(locations) > 1:  # Repeated meal
                # Keep first occurrence, mark others for replacement
                monotonous_meals.extend(locations[1:])
        
        return monotonous_meals
    
    def _find_variety_alternative(
        self, 
        current_meal: Dict[str, Any], 
        meal_plan: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find a more varied alternative for a meal"""
        # Simple variety improvement
        alternative = current_meal.copy()
        alternative['name'] = f"Varied {current_meal.get('name', 'Meal')}"
        alternative['variety_improvement'] = True
        
        # Add different ingredients or cooking method
        current_ingredients = set(ing.lower() for ing in current_meal.get('ingredients', []))
        new_ingredients = ["spinach", "quinoa", "avocado"]  # Add variety ingredients
        
        for new_ing in new_ingredients:
            if new_ing not in current_ingredients:
                alternative.setdefault('ingredients', []).append(new_ing.title())
                break
        
        return alternative
    
    def _get_current_season(self) -> str:
        """Get current season"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"
    
    def _get_seasonal_ingredients(self, season: str) -> List[str]:
        """Get ingredients that are in season"""
        seasonal_ingredients = {
            "spring": ["asparagus", "peas", "artichokes", "spring_onions", "strawberries"],
            "summer": ["tomatoes", "corn", "zucchini", "berries", "stone_fruits"],
            "fall": ["pumpkin", "squash", "apples", "cranberries", "root_vegetables"],
            "winter": ["citrus", "cabbage", "potatoes", "winter_squash", "pomegranate"]
        }
        return seasonal_ingredients.get(season, [])
    
    def _get_seasonal_recipes(self, season: str) -> List[Dict[str, Any]]:
        """Get recipes appropriate for the season"""
        # Placeholder for seasonal recipe database
        return [
            {"name": f"Seasonal {season} Bowl", "season": season},
            {"name": f"{season.title()} Soup", "season": season}
        ]
    
    def _find_seasonal_alternative(
        self, 
        meal_data: Dict[str, Any], 
        seasonal_recipes: List[Dict[str, Any]], 
        seasonal_ingredients: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Find seasonal alternative for a meal"""
        if seasonal_recipes:
            alternative = seasonal_recipes[0].copy()
            alternative.update({
                "calories": meal_data.get('calories', 400),
                "protein": meal_data.get('protein', 25),
                "ingredients": seasonal_ingredients[:5]
            })
            return alternative
        return None
    
    def _initialize_variety_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize meal variety and rotation rules"""
        return {
            "same_meal_weekly": {
                "max_frequency": 1,
                "time_period": "week",
                "applies_to": lambda meal: True
            },
            "same_protein_daily": {
                "max_frequency": 2,
                "time_period": "day",
                "applies_to": lambda meal: meal.get('primary_protein') is not None
            },
            "same_cuisine_consecutive": {
                "max_frequency": 2,
                "time_period": "consecutive",
                "applies_to": lambda meal: meal.get('cuisine_type') is not None
            }
        }
    
    def _initialize_cuisine_categories(self) -> Dict[str, List[str]]:
        """Initialize cuisine categories for variety tracking"""
        return {
            "mediterranean": ["greek", "italian", "spanish", "turkish"],
            "asian": ["chinese", "japanese", "thai", "korean", "indian"],
            "latin": ["mexican", "brazilian", "peruvian", "caribbean"],
            "american": ["southern", "cajun", "southwestern", "classic_american"],
            "middle_eastern": ["lebanese", "moroccan", "persian", "israeli"]
        }
    
    def _initialize_cooking_methods(self) -> List[str]:
        """Initialize cooking methods for variety tracking"""
        return [
            "grilled", "baked", "roasted", "steamed", "sauteed",
            "braised", "stir_fried", "raw", "poached", "broiled"
        ]
    
    def _initialize_protein_sources(self) -> Dict[str, List[str]]:
        """Initialize protein source categories"""
        return {
            "poultry": ["chicken", "turkey", "duck"],
            "red_meat": ["beef", "pork", "lamb"],
            "seafood": ["fish", "salmon", "tuna", "shrimp", "crab"],
            "plant_protein": ["beans", "lentils", "tofu", "tempeh", "quinoa"],
            "dairy": ["cheese", "yogurt", "milk"],
            "eggs": ["eggs", "egg_whites"],
            "nuts_seeds": ["almonds", "walnuts", "chia", "hemp"]
        }
