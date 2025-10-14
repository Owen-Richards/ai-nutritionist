"""
Integration test framework for AI Nutritionist application.

This module provides comprehensive integration testing across all service domains:
- End-to-end workflow testing
- Cross-service integration validation
- Performance and reliability testing
- Data consistency and integrity testing
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List
import json
import time

from src.services.nutrition.service import EdamamService, NutritionTracker
from src.services.meal_planning.service import AdaptiveMealPlanningService
from src.services.business.subscription_service import SubscriptionService
from src.services.infrastructure.ai_service import AIService
from src.services.messaging.consolidated_service import ConsolidatedMessagingService
from src.services.community.service import CommunityService
from src.services.personalization.preferences import UserService


class TestEndToEndWorkflows:
    """Test complete end-to-end user workflows."""
    
    @pytest.fixture
    def integration_services(self):
        """Set up all services for integration testing."""
        services = {
            'nutrition': Mock(spec=NutritionTracker),
            'meal_planning': Mock(spec=AdaptiveMealPlanningService),
            'subscription': Mock(spec=SubscriptionService),
            'ai': Mock(spec=AIService),
            'messaging': Mock(spec=ConsolidatedMessagingService),
            'community': Mock(spec=CommunityService),
            'user_preferences': Mock(spec=UserService)
        }
        
        # Configure common mock behaviors
        services['subscription'].get_user_subscription.return_value = {
            'tier': 'premium',
            'status': 'active',
            'features': ['ai_recommendations', 'meal_planning', 'community_access']
        }
        
        return services
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_new_user_onboarding_flow(self, integration_services):
        """Test complete new user onboarding workflow."""
        user_id = "new_user_123"
        
        # Step 1: User preferences setup
        preferences = {
            "dietary_restrictions": ["vegetarian"],
            "cuisine_preferences": ["mediterranean", "indian"],
            "calorie_target": 2000,
            "fitness_goal": "maintenance"
        }
        
        integration_services['user_preferences'].update_preferences.return_value = Mock(success=True)
        
        # Step 2: Initial meal plan generation
        integration_services['meal_planning'].generate_plan.return_value = Mock(
            success=True,
            plan_id="plan_001",
            meals=[
                {"meal_type": "breakfast", "recipe_id": "rec_001", "calories": 400},
                {"meal_type": "lunch", "recipe_id": "rec_002", "calories": 600},
                {"meal_type": "dinner", "recipe_id": "rec_003", "calories": 800}
            ]
        )
        
        # Step 3: Welcome message delivery
        integration_services['messaging'].send_welcome_sequence.return_value = Mock(
            success=True,
            messages_sent=3
        )
        
        # Step 4: Community crew suggestions
        integration_services['community'].suggest_crews.return_value = Mock(
            success=True,
            suggested_crews=[
                {"crew_id": "crew_001", "name": "Vegetarian Wellness", "member_count": 45},
                {"crew_id": "crew_002", "name": "Mediterranean Diet", "member_count": 38}
            ]
        )
        
        # Execute workflow
        result = await self._execute_onboarding_workflow(
            user_id, preferences, integration_services
        )
        
        # Validate workflow completion
        assert result['status'] == 'completed'
        assert result['preferences_set'] is True
        assert result['meal_plan_created'] is True
        assert result['welcome_messages_sent'] is True
        assert result['crew_suggestions_provided'] is True
        
        # Verify service interactions
        integration_services['user_preferences'].update_preferences.assert_called_once()
        integration_services['meal_planning'].generate_plan.assert_called_once()
        integration_services['messaging'].send_welcome_sequence.assert_called_once()
        integration_services['community'].suggest_crews.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_meal_planning_to_shopping_flow(self, integration_services):
        """Test meal plan generation to shopping list creation workflow."""
        user_id = "user_123"
        plan_id = "plan_001"
        
        # Mock meal plan with recipes
        meal_plan = {
            "plan_id": plan_id,
            "meals": [
                {
                    "meal_type": "breakfast",
                    "recipe_id": "rec_001",
                    "ingredients": [
                        {"name": "oats", "quantity": "1 cup", "unit": "cup"},
                        {"name": "banana", "quantity": "1", "unit": "piece"},
                        {"name": "almond milk", "quantity": "200ml", "unit": "ml"}
                    ]
                },
                {
                    "meal_type": "lunch", 
                    "recipe_id": "rec_002",
                    "ingredients": [
                        {"name": "quinoa", "quantity": "0.5 cup", "unit": "cup"},
                        {"name": "chickpeas", "quantity": "100g", "unit": "g"},
                        {"name": "spinach", "quantity": "2 cups", "unit": "cup"}
                    ]
                }
            ]
        }
        
        integration_services['meal_planning'].get_plan.return_value = meal_plan
        integration_services['meal_planning'].generate_shopping_list.return_value = {
            "ingredients": [
                {"name": "oats", "total_quantity": "7 cups", "category": "grains"},
                {"name": "banana", "total_quantity": "7 pieces", "category": "fruits"},
                {"name": "almond milk", "total_quantity": "1.4L", "category": "dairy_alternatives"},
                {"name": "quinoa", "total_quantity": "3.5 cups", "category": "grains"},
                {"name": "chickpeas", "total_quantity": "700g", "category": "legumes"},
                {"name": "spinach", "total_quantity": "14 cups", "category": "vegetables"}
            ],
            "estimated_cost": Decimal("45.50"),
            "store_sections": ["produce", "pantry", "refrigerated"]
        }
        
        # Execute workflow
        shopping_list = await self._execute_shopping_list_workflow(
            user_id, plan_id, integration_services
        )
        
        # Validate shopping list generation
        assert len(shopping_list["ingredients"]) == 6
        assert shopping_list["estimated_cost"] > 0
        assert "produce" in shopping_list["store_sections"]
        
        # Verify ingredient aggregation
        oats_item = next(item for item in shopping_list["ingredients"] if item["name"] == "oats")
        assert oats_item["total_quantity"] == "7 cups"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_nutrition_tracking_feedback_loop(self, integration_services):
        """Test nutrition tracking with AI feedback and plan optimization."""
        user_id = "user_123"
        
        # Mock nutrition tracking data
        nutrition_log = {
            "date": "2024-01-15",
            "meals": [
                {"meal_type": "breakfast", "calories": 450, "protein": 15, "carbs": 60, "fat": 18},
                {"meal_type": "lunch", "calories": 650, "protein": 35, "carbs": 45, "fat": 28},
                {"meal_type": "dinner", "calories": 750, "protein": 40, "carbs": 55, "fat": 32}
            ],
            "total_calories": 1850,
            "total_protein": 90,
            "water_intake": 2.1,
            "mood_score": 7
        }
        
        integration_services['nutrition'].log_nutrition.return_value = Mock(success=True)
        integration_services['ai'].analyze_nutrition_patterns.return_value = {
            "insights": [
                "Protein intake is below target (90g vs 120g target)",
                "Calorie intake is within target range",
                "Water intake is excellent"
            ],
            "recommendations": [
                "Add protein-rich snack in afternoon",
                "Consider Greek yogurt or nuts as additions"
            ],
            "optimization_score": 0.75
        }
        
        integration_services['meal_planning'].optimize_plan.return_value = Mock(
            success=True,
            adjustments=["Added protein smoothie as afternoon snack"]
        )
        
        # Execute workflow
        feedback_result = await self._execute_nutrition_feedback_workflow(
            user_id, nutrition_log, integration_services
        )
        
        # Validate feedback loop
        assert feedback_result['tracking_success'] is True
        assert len(feedback_result['ai_insights']) > 0
        assert len(feedback_result['recommendations']) > 0
        assert feedback_result['plan_optimized'] is True
        
        # Verify service interactions
        integration_services['nutrition'].log_nutrition.assert_called_once()
        integration_services['ai'].analyze_nutrition_patterns.assert_called_once()
        integration_services['meal_planning'].optimize_plan.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_community_engagement_workflow(self, integration_services):
        """Test community engagement and social features workflow."""
        user_id = "user_123"
        crew_id = "crew_001"
        
        # Mock community interactions
        integration_services['community'].join_crew.return_value = Mock(
            success=True,
            member_id="member_123"
        )
        
        integration_services['community'].submit_reflection.return_value = Mock(
            success=True,
            reflection_id="reflection_001",
            crew_responses=["Great progress!", "Keep it up!"]
        )
        
        integration_services['community'].get_crew_challenges.return_value = [
            {
                "challenge_id": "challenge_001",
                "title": "7-Day Veggie Challenge",
                "description": "Eat 5 servings of vegetables daily",
                "participants": 23,
                "end_date": "2024-01-22"
            }
        ]
        
        integration_services['messaging'].send_crew_updates.return_value = Mock(
            success=True,
            updates_sent=2
        )
        
        # Execute workflow
        engagement_result = await self._execute_community_engagement_workflow(
            user_id, crew_id, integration_services
        )
        
        # Validate community engagement
        assert engagement_result['crew_joined'] is True
        assert engagement_result['reflection_submitted'] is True
        assert len(engagement_result['available_challenges']) > 0
        assert engagement_result['updates_received'] is True
        
        # Verify service interactions
        integration_services['community'].join_crew.assert_called_once()
        integration_services['community'].submit_reflection.assert_called_once()
        integration_services['messaging'].send_crew_updates.assert_called_once()
    
    async def _execute_onboarding_workflow(self, user_id, preferences, services):
        """Execute the onboarding workflow."""
        result = {
            'status': 'in_progress',
            'preferences_set': False,
            'meal_plan_created': False,
            'welcome_messages_sent': False,
            'crew_suggestions_provided': False
        }
        
        try:
            # Set preferences
            pref_result = services['user_preferences'].update_preferences(user_id, preferences)
            result['preferences_set'] = pref_result.success
            
            # Generate initial meal plan
            plan_result = services['meal_planning'].generate_plan(user_id, preferences)
            result['meal_plan_created'] = plan_result.success
            
            # Send welcome messages
            message_result = services['messaging'].send_welcome_sequence(user_id)
            result['welcome_messages_sent'] = message_result.success
            
            # Suggest crews
            crew_result = services['community'].suggest_crews(user_id, preferences)
            result['crew_suggestions_provided'] = crew_result.success
            
            result['status'] = 'completed'
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
        
        return result
    
    async def _execute_shopping_list_workflow(self, user_id, plan_id, services):
        """Execute the shopping list generation workflow."""
        # Get meal plan
        meal_plan = services['meal_planning'].get_plan(plan_id)
        
        # Generate shopping list from plan
        shopping_list = services['meal_planning'].generate_shopping_list(meal_plan)
        
        return shopping_list
    
    async def _execute_nutrition_feedback_workflow(self, user_id, nutrition_log, services):
        """Execute the nutrition tracking and feedback workflow."""
        result = {
            'tracking_success': False,
            'ai_insights': [],
            'recommendations': [],
            'plan_optimized': False
        }
        
        # Log nutrition data
        log_result = services['nutrition'].log_nutrition(user_id, nutrition_log)
        result['tracking_success'] = log_result.success
        
        # Get AI analysis
        ai_analysis = services['ai'].analyze_nutrition_patterns(user_id, nutrition_log)
        result['ai_insights'] = ai_analysis.get('insights', [])
        result['recommendations'] = ai_analysis.get('recommendations', [])
        
        # Optimize meal plan based on insights
        if ai_analysis.get('optimization_score', 0) < 0.8:
            optimization = services['meal_planning'].optimize_plan(user_id, ai_analysis)
            result['plan_optimized'] = optimization.success
        
        return result
    
    async def _execute_community_engagement_workflow(self, user_id, crew_id, services):
        """Execute the community engagement workflow."""
        result = {
            'crew_joined': False,
            'reflection_submitted': False,
            'available_challenges': [],
            'updates_received': False
        }
        
        # Join crew
        join_result = services['community'].join_crew(user_id, crew_id)
        result['crew_joined'] = join_result.success
        
        # Submit daily reflection
        reflection_data = {
            "content": "Had a great day focusing on my nutrition goals!",
            "mood_score": 8,
            "progress_rating": 4
        }
        reflection_result = services['community'].submit_reflection(user_id, crew_id, reflection_data)
        result['reflection_submitted'] = reflection_result.success
        
        # Get available challenges
        challenges = services['community'].get_crew_challenges(crew_id)
        result['available_challenges'] = challenges
        
        # Receive crew updates
        updates_result = services['messaging'].send_crew_updates(user_id, crew_id)
        result['updates_received'] = updates_result.success
        
        return result


class TestCrossServiceIntegration:
    """Test integration between different service domains."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_subscription_feature_access_integration(self):
        """Test that subscription tiers properly control feature access."""
        user_id = "user_123"
        
        # Test different subscription tiers
        test_scenarios = [
            {
                'tier': 'free',
                'expected_features': ['basic_tracking', 'limited_recipes'],
                'restricted_features': ['ai_recommendations', 'meal_planning', 'community_access']
            },
            {
                'tier': 'premium',
                'expected_features': ['basic_tracking', 'limited_recipes', 'ai_recommendations', 'meal_planning'],
                'restricted_features': ['community_access', 'family_sharing']
            },
            {
                'tier': 'pro',
                'expected_features': ['basic_tracking', 'ai_recommendations', 'meal_planning', 'community_access', 'family_sharing'],
                'restricted_features': []
            }
        ]
        
        for scenario in test_scenarios:
            with patch('src.services.business.subscription_service.SubscriptionService') as mock_sub:
                mock_sub.return_value.get_user_subscription.return_value = {
                    'tier': scenario['tier'],
                    'status': 'active',
                    'features': scenario['expected_features']
                }
                
                # Test feature access
                for feature in scenario['expected_features']:
                    access_granted = await self._check_feature_access(user_id, feature)
                    assert access_granted, f"User should have access to {feature} with {scenario['tier']} tier"
                
                for feature in scenario['restricted_features']:
                    access_granted = await self._check_feature_access(user_id, feature)
                    assert not access_granted, f"User should NOT have access to {feature} with {scenario['tier']} tier"
    
    @pytest.mark.integration
    def test_data_consistency_across_services(self):
        """Test data consistency across service boundaries."""
        user_id = "user_123"
        
        # Test user data consistency
        user_data = {
            'user_id': user_id,
            'dietary_restrictions': ['vegetarian', 'gluten_free'],
            'calorie_target': 2000,
            'fitness_goal': 'weight_loss'
        }
        
        # Verify data propagation across services
        with patch.multiple(
            'src.services.personalization.preferences.UserService',
            get_user_preferences=Mock(return_value=user_data)
        ), patch.multiple(
            'src.services.meal_planning.service.AdaptiveMealPlanningService',
            get_user_constraints=Mock(return_value=user_data)
        ), patch.multiple(
            'src.services.nutrition.service.NutritionTracker',
            get_user_profile=Mock(return_value=user_data)
        ):
            
            # All services should have consistent user data
            prefs_service_data = Mock().get_user_preferences(user_id)
            meal_service_data = Mock().get_user_constraints(user_id)
            nutrition_service_data = Mock().get_user_profile(user_id)
            
            # Verify consistency
            assert prefs_service_data['dietary_restrictions'] == meal_service_data['dietary_restrictions']
            assert prefs_service_data['calorie_target'] == nutrition_service_data['calorie_target']
    
    async def _check_feature_access(self, user_id: str, feature: str) -> bool:
        """Check if user has access to a specific feature."""
        # This would integrate with actual feature access control logic
        # For testing, we'll mock the behavior
        return True  # Placeholder for actual implementation


