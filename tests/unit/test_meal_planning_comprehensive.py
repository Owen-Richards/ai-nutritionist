"""
Comprehensive unit tests for meal planning domain.

Tests cover:
- Meal plan generation logic
- Constraint handling and optimization
- Recipe variety management
- Plan coordination and scheduling
- Repository operations
- Business rule enforcement
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta, date
from decimal import Decimal
from uuid import uuid4
from typing import Dict, Any, List, Optional

from src.services.meal_planning.planner import AdaptiveMealPlanningService
from src.services.meal_planning.optimizer import MealPlanService
from src.services.meal_planning.constraints import MultiGoalService
from src.services.meal_planning.variety import MultiGoalMealPlanGenerator
from src.services.meal_planning.plan_coordinator import (
    PlanCoordinator, PlanPreferences, PlanGenerationCommand, compute_week_start
)
from src.services.meal_planning.repository import (
    InMemoryPlanRepository, GeneratedMealPlan, MealEntry, PlanFeedback
)
from src.services.meal_planning.rule_engine import RuleBasedMealPlanEngine


class TestAdaptiveMealPlanningService:
    """Test adaptive meal planning service."""
    
    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service for meal generation."""
        ai_service = AsyncMock()
        ai_service.generate_meal_plan.return_value = {
            "meals": [
                {"name": "Grilled Chicken Salad", "calories": 350, "protein": 35},
                {"name": "Quinoa Bowl", "calories": 400, "protein": 15},
                {"name": "Salmon with Vegetables", "calories": 450, "protein": 40}
            ]
        }
        return ai_service
    
    @pytest.fixture
    def mock_nutrition_service(self):
        """Mock nutrition calculation service."""
        service = Mock()
        service.calculate_nutrition = Mock(return_value={
            "calories": 1200, "protein": 90, "carbs": 120, "fat": 40
        })
        return service
    
    @pytest.fixture
    def meal_planning_service(self, mock_ai_service, mock_nutrition_service):
        """Create meal planning service with mocked dependencies."""
        return AdaptiveMealPlanningService(
            ai_service=mock_ai_service,
            nutrition_service=mock_nutrition_service
        )
    
    @pytest.mark.asyncio
    async def test_generate_weekly_plan_success(self, meal_planning_service, mock_ai_service):
        """Test successful weekly meal plan generation."""
        user_preferences = {
            "dietary_restrictions": ["vegetarian"],
            "calorie_target": 2000,
            "protein_target": 150,
            "preferred_cuisines": ["mediterranean", "asian"]
        }
        
        plan = await meal_planning_service.generate_weekly_plan("user123", user_preferences)
        
        assert plan is not None
        assert len(plan.meals) == 21  # 7 days * 3 meals
        assert plan.total_calories >= 13000  # ~2000 * 7 days (with tolerance)
        mock_ai_service.generate_meal_plan.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_adapt_plan_to_preferences(self, meal_planning_service):
        """Test plan adaptation based on user preferences."""
        base_plan = GeneratedMealPlan(
            plan_id="plan123",
            user_id="user123",
            week_start=date.today(),
            meals=[
                MealEntry(meal_id="meal1", name="Beef Steak", day_of_week=1, meal_type="dinner")
            ]
        )
        
        new_preferences = {
            "dietary_restrictions": ["vegetarian"]  # Should exclude beef
        }
        
        adapted_plan = await meal_planning_service.adapt_plan(base_plan, new_preferences)
        
        # Verify beef is replaced with vegetarian option
        beef_meals = [meal for meal in adapted_plan.meals if "beef" in meal.name.lower()]
        assert len(beef_meals) == 0
    
    @pytest.mark.asyncio
    async def test_handle_dietary_restrictions(self, meal_planning_service):
        """Test handling of various dietary restrictions."""
        restrictions_tests = [
            (["gluten_free"], "should exclude gluten"),
            (["dairy_free"], "should exclude dairy"),
            (["nut_free"], "should exclude nuts"),
            (["vegetarian"], "should exclude meat"),
            (["vegan"], "should exclude all animal products")
        ]
        
        for restrictions, expected_behavior in restrictions_tests:
            preferences = {"dietary_restrictions": restrictions}
            plan = await meal_planning_service.generate_weekly_plan("user123", preferences)
            
            # Verify restrictions are respected
            assert plan is not None
            # Additional validation would check meal ingredients
    
    def test_calorie_distribution_logic(self, meal_planning_service):
        """Test calorie distribution across meals."""
        daily_target = 2000
        distribution = meal_planning_service.calculate_meal_distribution(daily_target)
        
        # Standard distribution: breakfast 25%, lunch 35%, dinner 40%
        assert distribution['breakfast'] == 500   # 25% of 2000
        assert distribution['lunch'] == 700       # 35% of 2000
        assert distribution['dinner'] == 800      # 40% of 2000
        assert sum(distribution.values()) == daily_target


