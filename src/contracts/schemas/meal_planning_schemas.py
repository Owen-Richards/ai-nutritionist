"""
Meal Planning Service Contract Schemas
"""

from typing import Dict, Any


class MealPlanningServiceSchemas:
    """Contract schemas for Meal Planning Service."""
    
    @staticmethod
    def get_generate_plan_request_schema() -> Dict[str, Any]:
        """Schema for meal plan generation request."""
        return {
            "type": "object",
            "required": ["user_id", "plan_duration", "preferences"],
            "properties": {
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "plan_duration": {
                    "type": "object",
                    "required": ["days"],
                    "properties": {
                        "days": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 30
                        },
                        "start_date": {
                            "type": "string",
                            "format": "date"
                        }
                    }
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "dietary_restrictions": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "vegetarian", "vegan", "gluten_free", 
                                    "dairy_free", "nut_free", "low_sodium",
                                    "keto", "paleo", "mediterranean"
                                ]
                            }
                        },
                        "allergies": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "cuisine_preferences": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "meal_complexity": {
                            "type": "string",
                            "enum": ["simple", "moderate", "complex"]
                        },
                        "cooking_time_limit": {
                            "type": "integer",
                            "minimum": 10,
                            "maximum": 180
                        }
                    }
                },
                "nutrition_goals": {
                    "type": "object",
                    "properties": {
                        "daily_calories": {
                            "type": "number",
                            "minimum": 800,
                            "maximum": 5000
                        },
                        "macro_targets": {
                            "type": "object",
                            "properties": {
                                "protein_percent": {"type": "number", "minimum": 10, "maximum": 50},
                                "carbs_percent": {"type": "number", "minimum": 20, "maximum": 70},
                                "fat_percent": {"type": "number", "minimum": 15, "maximum": 60}
                            }
                        }
                    }
                },
                "budget_constraints": {
                    "type": "object",
                    "properties": {
                        "max_daily_cost": {"type": "number", "minimum": 0},
                        "currency": {"type": "string", "default": "USD"}
                    }
                }
            }
        }
    
    @staticmethod
    def get_meal_plan_response_schema() -> Dict[str, Any]:
        """Schema for meal plan response."""
        return {
            "type": "object",
            "required": ["plan_id", "user_id", "duration", "daily_plans", "summary"],
            "properties": {
                "plan_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "duration": {
                    "type": "object",
                    "required": ["days", "start_date", "end_date"],
                    "properties": {
                        "days": {"type": "integer"},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    }
                },
                "daily_plans": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/daily_plan"
                    }
                },
                "summary": {
                    "type": "object",
                    "required": ["avg_daily_nutrition", "total_recipes", "estimated_cost"],
                    "properties": {
                        "avg_daily_nutrition": {
                            "$ref": "#/definitions/nutrition_summary"
                        },
                        "total_recipes": {"type": "integer"},
                        "estimated_cost": {
                            "type": "object",
                            "properties": {
                                "total": {"type": "number"},
                                "daily_average": {"type": "number"},
                                "currency": {"type": "string"}
                            }
                        },
                        "adherence_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        }
                    }
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time"
                }
            },
            "definitions": {
                "daily_plan": {
                    "type": "object",
                    "required": ["date", "meals"],
                    "properties": {
                        "date": {"type": "string", "format": "date"},
                        "meals": {
                            "type": "array", 
                            "items": {"$ref": "#/definitions/meal"}
                        },
                        "daily_nutrition": {
                            "$ref": "#/definitions/nutrition_summary"
                        }
                    }
                },
                "meal": {
                    "type": "object",
                    "required": ["meal_type", "recipe"],
                    "properties": {
                        "meal_type": {
                            "type": "string",
                            "enum": ["breakfast", "lunch", "dinner", "snack"]
                        },
                        "recipe": {"$ref": "#/definitions/recipe"},
                        "serving_size": {"type": "number", "default": 1},
                        "prep_time": {"type": "integer"},
                        "cook_time": {"type": "integer"}
                    }
                },
                "recipe": {
                    "type": "object",
                    "required": ["id", "name", "ingredients", "instructions"],
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "ingredients": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "amount", "unit"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "amount": {"type": "number"},
                                    "unit": {"type": "string"},
                                    "optional": {"type": "boolean", "default": False}
                                }
                            }
                        },
                        "instructions": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "nutrition": {
                            "$ref": "#/definitions/nutrition_summary"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "difficulty": {
                            "type": "string",
                            "enum": ["easy", "medium", "hard"]
                        },
                        "servings": {"type": "integer", "minimum": 1}
                    }
                },
                "nutrition_summary": {
                    "type": "object",
                    "required": ["calories", "macros"],
                    "properties": {
                        "calories": {"type": "number", "minimum": 0},
                        "macros": {
                            "type": "object",
                            "required": ["protein", "carbs", "fat"],
                            "properties": {
                                "protein": {"type": "number"},
                                "carbs": {"type": "number"},
                                "fat": {"type": "number"},
                                "fiber": {"type": "number"}
                            }
                        },
                        "micronutrients": {
                            "type": "object",
                            "additionalProperties": {"type": "number"}
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def get_update_plan_request_schema() -> Dict[str, Any]:
        """Schema for meal plan update request."""
        return {
            "type": "object",
            "required": ["plan_id", "changes"],
            "properties": {
                "plan_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["type", "target"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["replace_meal", "swap_recipe", "adjust_serving", "remove_meal", "add_meal"]
                            },
                            "target": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string", "format": "date"},
                                    "meal_type": {"type": "string"},
                                    "recipe_id": {"type": "string"}
                                }
                            },
                            "replacement": {
                                "type": "object",
                                "properties": {
                                    "recipe_id": {"type": "string"},
                                    "serving_size": {"type": "number"}
                                }
                            },
                            "reason": {"type": "string"}
                        }
                    }
                },
                "regenerate_affected_days": {
                    "type": "boolean",
                    "default": False
                }
            }
        }
    
    @staticmethod
    def get_recipe_recommendation_request_schema() -> Dict[str, Any]:
        """Schema for recipe recommendation request."""
        return {
            "type": "object",
            "required": ["user_id", "meal_type"],
            "properties": {
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "meal_type": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner", "snack"]
                },
                "target_nutrition": {
                    "type": "object",
                    "properties": {
                        "calories": {"type": "number"},
                        "protein": {"type": "number"},
                        "carbs": {"type": "number"},
                        "fat": {"type": "number"}
                    }
                },
                "ingredients_to_use": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "ingredients_to_avoid": {
                    "type": "array",
                    "items": {"type": "string"}  
                },
                "max_prep_time": {
                    "type": "integer",
                    "minimum": 5
                },
                "difficulty_level": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"]
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10
                }
            }
        }