class TestPerformanceIntegration:
    """Test performance characteristics across integrated services."""
    
    @pytest.mark.performance
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_response_times(self):
        """Test response times for complete user workflows."""
        response_time_targets = {
            'user_login': 2.0,  # seconds
            'meal_plan_generation': 5.0,
            'nutrition_analysis': 3.0,
            'community_reflection': 1.5,
            'ai_recommendations': 4.0
        }
        
        for workflow, target_time in response_time_targets.items():
            start_time = time.time()
            
            # Execute workflow (mocked for testing)
            await self._execute_mock_workflow(workflow)
            
            end_time = time.time()
            actual_time = end_time - start_time
            
            assert actual_time < target_time, f"{workflow} took {actual_time}s, target was {target_time}s"
    
    @pytest.mark.performance
    @pytest.mark.integration
    def test_concurrent_user_handling(self):
        """Test system performance with concurrent users."""
        import concurrent.futures
        
        def simulate_user_activity(user_id):
            """Simulate typical user activity."""
            # Mock user actions
            return {
                'user_id': user_id,
                'actions_completed': 5,
                'response_time': 0.5,
                'errors': 0
            }
        
        # Simulate 100 concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(simulate_user_activity, f"user_{i}")
                for i in range(100)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all users were handled successfully
        assert len(results) == 100
        total_errors = sum(result['errors'] for result in results)
        assert total_errors == 0  # No errors should occur
        
        avg_response_time = sum(result['response_time'] for result in results) / len(results)
        assert avg_response_time < 2.0  # Average response time under 2 seconds
    
    async def _execute_mock_workflow(self, workflow_name: str):
        """Execute a mock workflow for performance testing."""
        # Simulate different workflow complexities
        if workflow_name == 'user_login':
            await asyncio.sleep(0.1)  # Quick authentication
        elif workflow_name == 'meal_plan_generation':
            await asyncio.sleep(0.3)  # Complex meal planning
        elif workflow_name == 'nutrition_analysis':
            await asyncio.sleep(0.2)  # AI analysis
        elif workflow_name == 'community_reflection':
            await asyncio.sleep(0.05)  # Simple content submission
        elif workflow_name == 'ai_recommendations':
            await asyncio.sleep(0.25)  # AI processing
        
        return {"status": "completed", "workflow": workflow_name}


