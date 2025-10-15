"""
Nutrition Service Provider Contracts

Defines contracts for the Nutrition Service as a provider.
"""

from typing import List, Dict, Any
from ..core.contract_manager import ContractManager
from ..schemas.nutrition_schemas import NutritionServiceSchemas


class NutritionServiceProvider:
    """Nutrition Service as a contract provider."""
    
    def __init__(self, contract_manager: ContractManager):
        self.contract_manager = contract_manager
        self.service_name = "nutrition-service"
        self.schemas = NutritionServiceSchemas()
    
    def create_contracts(self) -> List[str]:
        """Create all contracts for the Nutrition Service as a provider."""
        contracts = []
        
        # Nutrition Analysis Contract
        nutrition_analysis_contract = self.contract_manager.create_contract(
            consumer="meal-planning-service",
            provider=self.service_name,
            contract_type="rest",
            interactions=[
                {
                    "description": "Analyze nutrition for food items",
                    "request": {
                        "method": "POST",
                        "path": "/api/v1/nutrition/analyze",
                        "headers": {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer {token}"
                        },
                        "body": {
                            "user_id": "550e8400-e29b-41d4-a716-446655440000",
                            "food_items": [
                                {
                                    "name": "apple",
                                    "quantity": 150,
                                    "brand": "organic"
                                }
                            ],
                            "analysis_type": "detailed"
                        },
                        "schema": self.schemas.get_nutrition_analysis_request_schema()
                    },
                    "response": {
                        "status": 200,
                        "headers": {
                            "Content-Type": "application/json"
                        },
                        "body": {
                            "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                            "total_nutrition": {
                                "calories": 78,
                                "macros": {
                                    "protein": 0.4,
                                    "carbs": 20.6,
                                    "fat": 0.2,
                                    "fiber": 3.3
                                }
                            },
                            "item_breakdown": [
                                {
                                    "name": "apple",
                                    "quantity": 150,
                                    "nutrition": {
                                        "calories": 78,
                                        "macros": {
                                            "protein": 0.4,
                                            "carbs": 20.6,
                                            "fat": 0.2,
                                            "fiber": 3.3
                                        }
                                    }
                                }
                            ],
                            "insights": [
                                {
                                    "type": "recommendation",
                                    "message": "Great source of fiber and vitamin C",
                                    "priority": "low"
                                }
                            ]
                        },
                        "schema": self.schemas.get_nutrition_analysis_response_schema()
                    }
                }
            ],
            metadata={
                "version": "1.0.0",
                "description": "Nutrition analysis service contract",
                "owner": "nutrition-team",
                "sla": {
                    "response_time_ms": 500,
                    "availability": 99.9
                }
            }
        )
        contracts.append(nutrition_analysis_contract)
        
        # Food Tracking Contract
        food_tracking_contract = self.contract_manager.create_contract(
            consumer="mobile-app",
            provider=self.service_name,
            contract_type="rest",
            interactions=[
                {
                    "description": "Track food intake",
                    "request": {
                        "method": "POST",
                        "path": "/api/v1/nutrition/track",
                        "headers": {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer {token}"
                        },
                        "body": {
                            "user_id": "550e8400-e29b-41d4-a716-446655440000",
                            "meal_type": "breakfast",
                            "food_items": [
                                {
                                    "name": "oatmeal",
                                    "quantity": 100,
                                    "unit": "grams"
                                }
                            ],
                            "timestamp": "2024-01-15T08:30:00Z"
                        },
                        "schema": self.schemas.get_track_food_request_schema()
                    },
                    "response": {
                        "status": 201,
                        "headers": {
                            "Content-Type": "application/json",
                            "Location": "/api/v1/nutrition/track/123e4567-e89b-12d3-a456-426614174000"
                        },
                        "body": {
                            "tracking_id": "123e4567-e89b-12d3-a456-426614174000",
                            "status": "recorded",
                            "nutrition_summary": {
                                "calories": 389,
                                "macros": {
                                    "protein": 16.9,
                                    "carbs": 66.3,
                                    "fat": 6.9
                                }
                            }
                        }
                    }
                }
            ]
        )
        contracts.append(food_tracking_contract)
        
        # Daily Summary Contract
        daily_summary_contract = self.contract_manager.create_contract(
            consumer="analytics-service",
            provider=self.service_name,
            contract_type="rest",
            interactions=[
                {
                    "description": "Get daily nutrition summary",
                    "request": {
                        "method": "GET",
                        "path": "/api/v1/nutrition/users/{user_id}/daily-summary",
                        "headers": {
                            "Authorization": "Bearer {token}"
                        },
                        "query_params": {
                            "date": "2024-01-15"
                        }
                    },
                    "response": {
                        "status": 200,
                        "headers": {
                            "Content-Type": "application/json",
                            "Cache-Control": "max-age=300"
                        },
                        "body": {
                            "date": "2024-01-15",
                            "total_nutrition": {
                                "calories": 2100,
                                "macros": {
                                    "protein": 140,
                                    "carbs": 250,
                                    "fat": 85
                                }
                            },
                            "meals": [
                                {
                                    "meal_type": "breakfast",
                                    "nutrition": {
                                        "calories": 450,
                                        "macros": {
                                            "protein": 25,
                                            "carbs": 60,
                                            "fat": 15
                                        }
                                    },
                                    "items_count": 3
                                }
                            ],
                            "goals_progress": {
                                "calories": {
                                    "target": 2000,
                                    "consumed": 2100,
                                    "percentage": 105
                                }
                            }
                        },
                        "schema": self.schemas.get_daily_summary_response_schema()
                    }
                }
            ]
        )
        contracts.append(daily_summary_contract)
        
        return contracts
    
    def get_error_responses(self) -> List[Dict[str, Any]]:
        """Get standard error response definitions."""
        return [
            {
                "status": 400,
                "description": "Bad Request - Invalid input data",
                "body": {
                    "error": "validation_error",
                    "message": "Invalid food item data",
                    "details": {
                        "field": "quantity",
                        "issue": "must be greater than 0"
                    }
                }
            },
            {
                "status": 401,
                "description": "Unauthorized - Invalid or missing authentication",
                "body": {
                    "error": "authentication_required",
                    "message": "Valid authentication token required"
                }
            },
            {
                "status": 404,
                "description": "Not Found - User or resource not found",
                "body": {
                    "error": "not_found",
                    "message": "User not found"
                }
            },
            {
                "status": 429,
                "description": "Too Many Requests - Rate limit exceeded",
                "body": {
                    "error": "rate_limit_exceeded",
                    "message": "API rate limit exceeded",
                    "retry_after": 60
                }
            },
            {
                "status": 500,
                "description": "Internal Server Error",
                "body": {
                    "error": "internal_error",
                    "message": "An unexpected error occurred",
                    "request_id": "req_123456789"
                }
            }
        ]
