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
from .plan_coordinator import (
    PlanCoordinator,
    PlanPreferences,
    PlanGenerationCommand,
    PlanFeedbackCommand,
    compute_week_start,
)
from .repository import InMemoryPlanRepository
from .rule_engine import RuleBasedMealPlanEngine
from .data_store import InMemoryPlanDataStore, PlanDataStore, UserPreferenceRecord, PantryItemRecord, UserRecord
from .ml_logging import FeatureLogger
from .pipeline import MealPlanPipeline

__all__ = [
    'MealPlanningService',
    'MealOptimizer', 
    'DietaryConstraintHandler',
    'VarietyManager',
    'PlanCoordinator',
    'PlanPreferences',
    'PlanGenerationCommand',
    'PlanFeedbackCommand',
    'compute_week_start',
    'InMemoryPlanRepository',
    'RuleBasedMealPlanEngine',
    'MealPlanPipeline',
    'PlanDataStore',
    'InMemoryPlanDataStore',
    'UserPreferenceRecord',
    'PantryItemRecord',
    'UserRecord',
    'FeatureLogger',
]