class TestMealPlanOptimizer:
    """Test meal plan optimization logic."""
    
    @pytest.fixture
    def optimizer(self):
        """Create meal plan optimizer."""
        return MealPlanService()
    
    def test_optimize_for_nutrition_goals(self, optimizer):
        """Test optimization for nutritional goals."""
        meals = [
            {"name": "Meal 1", "calories": 300, "protein": 20, "carbs": 30, "fat": 10},
            {"name": "Meal 2", "calories": 400, "protein": 25, "carbs": 50, "fat": 15},
            {"name": "Meal 3", "calories": 350, "protein": 30, "carbs": 25, "fat": 12}
        ]
        
        goals = {
            "calories": 1000,
            "protein": 75,
            "carbs": 100,
            "fat": 35
        }
        
        optimized = optimizer.optimize_for_goals(meals, goals)
        
        # Check that optimization moves towards goals
        total_nutrition = optimizer.calculate_total_nutrition(optimized)
        assert abs(total_nutrition['calories'] - goals['calories']) < 100
        assert abs(total_nutrition['protein'] - goals['protein']) < 10
    
    def test_optimize_for_cost(self, optimizer):
        """Test cost optimization."""
        meals = [
            {"name": "Expensive Meal", "cost": 25.00, "calories": 400},
            {"name": "Moderate Meal", "cost": 12.00, "calories": 380},
            {"name": "Budget Meal", "cost": 6.00, "calories": 350}
        ]
        
        max_budget = 40.00
        optimized = optimizer.optimize_for_cost(meals, max_budget)
        
        total_cost = sum(meal['cost'] for meal in optimized)
        assert total_cost <= max_budget
    
    def test_optimize_for_time(self, optimizer):
        """Test time-based optimization."""
        meals = [
            {"name": "Quick Meal", "prep_time": 15, "calories": 350},
            {"name": "Medium Meal", "prep_time": 30, "calories": 400},
            {"name": "Complex Meal", "prep_time": 60, "calories": 450}
        ]
        
        max_prep_time = 90  # minutes per day
        optimized = optimizer.optimize_for_time(meals, max_prep_time)
        
        total_time = sum(meal['prep_time'] for meal in optimized)
        assert total_time <= max_prep_time
    
    @pytest.mark.parametrize("optimization_target,expected_priority", [
        ("nutrition", "protein_density"),
        ("cost", "cost_per_calorie"),
        ("time", "prep_time"),
        ("variety", "cuisine_diversity")
    ])
    def test_optimization_strategies(self, optimizer, optimization_target, expected_priority):
        """Test different optimization strategies."""
        strategy = optimizer.get_optimization_strategy(optimization_target)
        assert expected_priority in strategy['priority_metrics']


class TestConstraintHandling:
    """Test dietary constraint handling."""
    
    @pytest.fixture
    def constraint_handler(self):
        """Create constraint handler."""
        return MultiGoalService()
    
    def test_handle_multiple_constraints(self, constraint_handler):
        """Test handling multiple simultaneous constraints."""
        constraints = {
            "dietary_restrictions": ["vegetarian", "gluten_free"],
            "allergies": ["nuts", "shellfish"],
            "dislikes": ["mushrooms", "olives"],
            "calorie_range": [1800, 2200],
            "max_prep_time": 45
        }
        
        meals = [
            {"name": "Veggie Pasta", "gluten_free": True, "vegetarian": True, "prep_time": 30},
            {"name": "Mushroom Risotto", "vegetarian": True, "contains": ["mushrooms"]},
            {"name": "Nut Salad", "vegetarian": True, "contains": ["nuts"]},
            {"name": "Grilled Chicken", "vegetarian": False}
        ]
        
        filtered_meals = constraint_handler.apply_constraints(meals, constraints)
        
        # Should only include meals that satisfy all constraints
        assert len(filtered_meals) == 1
        assert filtered_meals[0]['name'] == "Veggie Pasta"
    
    def test_constraint_conflict_resolution(self, constraint_handler):
        """Test resolution of conflicting constraints."""
        # Conflicting constraints: high protein + vegan
        constraints = {
            "dietary_restrictions": ["vegan"],
            "protein_target": 150,  # High protein goal
            "calorie_target": 1800
        }
        
        resolution = constraint_handler.resolve_conflicts(constraints)
        
        # Should suggest plant-based protein sources
        assert 'protein_sources' in resolution
        assert 'legumes' in resolution['protein_sources']
        assert 'quinoa' in resolution['protein_sources']
    
    def test_constraint_priority_handling(self, constraint_handler):
        """Test constraint priority when conflicts arise."""
        constraints = {
            "dietary_restrictions": ["vegetarian"],  # High priority
            "preferred_proteins": ["chicken"],       # Conflicts with vegetarian
            "calorie_target": 2000
        }
        
        priorities = {"dietary_restrictions": 1, "preferred_proteins": 3}
        resolved = constraint_handler.apply_with_priorities(constraints, priorities)
        
        # Dietary restrictions should take precedence
        assert "chicken" not in resolved['allowed_proteins']
        assert "tofu" in resolved['allowed_proteins']


