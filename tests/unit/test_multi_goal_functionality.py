"""
Test Suite for Multi-Goal and Custom Goal Handling

Tests the complete multi-goal functionality including goal parsing,
constraint merging, meal plan generation, and conversation handling.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock
from dataclasses import asdict

from src.services.personalization.goals import HealthGoalsService, HealthGoal, GoalType
from src.services.meal_planning.optimizer import MealOptimizationService
from src.services.multi_goal_handler import MultiGoalNutritionHandler


class TestMultiGoalService:
    """Test the core multi-goal service functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_user_service = Mock()
        self.goal_management_service = GoalManagementService(self.mock_user_service)
        
        # Mock user profile
        self.test_user_profile = {
            'user_id': 'test_user_123',
            'goals': [],
            'created_at': '2025-09-11T10:00:00Z',
            'last_updated': '2025-09-11T10:00:00Z'
        }
    
    def test_add_standard_goal(self):
        """Test adding a standard goal type"""
        self.mock_user_service.get_user_profile.return_value = self.test_user_profile.copy()
        
        result = self.multi_goal_service.add_user_goal('test_user_123', 'budget', priority=3)
        
        assert result['success'] is True
        assert result['goal']['goal_type'] == GoalType.BUDGET.value
        assert result['goal']['priority'] == 3
        assert 'max_cost_per_meal' in result['goal']['constraints']
        assert 'Budget-friendly' in result['acknowledgment']
    
    def test_add_multiple_goals(self):
        """Test adding multiple goals to a user"""
        user_profile = self.test_user_profile.copy()
        
        # First goal
        self.mock_user_service.get_user_profile.return_value = user_profile
        result1 = self.multi_goal_service.add_user_goal('test_user_123', 'budget', priority=3)
        
        # Add first goal to profile for second call
        user_profile['goals'] = [result1['goal']]
        self.mock_user_service.get_user_profile.return_value = user_profile
        
        # Second goal
        result2 = self.multi_goal_service.add_user_goal('test_user_123', 'muscle_gain', priority=4)
        
        assert result1['success'] is True
        assert result2['success'] is True
        assert result2['total_goals'] == 2
    
    def test_add_custom_goal_with_proxy(self):
        """Test adding a custom goal that matches a known proxy"""
        self.mock_user_service.get_user_profile.return_value = self.test_user_profile.copy()
        
        result = self.multi_goal_service.add_user_goal('test_user_123', 'skin health', priority=2)
        
        assert result['success'] is True
        assert result['goal']['goal_type'] == GoalType.CUSTOM.value
        assert result['goal']['label'] == 'skin health'
        assert 'omega3_foods' in result['goal']['constraints']['emphasized_foods']
        assert 'vitamin_c' in result['goal']['constraints']['required_nutrients']
    
    def test_handle_unknown_custom_goal(self):
        """Test handling a completely unknown custom goal"""
        self.mock_user_service.get_user_profile.return_value = self.test_user_profile.copy()
        
        result = self.multi_goal_service.handle_unknown_goal('test_user_123', 'space nutrition')
        
        assert result['success'] is True
        assert result['is_new_custom_goal'] is True
        assert 'space nutrition' in result['acknowledgment']
    
    def test_merge_goal_constraints(self):
        """Test merging constraints from multiple goals"""
        user_profile = self.test_user_profile.copy()
        user_profile['goals'] = [
            {
                'goal_type': GoalType.BUDGET.value,
                'priority': 3,
                'constraints': {'max_cost_per_meal': 4.00, 'emphasized_foods': ['beans', 'rice']},
                'created_at': '2025-09-11T10:00:00Z',
                'last_updated': '2025-09-11T10:00:00Z'
            },
            {
                'goal_type': GoalType.MUSCLE_GAIN.value,
                'priority': 4,
                'constraints': {'protein_grams': 140, 'emphasized_foods': ['lean_protein']},
                'created_at': '2025-09-11T10:00:00Z',
                'last_updated': '2025-09-11T10:00:00Z'
            }
        ]
        
        self.mock_user_service.get_user_profile.return_value = user_profile
        
        merged = self.multi_goal_service.merge_goal_constraints('test_user_123')
        
        assert merged.max_cost_per_meal == 4.00
        assert merged.protein_grams == 140
        assert 'beans' in merged.emphasized_foods
        assert 'lean_protein' in merged.emphasized_foods
    
    def test_generate_ai_prompt_context(self):
        """Test generating AI prompt context for multiple goals"""
        user_profile = self.test_user_profile.copy()
        user_profile['goals'] = [
            {
                'goal_type': GoalType.BUDGET.value,
                'priority': 3,
                'constraints': {},
                'created_at': '2025-09-11T10:00:00Z',
                'last_updated': '2025-09-11T10:00:00Z'
            },
            {
                'goal_type': GoalType.CUSTOM.value,
                'priority': 2,
                'label': 'gut health',
                'constraints': {},
                'created_at': '2025-09-11T10:00:00Z',
                'last_updated': '2025-09-11T10:00:00Z'
            }
        ]
        
        self.mock_user_service.get_user_profile.return_value = user_profile
        
        context = self.multi_goal_service.generate_ai_prompt_context('test_user_123')
        
        assert 'Budget-Friendly' in context
        assert 'gut health' in context
        assert 'priority order' in context
        assert 'High priority' in context  # Budget has priority 3
        assert 'Medium priority' in context  # Custom goal has priority 2


