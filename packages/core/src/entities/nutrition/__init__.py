"""Nutrition domain entities.

Core nutrition entities for meal planning, recipes, and nutritional data.
"""

from .meal import Meal, MealPlan, DayPlan
from .recipe import Recipe, Ingredient, NutritionInfo
from .goals import NutritionTargets, DietaryGoal
from .tracking import FoodEntry, NutritionLog

__all__ = [
    "Meal",
    "MealPlan",
    "DayPlan", 
    "Recipe",
    "Ingredient",
    "NutritionInfo",
    "NutritionTargets",
    "DietaryGoal",
    "FoodEntry",
    "NutritionLog",
]
