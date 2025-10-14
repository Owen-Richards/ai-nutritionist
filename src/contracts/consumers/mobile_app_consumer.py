"""
Mobile App Consumer Contracts

Defines contracts for the Mobile App as a consumer of various services.
"""

from typing import List, Dict, Any
from ..core.consumer_tester import ConsumerTester


class MobileAppConsumer:
    """Mobile App as a contract consumer."""
    
    def __init__(self, consumer_tester: ConsumerTester):
        self.consumer_tester = consumer_tester
        self.consumer_name = "mobile-app"
    
    def define_nutrition_service_expectations(self) -> List[Dict[str, Any]]:
        """Define expectations from Nutrition Service."""
        expectations = []
        
        # Food Analysis Expectation
        analysis_expectation = self.consumer_tester.define_rest_expectation(
            provider_name="nutrition-service",
            description="Analyze nutrition for logged food items",
            method="POST",
            path="/api/v1/nutrition/analyze",
            request_body={
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "food_items": [
                    {
                        "name": "banana",
                        "quantity": 120
                    }
                ],
                "analysis_type": "basic"
            },
            request_headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer mobile_app_token"
            },
            response_status=200,
            response_body={
                "analysis_id": "analysis_123",
                "total_nutrition": {
                    "calories": 105,
                    "macros": {
                        "protein": 1.3,
                        "carbs": 27.0,
                        "fat": 0.3
                    }
                },
                "item_breakdown": [
                    {
                        "name": "banana",
                        "nutrition": {
                            "calories": 105,
                            "macros": {
                                "protein": 1.3,
                                "carbs": 27.0,
                                "fat": 0.3
                            }
                        }
                    }
                ]
            }
        )
        expectations.append(analysis_expectation)
        
        # Food Tracking Expectation
        tracking_expectation = self.consumer_tester.define_rest_expectation(
            provider_name="nutrition-service",
            description="Track food intake for user",
            method="POST",
            path="/api/v1/nutrition/track",
            request_body={
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "meal_type": "lunch",
                "food_items": [
                    {
                        "name": "grilled chicken",
                        "quantity": 150,
                        "unit": "grams"
                    }
                ],
                "timestamp": "2024-01-15T12:30:00Z"
            },
            response_status=201,
            response_body={
                "tracking_id": "track_456",
                "status": "recorded",
                "nutrition_summary": {
                    "calories": 231,
                    "macros": {
                        "protein": 43.5,
                        "carbs": 0,
                        "fat": 5.0
                    }
                }
            }
        )
        expectations.append(tracking_expectation)
        
        return expectations
    
    def define_meal_planning_service_expectations(self) -> List[Dict[str, Any]]:
        """Define expectations from Meal Planning Service."""
        expectations = []
        
        # Meal Plan Generation Expectation
        plan_expectation = self.consumer_tester.define_rest_expectation(
            provider_name="meal-planning-service",
            description="Generate weekly meal plan for user",
            method="POST",
            path="/api/v1/meal-plans/generate",
            request_body={
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "plan_duration": {
                    "days": 7
                },
                "preferences": {
                    "dietary_restrictions": ["gluten_free"],
                    "cooking_time_limit": 45
                },
                "nutrition_goals": {
                    "daily_calories": 1800
                }
            },
            response_status=201,
            response_body={
                "plan_id": "plan_789",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "duration": {
                    "days": 7,
                    "start_date": "2024-01-15",
                    "end_date": "2024-01-21"
                },
                "daily_plans": [
                    {
                        "date": "2024-01-15",
                        "meals": [
                            {
                                "meal_type": "breakfast",
                                "recipe": {
                                    "id": "recipe_gluten_free_001",
                                    "name": "Gluten-Free Pancakes",
                                    "nutrition": {
                                        "calories": 320,
                                        "macros": {
                                            "protein": 12,
                                            "carbs": 45,
                                            "fat": 10
                                        }
                                    }
                                }
                            }
                        ]
                    }
                ],
                "summary": {
                    "avg_daily_nutrition": {
                        "calories": 1800,
                        "macros": {
                            "protein": 135,
                            "carbs": 225,
                            "fat": 60
                        }
                    },
                    "total_recipes": 21,
                    "adherence_score": 92
                }
            }
        )
        expectations.append(plan_expectation)
        
        return expectations
    
    def define_messaging_service_expectations(self) -> List[Dict[str, Any]]:
        """Define expectations from Messaging Service.""" 
        expectations = []
        
        # Send Notification Expectation
        notification_expectation = self.consumer_tester.define_rest_expectation(
            provider_name="messaging-service",
            description="Send push notification to user",
            method="POST",
            path="/api/v1/messages/send",
            request_body={
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": {
                    "content": "Time to log your lunch! 🍽️",
                    "type": "text"
                },
                "channel": "push",
                "priority": "normal"
            },
            response_status=201,
            response_body={
                "message_id": "msg_123",
                "status": "sent",
                "channel": "push",
                "timestamp": "2024-01-15T12:00:00Z"
            }
        )
        expectations.append(notification_expectation)
        
        return expectations
    
    def define_all_expectations(self) -> List[Dict[str, Any]]:
        """Define all consumer expectations."""
        all_expectations = []
        
        all_expectations.extend(self.define_nutrition_service_expectations())
        all_expectations.extend(self.define_meal_planning_service_expectations())
        all_expectations.extend(self.define_messaging_service_expectations())
        
        return all_expectations
    
    def generate_consumer_contracts(self) -> Dict[str, str]:
        """Generate consumer-driven contracts for all providers."""
        contracts = {}
        
        # Define all expectations
        self.define_all_expectations()
        
        # Generate contracts for each provider
        providers = ["nutrition-service", "meal-planning-service", "messaging-service"]
        
        for provider in providers:
            try:
                contract = self.consumer_tester.generate_contract_from_expectations(provider)
                contracts[provider] = contract
            except Exception as e:
                print(f"Failed to generate contract for {provider}: {e}")
        
        return contracts
    
    def validate_expectations(self) -> Dict[str, Any]:
        """Validate all consumer expectations."""
        validation_results = {}
        
        providers = ["nutrition-service", "meal-planning-service", "messaging-service"]
        
        for provider in providers:
            try:
                result = self.consumer_tester.validate_consumer_expectations(provider)
                validation_results[provider] = result
            except Exception as e:
                validation_results[provider] = {
                    "valid": False,
                    "error": str(e)
                }
        
        return validation_results
