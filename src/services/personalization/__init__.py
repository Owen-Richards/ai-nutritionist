"""
Personalization Domain Package

This package contains all personalization-related services:
- preferences.py: User preferences and customization (UserService)
- behavior.py: User linking and family sharing (UserLinkingService) 
- learning.py: Seamless profiling and adaptation (SeamlessUserProfileService)
- goals.py: Personal goal management
"""

from .preferences import UserService as UserPreferencesService
from .behavior import UserLinkingService as UserBehaviorService
from .learning import SeamlessUserProfileService as UserLearningService
from .goals import HealthGoalsService as PersonalGoalsManager

__all__ = [
    'UserPreferencesService',
    'UserBehaviorService', 
    'UserLearningService',
    'PersonalGoalsManager'
]