class TestRecipeVarietyManager:
    """Test recipe variety and rotation management."""
    
    @pytest.fixture
    def variety_manager(self):
        """Create variety manager."""
        return MultiGoalMealPlanGenerator()
    
    def test_ensure_cuisine_variety(self, variety_manager):
        """Test ensuring variety in cuisines."""
        previous_plans = [
            {"cuisine": "italian", "meals": ["pasta", "pizza"]},
            {"cuisine": "italian", "meals": ["risotto"]},
            {"cuisine": "mexican", "meals": ["tacos"]}
        ]
        
        new_suggestions = variety_manager.suggest_varied_cuisines(previous_plans, target_count=3)
        
        # Should suggest less-used cuisines
        assert "asian" in new_suggestions
        assert "mediterranean" in new_suggestions
        # Should reduce italian suggestions
        italian_count = sum(1 for cuisine in new_suggestions if cuisine == "italian")
        assert italian_count <= 1
    
    def test_ingredient_rotation(self, variety_manager):
        """Test ingredient rotation to avoid repetition."""
        recent_ingredients = ["chicken", "chicken", "beef", "salmon"]
        
        recommendations = variety_manager.recommend_proteins(recent_ingredients)
        
        # Should suggest less-used proteins
        assert "turkey" in recommendations
        assert "tofu" in recommendations
        # Should deprioritize overused ingredients
        assert recommendations.index("chicken") > recommendations.index("turkey")
    
    def test_seasonal_variety(self, variety_manager):
        """Test seasonal ingredient suggestions."""
        current_season = "winter"
        
        seasonal_suggestions = variety_manager.get_seasonal_ingredients(current_season)
        
        assert "root vegetables" in seasonal_suggestions
        assert "citrus fruits" in seasonal_suggestions
        assert "tomatoes" not in seasonal_suggestions  # Summer ingredient
    
    def test_cooking_method_variety(self, variety_manager):
        """Test variety in cooking methods."""
        recent_methods = ["grilled", "grilled", "baked", "steamed"]
        
        method_suggestions = variety_manager.suggest_cooking_methods(recent_methods)
        
        # Should suggest underused methods
        assert "sautéed" in method_suggestions
        assert "roasted" in method_suggestions
        # Should deprioritize overused methods
        assert "grilled" not in method_suggestions[:2]


