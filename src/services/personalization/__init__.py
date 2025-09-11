"""
Personalization Domain Package

This package contains all personalization-related services:
- preferences.py: User preferences and customization
- recommendations.py: Personalized recommendations engine
- learning.py: Machine learning and adaptation
- profiles.py: User profile management
"""

from .preferences import PreferencesManager
from .recommendations import RecommendationsEngine
from .learning import LearningService
from .profiles import ProfileManager

__all__ = [
    'PreferencesManager',
    'RecommendationsEngine', 
    'LearningService',
    'ProfileManager'
]
