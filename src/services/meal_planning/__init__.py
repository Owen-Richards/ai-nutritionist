"""
Meal Planning Domain Package

This package contains all meal planning related services organized by responsibility:
- planner.py: Core meal plan generation logic
- optimizer.py: Cost and nutrition optimization
- constraints.py: Dietary restrictions and health condition handling
- variety.py: Meal variety and rotation enforcement
"""

from .planner import MealPlanningService
from .optimizer import MealOptimizer
from .constraints import DietaryConstraintHandler
from .variety import VarietyManager

__all__ = [
    'MealPlanningService',
    'MealOptimizer', 
    'DietaryConstraintHandler',
    'VarietyManager'
]