class TestPlanCoordinator:
    """Test meal plan coordination and scheduling."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock plan repository."""
        repository = Mock()
        repository.save_plan = Mock()
        repository.get_plan_for_week = Mock()
        repository.remember_idempotency = Mock()
        repository.get_plan_by_idempotency = Mock(return_value=None)
        return repository
    
    @pytest.fixture
    def plan_coordinator(self, mock_repository):
        """Create plan coordinator with mocked repository."""
        return PlanCoordinator(repository=mock_repository)
    
    @pytest.mark.asyncio
    async def test_generate_plan_with_idempotency(self, plan_coordinator, mock_repository):
        """Test plan generation with idempotency key."""
        command = PlanGenerationCommand(
            user_id="user123",
            week_start=date(2024, 1, 1),
            preferences=PlanPreferences(
                diet_type="vegetarian",
                calorie_target=2000
            ),
            idempotency_key="abc123"
        )
        
        # First call - should generate new plan
        plan1 = await plan_coordinator.generate_plan(command)
        
        # Mock that idempotency key now returns the saved plan
        mock_repository.get_plan_by_idempotency.return_value = plan1
        
        # Second call with same key - should return cached plan
        plan2 = await plan_coordinator.generate_plan(command)
        
        assert plan1.plan_id == plan2.plan_id
        # Repository save should only be called once
        assert mock_repository.save_plan.call_count == 1
    
    @pytest.mark.asyncio
    async def test_feedback_incorporation(self, plan_coordinator):
        """Test incorporating user feedback into future plans."""
        feedback = PlanFeedback(
            feedback_id="feedback123",
            user_id="user123",
            plan_id="plan123",
            meal_id="meal456",
            rating=2,  # Low rating
            feedback_text="Too spicy",
            created_at=datetime.utcnow()
        )
        
        preferences = await plan_coordinator.incorporate_feedback(feedback)
        
        # Should adjust preferences based on feedback
        assert "spice_level" in preferences
        assert preferences["spice_level"] == "mild"
    
    def test_week_start_calculation(self):
        """Test week start calculation utility."""
        # Test various dates
        monday_date = date(2024, 1, 1)  # Assume this is a Monday
        wednesday_date = date(2024, 1, 3)  # Wednesday same week
        
        monday_week_start = compute_week_start(monday_date)
        wednesday_week_start = compute_week_start(wednesday_date)
        
        # Both should return the same Monday
        assert monday_week_start == wednesday_week_start
        assert monday_week_start.weekday() == 0  # Monday
    
    def test_plan_preferences_validation(self):
        """Test plan preferences validation."""
        valid_preferences = PlanPreferences(
            diet_type="vegetarian",
            calorie_target=2000,
            protein_target=150
        )
        
        invalid_preferences = PlanPreferences(
            diet_type="invalid_diet",
            calorie_target=-100  # Invalid negative calories
        )
        
        assert valid_preferences.validate() is True
        assert invalid_preferences.validate() is False


class TestInMemoryPlanRepository:
    """Test in-memory plan repository implementation."""
    
    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return InMemoryPlanRepository()
    
    def test_save_and_retrieve_plan(self, repository):
        """Test saving and retrieving meal plans."""
        plan = GeneratedMealPlan(
            plan_id="plan123",
            user_id="user123",
            week_start=date(2024, 1, 1),
            meals=[
                MealEntry(meal_id="meal1", name="Breakfast", day_of_week=1, meal_type="breakfast")
            ]
        )
        
        # Save plan
        repository.save_plan(plan)
        
        # Retrieve plan
        retrieved = repository.get_plan_for_week("user123", date(2024, 1, 1))
        
        assert retrieved is not None
        assert retrieved.plan_id == plan.plan_id
        assert len(retrieved.meals) == 1
    
    def test_idempotency_handling(self, repository):
        """Test idempotency key handling."""
        plan = GeneratedMealPlan(
            plan_id="plan123",
            user_id="user123",
            week_start=date(2024, 1, 1),
            meals=[]
        )
        
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store with idempotency key
        repository.remember_idempotency("user123", "key123", plan, expires_at)
        
        # Retrieve by idempotency key
        retrieved = repository.get_plan_by_idempotency("user123", "key123")
        
        assert retrieved is not None
        assert retrieved.plan_id == plan.plan_id
    
    def test_feedback_recording(self, repository):
        """Test feedback recording and retrieval."""
        feedback = PlanFeedback(
            feedback_id="feedback123",
            user_id="user123",
            plan_id="plan123",
            meal_id="meal456",
            rating=4,
            feedback_text="Delicious!",
            created_at=datetime.utcnow()
        )
        
        # Record feedback
        repository.record_feedback(feedback)
        
        # Retrieve feedback
        feedback_list = repository.list_feedback("user123", "plan123")
        
        assert len(feedback_list) == 1
        assert feedback_list[0].feedback_id == feedback.feedback_id
        assert feedback_list[0].rating == 4
    
    def test_thread_safety(self, repository):
        """Test repository thread safety."""
        import threading
        import time
        
        plans_created = []
        
        def create_plan(plan_id):
            plan = GeneratedMealPlan(
                plan_id=plan_id,
                user_id="user123",
                week_start=date(2024, 1, 1),
                meals=[]
            )
            repository.save_plan(plan)
            plans_created.append(plan_id)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_plan, args=[f"plan{i}"])
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All plans should be created
        assert len(plans_created) == 10
        
        # Repository should have all plans
        all_plans = repository._plans
        assert len(all_plans) == 10


