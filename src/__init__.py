"""
AI Nutritionist - Main Package
Production-ready WhatsApp/SMS nutrition coaching SaaS
"""

__version__ = "1.0.0"
__author__ = "Owen Richards"
__email__ = "owenlrichards2000@gmail.com"

# Import core components for easy access
from .config import get_settings, validate_environment
from .models import UserProfile, MealPlan, Recipe

__all__ = [
    '__version__',
    'get_settings',
    'validate_environment', 
    'UserProfile',
    'MealPlan',
    'Recipe',
]
