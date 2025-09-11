"""
Nutrition Domain Package

This package contains all nutrition-related services organized by responsibility:
- tracker.py: Nutrition tracking and logging (NutritionTrackingService)
- calculator.py: Nutrition calculations and analysis (EdamamService)
- goals.py: Health goals and targets management
- insights.py: AI-powered nutrition insights (ConsolidatedAINutritionService)
"""

from .tracker import NutritionTrackingService as NutritionTracker
from .calculator import EdamamService as NutritionCalculator
from .goals import HealthGoalsManager
from .insights import ConsolidatedAINutritionService as NutritionInsights

__all__ = [
    'NutritionTracker',
    'NutritionCalculator',
    'HealthGoalsManager',
    'NutritionInsights'
]