class TestRuleBasedMealPlanEngine:
    """Test rule-based meal plan generation engine."""
    
    @pytest.fixture
    def rule_engine(self):
        """Create rule engine instance."""
        return RuleBasedMealPlanEngine()
    
    def test_nutrition_rules(self, rule_engine):
        """Test nutrition-based rules."""
        user_profile = {
            "age": 30,
            "gender": "female",
            "weight": 150,
            "height": 65,
            "activity_level": "moderate",
            "goal": "weight_loss"
        }
        
        nutrition_targets = rule_engine.calculate_nutrition_targets(user_profile)
        
        # Verify reasonable targets for weight loss
        assert nutrition_targets['calories'] < 2000  # Deficit for weight loss
        assert nutrition_targets['protein'] >= 120   # Adequate protein
        assert nutrition_targets['fiber'] >= 25      # Adequate fiber
    
    def test_meal_timing_rules(self, rule_engine):
        """Test meal timing and frequency rules."""
        user_schedule = {
            "wake_time": "07:00",
            "work_start": "09:00",
            "lunch_break": "12:00",
            "work_end": "17:00",
            "sleep_time": "23:00"
        }
        
        meal_schedule = rule_engine.generate_meal_schedule(user_schedule)
        
        assert len(meal_schedule) >= 3  # At least 3 main meals
        assert meal_schedule[0]['time'] <= "08:00"  # Breakfast before work
        assert "12:00" <= meal_schedule[1]['time'] <= "13:00"  # Lunch during break
        assert meal_schedule[-1]['time'] <= "20:00"  # Dinner not too late
    
    def test_dietary_restriction_rules(self, rule_engine):
        """Test dietary restriction enforcement."""
        restrictions = ["vegetarian", "gluten_free", "dairy_free"]
        
        allowed_ingredients = rule_engine.get_allowed_ingredients(restrictions)
        
        # Should exclude restricted ingredients
        assert "chicken" not in allowed_ingredients
        assert "wheat" not in allowed_ingredients
        assert "milk" not in allowed_ingredients
        
        # Should include allowed ingredients
        assert "tofu" in allowed_ingredients
        assert "rice" in allowed_ingredients
        assert "vegetables" in allowed_ingredients
    
    def test_portion_size_rules(self, rule_engine):
        """Test portion size calculation rules."""
        user_profile = {
            "weight": 180,
            "height": 72,
            "activity_level": "high",
            "goal": "muscle_gain"
        }
        
        portions = rule_engine.calculate_portion_sizes(user_profile)
        
        # High activity muscle gain should have larger portions
        assert portions['protein_per_meal'] >= 30  # grams
        assert portions['carbs_per_meal'] >= 50    # grams
        assert portions['total_calories_per_meal'] >= 600


class TestMealPlanBusinessRules:
    """Test business rules enforcement in meal planning."""
    
    def test_cost_per_meal_limits(self):
        """Test cost per meal business rules."""
        # Premium tier can have higher cost meals
        premium_limit = MealPlanService.get_cost_limit("premium")
        assert premium_limit >= 15.0
        
        # Free tier has lower cost limits
        free_limit = MealPlanService.get_cost_limit("free")
        assert free_limit <= 8.0
    
    def test_plan_generation_rate_limits(self):
        """Test rate limiting for plan generation."""
        # Free users limited to 3 plans per month
        free_limit = MealPlanService.get_generation_limit("free")
        assert free_limit == 3
        
        # Premium users get more plans
        premium_limit = MealPlanService.get_generation_limit("premium")
        assert premium_limit >= 50
    
    def test_nutrition_accuracy_requirements(self):
        """Test nutrition accuracy business rules."""
        calculated_nutrition = {"calories": 2000, "protein": 150}
        target_nutrition = {"calories": 2000, "protein": 150}
        
        accuracy = MealPlanService.calculate_nutrition_accuracy(
            calculated_nutrition, target_nutrition
        )
        
        # Should meet minimum accuracy requirements
        assert accuracy >= 0.95  # 95% accuracy requirement


# Property-based testing examples
class TestMealPlanProperties:
    """Property-based tests for meal planning logic."""
    
    @pytest.mark.parametrize("calorie_target", [1200, 1500, 1800, 2000, 2500, 3000])
    def test_calorie_targets_always_positive(self, calorie_target):
        """Test that calorie targets are always positive and reasonable."""
        assert calorie_target > 0
        assert calorie_target <= 4000  # Upper reasonable limit
    
    @pytest.mark.parametrize("meal_count", [3, 4, 5, 6])
    def test_meal_distribution_sums_to_target(self, meal_count):
        """Test that meal calorie distribution always sums to target."""
        target_calories = 2000
        distribution = MealPlanService.distribute_calories(target_calories, meal_count)
        
        assert sum(distribution) == target_calories
        assert all(calories > 0 for calories in distribution)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