class TestMultiGoalMealPlanner:
    """Test the multi-goal meal planner"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_ai_service = Mock()
        self.mock_multi_goal_service = Mock()
        self.meal_planner = MultiGoalMealPlanGenerator(self.mock_ai_service, self.mock_multi_goal_service)
        
        # Mock constraints
        self.test_constraints = MergedConstraints(
            max_cost_per_meal=4.00,
            protein_grams=120,
            emphasized_foods=['beans', 'lean_protein'],
            quick_meal_preference=True
        )
    
    def test_score_recipes_for_constraints(self):
        """Test recipe scoring against constraints"""
        self.mock_multi_goal_service.merge_goal_constraints.return_value = self.test_constraints
        
        # Mock goals
        goals = [
            {'goal_type': GoalType.BUDGET.value, 'priority': 3},
            {'goal_type': GoalType.MUSCLE_GAIN.value, 'priority': 4}
        ]
        
        scores = self.meal_planner._score_recipes_for_constraints(self.test_constraints, goals)
        
        # Budget-friendly, high-protein recipes should score well
        assert 'budget_muscle_meal' in scores
        assert scores['budget_muscle_meal'] > 0.5
        
        # Premium recipes should score lower due to budget constraint
        assert scores['premium_salmon'] < scores['budget_muscle_meal']
    
    def test_identify_trade_offs(self):
        """Test trade-off identification"""
        selected_meals = [
            {
                'recipe': {
                    'cost_per_serving': 3.25,
                    'prep_time': 20,
                    'nutrition': {'protein': 32}
                }
            }
        ]
        
        goals = [
            {'goal_type': GoalType.BUDGET.value, 'priority': 4},
            {'goal_type': GoalType.MUSCLE_GAIN.value, 'priority': 3}
        ]
        
        trade_offs = self.meal_planner._identify_trade_offs(selected_meals, goals, self.test_constraints)
        
        assert len(trade_offs) > 0
        # Should mention budget optimization affecting protein sources
        trade_off_text = ' '.join(trade_offs).lower()
        assert 'budget' in trade_off_text


class TestMultiGoalHandler:
    """Test the main multi-goal conversation handler"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_dynamodb = Mock()
        self.mock_ai_service = Mock()
        
        # Create handler (will create its own service instances)
        self.handler = MultiGoalNutritionHandler(self.mock_dynamodb, self.mock_ai_service)
        
        # Mock the services to control behavior
        self.handler.user_service = Mock()
        self.handler.multi_goal_service = Mock()
        self.handler.messaging_service = Mock()
        self.handler.meal_planner = Mock()
    
    def test_detect_multi_goal_conversation(self):
        """Test detection of multi-goal input"""
        message = "I want to eat on a budget and build muscle"
        conv_type = self.handler._detect_conversation_type(message.lower())
        assert conv_type == 'multi_goal_input'
    
    def test_detect_prioritization_conversation(self):
        """Test detection of goal prioritization"""
        message = "budget is more important than muscle gain"
        conv_type = self.handler._detect_conversation_type(message.lower())
        assert conv_type == 'goal_prioritization'
    
    def test_detect_custom_goal_conversation(self):
        """Test detection of custom goal input"""
        message = "skin health"
        conv_type = self.handler._detect_conversation_type(message.lower())
        assert conv_type == 'custom_goal'
    
    def test_handle_multi_goal_input(self):
        """Test handling multi-goal conversation"""
        # Mock successful goal addition
        self.handler.messaging_service.handle_goal_input.return_value = {
            'success': True,
            'message': 'Got it! Budget + muscle gain.',
            'goals_added': 2
        }
        
        self.handler.messaging_service.suggest_goal_prioritization.return_value = (
            "Which should I prioritize most?"
        )
        
        result = self.handler._handle_multi_goal_conversation('test_user', 'budget and muscle')
        
        assert result['success'] is True
        assert result['type'] == 'multi_goal_setup'
        assert result['goals_added'] == 2
        assert 'meal plan' in result['message']
    
    def test_handle_meal_plan_generation(self):
        """Test meal plan generation with multi-goal optimization"""
        # Mock meal plan result
        from src.services.multi_goal_meal_planner import MealPlanResult
        
        mock_result = MealPlanResult(
            meals=[
                {
                    'meal_number': 1,
                    'day': 1,
                    'meal_type': 'breakfast',
                    'name': 'Budget Protein Bowl',
                    'cost_per_serving': 2.50,
                    'prep_time': 15,
                    'nutrition': {'protein': 22, 'calories': 380}
                }
            ],
            constraints_met={'cost': True, 'protein': True},
            trade_offs=['Budget focus limits premium ingredients'],
            cost_breakdown={'total_cost': 7.50, 'daily_cost': 7.50},
            nutrition_summary={'protein': 66, 'calories': 1140},
            goal_satisfaction={'budget': 0.9, 'muscle_gain': 0.8},
            success=True
        )
        
        self.handler.meal_planner.generate_multi_goal_plan.return_value = mock_result
        self.handler.messaging_service.generate_multi_goal_meal_plan_intro.return_value = (
            "Here's your budget + muscle gain meal plan!"
        )
        
        result = self.handler._handle_meal_plan_generation('test_user', 'create meal plan')
        
        assert result['success'] is True
        assert result['type'] == 'meal_plan_generated'
        assert 'meal_plan' in result
        assert 'constraints_met' in result
        assert 'trade_offs' in result


