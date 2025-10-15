"""
Meal Planning Service Provider Contracts
"""

from typing import List, Dict, Any
from ..core.contract_manager import ContractManager
from ..schemas.meal_planning_schemas import MealPlanningServiceSchemas


class MealPlanningServiceProvider:
    """Meal Planning Service as a contract provider."""
    
    def __init__(self, contract_manager: ContractManager):
        self.contract_manager = contract_manager
        self.service_name = "meal-planning-service"
        self.schemas = MealPlanningServiceSchemas()
    
    def create_contracts(self) -> List[str]:
        """Create all contracts for the Meal Planning Service as a provider."""
        contracts = []
        
        # Meal Plan Generation Contract
        plan_generation_contract = self.contract_manager.create_contract(
            consumer="mobile-app",
            provider=self.service_name,
            contract_type="rest",
            interactions=[
                {
                    "description": "Generate personalized meal plan",
                    "request": {
                        "method": "POST",
                        "path": "/api/v1/meal-plans/generate",
                        "headers": {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer {token}"
                        },
                        "body": {
                            "user_id": "550e8400-e29b-41d4-a716-446655440000",
                            "plan_duration": {
                                "days": 7,
                                "start_date": "2024-01-15"
                            },
                            "preferences": {
                                "dietary_restrictions": ["vegetarian"],
                                "allergies": ["nuts"],
                                "meal_complexity": "moderate",
                                "cooking_time_limit": 60
                            },
                            "nutrition_goals": {
                                "daily_calories": 2000,
                                "macro_targets": {
                                    "protein_percent": 25,
                                    "carbs_percent": 50,
                                    "fat_percent": 25
                                }
                            }
                        },
                        "schema": self.schemas.get_generate_plan_request_schema()
                    },
                    "response": {
                        "status": 201,
                        "headers": {
                            "Content-Type": "application/json",
                            "Location": "/api/v1/meal-plans/123e4567-e89b-12d3-a456-426614174000"
                        },
                        "body": {
                            "plan_id": "123e4567-e89b-12d3-a456-426614174000",
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
                                                "id": "recipe_001",
                                                "name": "Vegetarian Oatmeal Bowl",
                                                "ingredients": [
                                                    {
                                                        "name": "rolled oats",
                                                        "amount": 0.5,
                                                        "unit": "cup"
                                                    },
                                                    {
                                                        "name": "almond milk",
                                                        "amount": 1,
                                                        "unit": "cup"
                                                    }
                                                ],
                                                "instructions": [
                                                    "Combine oats and almond milk in a bowl",
                                                    "Microwave for 2 minutes",
                                                    "Top with fresh berries"
                                                ],
                                                "nutrition": {
                                                    "calories": 350,
                                                    "macros": {
                                                        "protein": 12,
                                                        "carbs": 58,
                                                        "fat": 8,
                                                        "fiber": 6
                                                    }
                                                },
                                                "difficulty": "easy",
                                                "servings": 1
                                            },
                                            "prep_time": 5,
                                            "cook_time": 3
                                        }
                                    ]
                                }
                            ],
                            "summary": {
                                "avg_daily_nutrition": {
                                    "calories": 2000,
                                    "macros": {
                                        "protein": 125,
                                        "carbs": 250,
                                        "fat": 89,
                                        "fiber": 35
                                    }
                                },
                                "total_recipes": 21,
                                "estimated_cost": {
                                    "total": 84.50,
                                    "daily_average": 12.07,
                                    "currency": "USD"
                                },
                                "adherence_score": 95
                            },
                            "created_at": "2024-01-15T10:00:00Z"
                        },
                        "schema": self.schemas.get_meal_plan_response_schema()
                    }
                }
            ],
            metadata={
                "version": "1.0.0",
                "description": "Meal plan generation service contract",
                "owner": "meal-planning-team",
                "sla": {
                    "response_time_ms": 2000,
                    "availability": 99.9
                }
            }
        )
        contracts.append(plan_generation_contract)
        
        # Recipe Recommendation Contract
        recipe_recommendation_contract = self.contract_manager.create_contract(
            consumer="chatbot-service",
            provider=self.service_name,
            contract_type="rest",
            interactions=[
                {
                    "description": "Get recipe recommendations",
                    "request": {
                        "method": "GET",
                        "path": "/api/v1/recipes/recommendations",
                        "headers": {
                            "Authorization": "Bearer {token}"
                        },
                        "query_params": {
                            "user_id": "550e8400-e29b-41d4-a716-446655440000",
                            "meal_type": "dinner",
                            "max_prep_time": "30",
                            "difficulty_level": "easy",
                            "limit": "5"
                        },
                        "schema": self.schemas.get_recipe_recommendation_request_schema()
                    },
                    "response": {
                        "status": 200,
                        "headers": {
                            "Content-Type": "application/json",
                            "Cache-Control": "max-age=600"
                        },
                        "body": {
                            "recommendations": [
                                {
                                    "id": "recipe_123",
                                    "name": "Quick Veggie Stir Fry",
                                    "match_score": 0.95,
                                    "nutrition": {
                                        "calories": 420,
                                        "macros": {
                                            "protein": 18,
                                            "carbs": 45,
                                            "fat": 22
                                        }
                                    },
                                    "prep_time": 15,
                                    "cook_time": 10,
                                    "difficulty": "easy"
                                }
                            ],
                            "total_results": 15,
                            "filters_applied": {
                                "meal_type": "dinner",
                                "max_prep_time": 30,
                                "difficulty": "easy"
                            }
                        }
                    }
                }
            ]
        )
        contracts.append(recipe_recommendation_contract)
        
        return contracts