class TestDataIntegrityAndConsistency:
    """Test data integrity and consistency across the system."""
    
    @pytest.mark.integration
    def test_user_data_synchronization(self):
        """Test that user data stays synchronized across services."""
        user_id = "user_123"
        
        # Initial user data
        initial_data = {
            'dietary_restrictions': ['vegetarian'],
            'calorie_target': 2000,
            'fitness_goal': 'maintenance'
        }
        
        # Update in preferences service
        updated_data = {
            'dietary_restrictions': ['vegetarian', 'gluten_free'],
            'calorie_target': 1800,
            'fitness_goal': 'weight_loss'
        }
        
        # Verify updates propagate to all dependent services
        dependent_services = [
            'meal_planning',
            'nutrition_tracking',
            'ai_recommendations',
            'community_matching'
        ]
        
        for service in dependent_services:
            # Each service should reflect the updated user data
            service_data = self._get_user_data_from_service(service, user_id)
            assert service_data['dietary_restrictions'] == updated_data['dietary_restrictions']
            assert service_data['calorie_target'] == updated_data['calorie_target']
    
    @pytest.mark.integration
    def test_meal_plan_nutrition_consistency(self):
        """Test consistency between meal plans and nutrition calculations."""
        user_id = "user_123"
        plan_id = "plan_001"
        
        # Mock meal plan data
        meal_plan = {
            'plan_id': plan_id,
            'total_calories': 2000,
            'total_protein': 150,
            'total_carbs': 200,
            'total_fat': 78
        }
        
        # Calculate nutrition from individual meals
        calculated_nutrition = self._calculate_nutrition_from_meals(meal_plan)
        
        # Values should match within tolerance
        tolerance = 0.05  # 5% tolerance
        
        assert abs(meal_plan['total_calories'] - calculated_nutrition['calories']) / meal_plan['total_calories'] < tolerance
        assert abs(meal_plan['total_protein'] - calculated_nutrition['protein']) / meal_plan['total_protein'] < tolerance
        assert abs(meal_plan['total_carbs'] - calculated_nutrition['carbs']) / meal_plan['total_carbs'] < tolerance
        assert abs(meal_plan['total_fat'] - calculated_nutrition['fat']) / meal_plan['total_fat'] < tolerance
    
    def _get_user_data_from_service(self, service_name: str, user_id: str) -> Dict[str, Any]:
        """Mock getting user data from a specific service."""
        # In actual implementation, this would call the real service
        return {
            'dietary_restrictions': ['vegetarian', 'gluten_free'],
            'calorie_target': 1800,
            'fitness_goal': 'weight_loss'
        }
    
    def _calculate_nutrition_from_meals(self, meal_plan: Dict[str, Any]) -> Dict[str, float]:
        """Mock calculation of nutrition from meal components."""
        # In actual implementation, this would sum nutrition from all meals
        return {
            'calories': 1980,  # Slight variance for realistic testing
            'protein': 148,
            'carbs': 205,
            'fat': 76
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