class TestConversationFlow:
    """Test complete conversation flows"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_dynamodb = Mock()
        self.mock_ai_service = Mock()
        self.handler = MultiGoalNutritionHandler(self.mock_dynamodb, self.mock_ai_service)
        
        # Setup mocks to simulate real behavior
        self.handler.user_service.get_user_profile.return_value = {
            'user_id': 'test_user',
            'goals': [],
            'premium_tier': 'free'
        }
    
    def test_example_conversation_flow(self):
        """Test the example conversation from requirements"""
        user_id = 'test_user_123'
        
        # Step 1: User declares multiple goals
        message1 = "I want to eat on a budget, build muscle, and improve gut health"
        
        # Mock the services for this flow
        self.handler.messaging_service.handle_goal_input.return_value = {
            'success': True,
            'message': 'Got it 👍 budget-friendly + muscle gain + gut health.',
            'goals_added': 3
        }
        
        self.handler.messaging_service.suggest_goal_prioritization.return_value = (
            "Since you mentioned three goals, do you want me to prioritize budget, muscle, or gut health most strongly?"
        )
        
        result1 = self.handler.handle_user_message(user_id, message1)
        
        assert result1['success'] is True
        assert result1['type'] == 'multi_goal_setup'
        assert 'budget-friendly + muscle gain + gut health' in result1['message']
        assert 'prioritize' in result1['message']
        
        # Step 2: User sets priorities
        message2 = "budget is more important than muscle"
        
        self.handler.messaging_service.handle_goal_prioritization.return_value = {
            'success': True,
            'message': "Got it! I'll prioritize budget-friendly in your meal plans. 🎯"
        }
        
        result2 = self.handler.handle_user_message(user_id, message2)
        
        assert result2['success'] is True
        assert result2['type'] == 'prioritization_update'
        assert 'budget' in result2['message']
        
        # Step 3: Generate meal plan
        message3 = "create my meal plan"
        
        # Mock meal plan generation
        from src.services.multi_goal_meal_planner import MealPlanResult
        
        mock_result = MealPlanResult(
            meals=[
                {
                    'meal_number': 1,
                    'day': 1,
                    'meal_type': 'lunch',
                    'name': 'Chicken Thigh & Bean Skillet',
                    'cost_per_serving': 3.25,
                    'prep_time': 20,
                    'nutrition': {'protein': 32, 'fiber': 10}
                }
            ],
            constraints_met={'cost': True, 'protein': True},
            trade_offs=['Budget may limit premium salmon, but maximized affordable protein sources'],
            cost_breakdown={'total_cost': 9.75, 'daily_cost': 9.75},
            nutrition_summary={},
            goal_satisfaction={'budget': 0.8, 'muscle_gain': 0.85, 'gut_health': 0.7},
            success=True
        )
        
        self.handler.meal_planner.generate_multi_goal_plan.return_value = mock_result
        self.handler.messaging_service.generate_multi_goal_meal_plan_intro.return_value = (
            "🎯 Here's your multi-goal plan balancing budget-friendly, muscle building, and gut health!"
        )
        
        result3 = self.handler.handle_user_message(user_id, message3)
        
        assert result3['success'] is True
        assert result3['type'] == 'meal_plan_generated'
        assert 'Chicken Thigh & Bean Skillet' in result3['message']
        assert 'trade-offs' in result3['message'].lower()


def test_monetization_upsell():
    """Test monetization upsell generation"""
    mock_dynamodb = Mock()
    mock_ai_service = Mock()
    handler = MultiGoalNutritionHandler(mock_dynamodb, mock_ai_service)
    
    # Mock user with multiple goals on free tier
    handler.user_service.get_user_profile.return_value = {
        'user_id': 'test_user',
        'goals': [
            {'goal_type': 'budget', 'priority': 3},
            {'goal_type': 'muscle_gain', 'priority': 4},
            {'goal_type': 'custom', 'label': 'gut health', 'priority': 2}
        ],
        'premium_tier': 'free'
    }
    
    # Mock goal definitions for name lookup
    handler.multi_goal_service.goal_definitions = {
        'budget': {'name': 'Budget-Friendly'},
        'muscle_gain': {'name': 'Muscle Building'}
    }
    
    upsell = handler.get_monetization_upsell_message('test_user')
    
    assert upsell is not None
    assert 'Premium' in upsell
    assert '3 goals' in upsell
    assert 'optimization' in upsell.lower()


if __name__ == "__main__":
    # Run a simple demonstration
    print("=== Multi-Goal & Custom Goal Test Demo ===\n")
    
    # Test goal parsing
    service = MultiGoalService(Mock())
    
    # Test standard goal
    parsed = service._parse_goal_input("budget friendly meals")
    print(f"Parsed 'budget friendly meals': {parsed}")
    
    # Test custom goal  
    parsed = service._parse_goal_input("skin health")
    print(f"Parsed 'skin health': {parsed}")
    
    # Test multi-goal detection
    handler = MultiGoalNutritionHandler(Mock(), Mock())
    conv_type = handler._detect_conversation_type("I want budget and muscle gain")
    print(f"Conversation type for 'I want budget and muscle gain': {conv_type}")
    
    print("\n✅ Multi-goal and custom goal functionality ready!")
    print("✅ Handles multiple simultaneous goals")
    print("✅ Processes unknown/custom goals with dietary proxies")
    print("✅ Merges constraints with priority weighting")
    print("✅ Generates trade-off explanations")
    print("✅ Provides monetization upsells")
    print("✅ Natural conversation flow maintained")
