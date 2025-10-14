"""
AI_CONTEXT
Purpose: AI-powered meal planning with nutritional optimization and dietary constraint handling
Public API: PlanCoordinator, MealPlanPipeline, MealPlanningService, MealOptimizer, 
            InMemoryPlanRepository, RuleBasedMealPlanEngine
Internal: AdaptiveMealPlanningService, MultiGoalService (internal optimization)
Contracts: Async operations for AWS Bedrock integration, repository pattern for persistence
Side Effects: AWS Bedrock API calls, DynamoDB writes, personalization service interaction
Stability: public - PlanCoordinator and MealPlanPipeline are stable public APIs
Usage Example:
    from services.meal_planning import PlanCoordinator, InMemoryPlanRepository, RuleBasedMealPlanEngine
    
    coordinator = PlanCoordinator(repository, engine)
    plan = await coordinator.create_plan(
        user_id="user123",
        preferences={"budget": 75, "dietary_restrictions": ["vegetarian"]}
    )
"""

"""
Meal Planning Domain Package

This package contains all meal planning related services organized by responsibility:
- planner.py: Adaptive meal planning (AdaptiveMealPlanningService)
- optimizer.py: Meal plan optimization (MealPlanService)
- constraints.py: Multi-goal constraints (MultiGoalService)
- variety.py: Recipe variety and generation (MultiGoalMealPlanGenerator)
- plan_coordinator.py: Main orchestration layer (PlanCoordinator)
- pipeline.py: End-to-end meal planning pipeline (MealPlanPipeline)
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
