"""
Nutrition Domain Package

This package contains all nutrition-related services organized by responsibility:
- tracker.py: Nutrition tracking and logging
- calculator.py: Nutrition calculations and analysis
- goals.py: Health goals and targets management
- insights.py: Nutrition insights and recommendations
"""

from .tracker import NutritionTracker
from .calculator import NutritionCalculator
from .goals import HealthGoalsManager
from .insights import NutritionInsights

__all__ = [
    'NutritionTracker',
    'NutritionCalculator',
    'HealthGoalsManager',
    'NutritionInsights'
]
