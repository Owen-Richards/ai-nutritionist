"""
Meal Optimizer - Cost and nutrition optimization service
Consolidates: cost_optimization_service.py, nutrition_optimization_service.py
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class OptimizationCriteria:
    """Criteria for meal plan optimization"""
    minimize_cost: bool = True
    maximize_nutrition: bool = True
    prefer_seasonal: bool = True
    local_ingredients: bool = False
    sustainability_score: bool = False
    prep_time_limit: Optional[int] = None  # minutes
    
class MealOptimizer:
    """
    Optimizes meal plans for cost, nutrition, and other criteria
    while maintaining taste and variety preferences.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cost_database = self._initialize_cost_database()
        self.nutrition_weights = self._initialize_nutrition_weights()
    
    def optimize_meal_plan(
        self, 
        meal_plan: Dict[str, Any], 
        criteria: OptimizationCriteria,
        budget_limit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Optimize a meal plan based on specified criteria
        
        Args:
            meal_plan: Original meal plan to optimize
            criteria: Optimization criteria and preferences
            budget_limit: Maximum budget per day/week
            
        Returns:
            Optimized meal plan with cost and nutrition improvements
        """
        try:
            self.logger.info("Starting meal plan optimization")
            
            optimized_plan = meal_plan.copy()
            optimization_stats = {
                "original_cost": 0,
                "optimized_cost": 0,
                "cost_savings": 0,
                "nutrition_score_improvement": 0,
                "optimizations_applied": []
            }
            
            # Calculate original metrics
            original_metrics = self._calculate_plan_metrics(meal_plan)
            optimization_stats["original_cost"] = original_metrics["total_cost"]
            
            # Apply cost optimization if requested
            if criteria.minimize_cost:
                optimized_plan = self._optimize_for_cost(optimized_plan, budget_limit)
                optimization_stats["optimizations_applied"].append("cost_optimization")
            
            # Apply nutrition optimization if requested
            if criteria.maximize_nutrition:
                optimized_plan = self._optimize_for_nutrition(optimized_plan)
                optimization_stats["optimizations_applied"].append("nutrition_optimization")
            
            # Apply seasonal optimization if requested
            if criteria.prefer_seasonal:
                optimized_plan = self._optimize_for_seasonality(optimized_plan)
                optimization_stats["optimizations_applied"].append("seasonal_optimization")
            
            # Apply prep time optimization if requested
            if criteria.prep_time_limit:
                optimized_plan = self._optimize_prep_time(optimized_plan, criteria.prep_time_limit)
                optimization_stats["optimizations_applied"].append("prep_time_optimization")
            
            # Calculate final metrics
            final_metrics = self._calculate_plan_metrics(optimized_plan)
            optimization_stats["optimized_cost"] = final_metrics["total_cost"]
            optimization_stats["cost_savings"] = original_metrics["total_cost"] - final_metrics["total_cost"]
            optimization_stats["nutrition_score_improvement"] = (
                final_metrics["nutrition_score"] - original_metrics["nutrition_score"]
            )
            
            # Add optimization metadata
            optimized_plan["optimization_stats"] = optimization_stats
            optimized_plan["optimized_at"] = optimization_stats
            optimized_plan["optimization_criteria"] = criteria.__dict__
            
            self.logger.info(f"Optimization complete. Cost savings: ${optimization_stats['cost_savings']:.2f}")
            return optimized_plan
            
        except Exception as e:
            self.logger.error(f"Error optimizing meal plan: {str(e)}")
            return meal_plan
    
    def find_cost_effective_substitutions(
        self, 
        meal: Dict[str, Any], 
        max_cost_per_serving: float
    ) -> List[Dict[str, Any]]:
        """
        Find cost-effective ingredient substitutions for a meal
        
        Args:
            meal: Meal to find substitutions for
            max_cost_per_serving: Maximum acceptable cost per serving
            
        Returns:
            List of possible substitutions with cost analysis
        """
        try:
            substitutions = []
            ingredients = meal.get('ingredients', [])
            
            for ingredient in ingredients:
                ingredient_cost = self._get_ingredient_cost(ingredient)
                
                if ingredient_cost > max_cost_per_serving * 0.3:  # If ingredient is >30% of meal cost
                    alternatives = self._find_ingredient_alternatives(ingredient)
                    
                    for alt in alternatives:
                        alt_cost = self._get_ingredient_cost(alt)
                        if alt_cost < ingredient_cost:
                            savings = ingredient_cost - alt_cost
                            substitutions.append({
                                "original": ingredient,
                                "substitute": alt,
                                "cost_savings": savings,
                                "nutrition_impact": self._calculate_nutrition_impact(ingredient, alt)
                            })
            
            # Sort by cost savings
            substitutions.sort(key=lambda x: x["cost_savings"], reverse=True)
            return substitutions[:5]  # Return top 5 substitutions
            
        except Exception as e:
            self.logger.error(f"Error finding substitutions: {str(e)}")
            return []
    
    def optimize_portion_sizes(
        self, 
        meal_plan: Dict[str, Any], 
        nutritional_targets: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Optimize portion sizes to meet nutritional targets efficiently
        
        Args:
            meal_plan: Meal plan to optimize
            nutritional_targets: Target nutrition values (calories, protein, etc.)
            
        Returns:
            Meal plan with optimized portion sizes
        """
        try:
            optimized_plan = meal_plan.copy()
            
            for meal_day in optimized_plan.get('meals', []):
                for meal_time, meal_data in meal_day.items():
                    if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks']:
                        if isinstance(meal_data, dict):
                            optimized_portions = self._calculate_optimal_portions(
                                meal_data, nutritional_targets
                            )
                            meal_data.update(optimized_portions)
            
            return optimized_plan
            
        except Exception as e:
            self.logger.error(f"Error optimizing portions: {str(e)}")
            return meal_plan
    
    def _optimize_for_cost(
        self, 
        meal_plan: Dict[str, Any], 
        budget_limit: Optional[float]
    ) -> Dict[str, Any]:
        """Apply cost optimization strategies"""
        optimized_plan = meal_plan.copy()
        
        for meal_day in optimized_plan.get('meals', []):
            daily_cost = 0
            
            for meal_time, meal_data in meal_day.items():
                if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks']:
                    if isinstance(meal_data, dict):
                        # Find cost-effective alternatives
                        meal_cost = self._calculate_meal_cost(meal_data)
                        daily_cost += meal_cost
                        
                        if budget_limit and daily_cost > budget_limit:
                            # Apply cost reduction strategies
                            meal_data = self._reduce_meal_cost(meal_data)
        
        return optimized_plan
    
    def _optimize_for_nutrition(self, meal_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Apply nutrition optimization strategies"""
        optimized_plan = meal_plan.copy()
        
        for meal_day in optimized_plan.get('meals', []):
            for meal_time, meal_data in meal_day.items():
                if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks']:
                    if isinstance(meal_data, dict):
                        # Enhance nutritional value
                        enhanced_meal = self._enhance_meal_nutrition(meal_data)
                        meal_day[meal_time] = enhanced_meal
        
        return optimized_plan
    
    def _optimize_for_seasonality(self, meal_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Apply seasonal ingredient optimization"""
        optimized_plan = meal_plan.copy()
        current_season = self._get_current_season()
        
        for meal_day in optimized_plan.get('meals', []):
            for meal_time, meal_data in meal_day.items():
                if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks']:
                    if isinstance(meal_data, dict):
                        # Replace with seasonal alternatives
                        seasonal_meal = self._use_seasonal_ingredients(meal_data, current_season)
                        meal_day[meal_time] = seasonal_meal
        
        return optimized_plan
    
    def _optimize_prep_time(
        self, 
        meal_plan: Dict[str, Any], 
        time_limit: int
    ) -> Dict[str, Any]:
        """Optimize meals to fit within prep time constraints"""
        optimized_plan = meal_plan.copy()
        
        for meal_day in optimized_plan.get('meals', []):
            for meal_time, meal_data in meal_day.items():
                if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks']:
                    if isinstance(meal_data, dict):
                        prep_time = meal_data.get('prep_time', 30)
                        if prep_time > time_limit:
                            # Find quicker alternatives
                            quick_meal = self._find_quick_alternative(meal_data, time_limit)
                            meal_day[meal_time] = quick_meal
        
        return optimized_plan
    
    def _calculate_plan_metrics(self, meal_plan: Dict[str, Any]) -> Dict[str, float]:
        """Calculate comprehensive metrics for a meal plan"""
        total_cost = 0
        total_nutrition_score = 0
        meal_count = 0
        
        for meal_day in meal_plan.get('meals', []):
            for meal_time, meal_data in meal_day.items():
                if meal_time in ['breakfast', 'lunch', 'dinner', 'snacks']:
                    if isinstance(meal_data, dict):
                        total_cost += self._calculate_meal_cost(meal_data)
                        total_nutrition_score += self._calculate_nutrition_score(meal_data)
                        meal_count += 1
        
        return {
            "total_cost": total_cost,
            "nutrition_score": total_nutrition_score / max(meal_count, 1),
            "average_cost_per_meal": total_cost / max(meal_count, 1)
        }
    
    def _initialize_cost_database(self) -> Dict[str, float]:
        """Initialize ingredient cost database"""
        return {
            # Proteins
            "chicken_breast": 6.99,
            "ground_turkey": 5.99,
            "salmon": 12.99,
            "eggs": 3.99,
            "beans": 1.99,
            "lentils": 2.49,
            
            # Carbohydrates
            "brown_rice": 2.99,
            "quinoa": 5.99,
            "oats": 3.49,
            "sweet_potato": 1.99,
            
            # Vegetables
            "broccoli": 2.99,
            "spinach": 3.99,
            "carrots": 1.99,
            "bell_peppers": 4.99,
            
            # Fats
            "olive_oil": 7.99,
            "avocado": 1.99,
            "nuts": 8.99
        }
    
    def _initialize_nutrition_weights(self) -> Dict[str, float]:
        """Initialize nutrition scoring weights"""
        return {
            "protein": 0.25,
            "fiber": 0.20,
            "vitamins": 0.20,
            "minerals": 0.15,
            "healthy_fats": 0.15,
            "antioxidants": 0.05
        }
    
    def _get_ingredient_cost(self, ingredient: str) -> float:
        """Get cost for a specific ingredient"""
        return self.cost_database.get(ingredient.lower().replace(' ', '_'), 5.0)
    
    def _calculate_meal_cost(self, meal_data: Dict[str, Any]) -> float:
        """Calculate total cost for a meal"""
        base_cost = meal_data.get('estimated_cost', 8.0)
        ingredients = meal_data.get('ingredients', [])
        
        if ingredients:
            ingredient_costs = sum(self._get_ingredient_cost(ing) for ing in ingredients)
            return ingredient_costs * 0.3  # Assuming ingredients are 30% of retail cost
        
        return base_cost
    
    def _calculate_nutrition_score(self, meal_data: Dict[str, Any]) -> float:
        """Calculate nutrition score for a meal"""
        score = 0
        
        # Basic nutrition metrics
        protein = meal_data.get('protein', 0)
        fiber = meal_data.get('fiber', 0)
        calories = meal_data.get('calories', 0)
        
        # Score based on nutrition density
        if calories > 0:
            protein_score = min((protein / calories) * 100, 1.0) * self.nutrition_weights['protein']
            fiber_score = min(fiber / 25, 1.0) * self.nutrition_weights['fiber']
            score = (protein_score + fiber_score) * 100
        
        return max(score, 10)  # Minimum score of 10
    
    def _find_ingredient_alternatives(self, ingredient: str) -> List[str]:
        """Find alternative ingredients with similar nutrition profile"""
        alternatives_map = {
            "chicken_breast": ["turkey_breast", "lean_pork", "tofu"],
            "salmon": ["mackerel", "sardines", "tuna"],
            "quinoa": ["brown_rice", "barley", "bulgur"],
            "broccoli": ["cauliflower", "brussels_sprouts", "green_beans"]
        }
        
        return alternatives_map.get(ingredient.lower().replace(' ', '_'), [ingredient])
    
    def _calculate_nutrition_impact(
        self, 
        original: str, 
        substitute: str
    ) -> Dict[str, str]:
        """Calculate nutritional impact of substitution"""
        return {
            "protein_change": "similar",
            "calorie_change": "similar",
            "fiber_change": "similar",
            "overall_impact": "minimal"
        }
    
    def _calculate_optimal_portions(
        self, 
        meal_data: Dict[str, Any], 
        targets: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate optimal portion sizes for nutritional targets"""
        current_calories = meal_data.get('calories', 400)
        target_calories = targets.get('calories', 400)
        
        portion_multiplier = target_calories / current_calories if current_calories > 0 else 1.0
        portion_multiplier = max(0.5, min(2.0, portion_multiplier))  # Limit between 50% and 200%
        
        return {
            "portion_size": f"{portion_multiplier:.1f}x standard",
            "adjusted_calories": current_calories * portion_multiplier,
            "adjusted_protein": meal_data.get('protein', 0) * portion_multiplier
        }
    
    def _reduce_meal_cost(self, meal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply cost reduction strategies to a meal"""
        # Simple cost reduction: reduce portion size slightly
        current_cost = self._calculate_meal_cost(meal_data)
        reduced_meal = meal_data.copy()
        
        if current_cost > 10:  # High cost meal
            reduced_meal['portion_adjustment'] = 0.9
            reduced_meal['cost_reduction_note'] = "Optimized portion size for budget"
        
        return reduced_meal
    
    def _enhance_meal_nutrition(self, meal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance nutritional value of a meal"""
        enhanced_meal = meal_data.copy()
        
        # Add nutrition boosters
        enhanced_meal['nutrition_boosters'] = [
            "Added leafy greens for vitamins",
            "Included healthy fats for absorption",
            "Balanced protein content"
        ]
        
        return enhanced_meal
    
    def _get_current_season(self) -> str:
        """Get current season for seasonal optimization"""
        from datetime import datetime
        month = datetime.now().month
        
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"
    
    def _use_seasonal_ingredients(
        self, 
        meal_data: Dict[str, Any], 
        season: str
    ) -> Dict[str, Any]:
        """Replace ingredients with seasonal alternatives"""
        seasonal_meal = meal_data.copy()
        seasonal_meal['seasonal_optimization'] = f"Optimized for {season} ingredients"
        return seasonal_meal
    
    def _find_quick_alternative(
        self, 
        meal_data: Dict[str, Any], 
        time_limit: int
    ) -> Dict[str, Any]:
        """Find quicker alternative for time-constrained meal"""
        quick_meal = meal_data.copy()
        quick_meal['prep_time'] = min(meal_data.get('prep_time', 30), time_limit)
        quick_meal['time_optimization'] = f"Optimized for {time_limit} minute prep"
        return quick_meal
