"""
Meal Planning Domain Package

This package contains all meal planning related services organized by responsibility:
- planner.py: Adaptive meal planning (AdaptiveMealPlanningService)
- optimizer.py: Meal plan optimization (MealPlanService)
- constraints.py: Multi-goal constraints (MultiGoalService)
- variety.py: Recipe variety and generation (MultiGoalMealPlanGenerator)
"""

from .planner import AdaptiveMealPlanningService as MealPlanningService
from .optimizer import MealPlanService as MealOptimizer
from .constraints import MultiGoalService as DietaryConstraintHandler
from .variety import MultiGoalMealPlanGenerator as VarietyManager

__all__ = [
    'MealPlanningService',
    'MealOptimizer', 
    'DietaryConstraintHandler',
    'VarietyManager'
]
