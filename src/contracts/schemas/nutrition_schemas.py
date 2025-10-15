"""
Nutrition Service Contract Schemas
"""

from typing import Dict, Any


class NutritionServiceSchemas:
    """Contract schemas for Nutrition Service."""
    
    @staticmethod
    def get_nutrition_analysis_request_schema() -> Dict[str, Any]:
        """Schema for nutrition analysis request."""
        return {
            "type": "object",
            "required": ["user_id", "food_items"],
            "properties": {
                "user_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "User identifier"
                },
                "food_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "quantity"],
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Food item name"
                            },
                            "quantity": {
                                "type": "number",
                                "minimum": 0,
                                "description": "Quantity in grams"
                            },
                            "brand": {
                                "type": "string",
                                "description": "Brand name (optional)"
                            }
                        }
                    }
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["basic", "detailed", "premium"],
                    "default": "basic"
                }
            }
        }
    
    @staticmethod
    def get_nutrition_analysis_response_schema() -> Dict[str, Any]:
        """Schema for nutrition analysis response."""
        return {
            "type": "object",
            "required": ["analysis_id", "total_nutrition", "item_breakdown"],
            "properties": {
                "analysis_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "total_nutrition": {
                    "type": "object",
                    "required": ["calories", "macros"],
                    "properties": {
                        "calories": {
                            "type": "number",
                            "minimum": 0
                        },
                        "macros": {
                            "type": "object",
                            "required": ["protein", "carbs", "fat"],
                            "properties": {
                                "protein": {"type": "number", "minimum": 0},
                                "carbs": {"type": "number", "minimum": 0},
                                "fat": {"type": "number", "minimum": 0},
                                "fiber": {"type": "number", "minimum": 0}
                            }
                        },
                        "vitamins": {
                            "type": "object",
                            "additionalProperties": {"type": "number"}
                        },
                        "minerals": {
                            "type": "object", 
                            "additionalProperties": {"type": "number"}
                        }
                    }
                },
                "item_breakdown": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "nutrition"],
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "number"},
                            "nutrition": {
                                "$ref": "#/properties/total_nutrition"
                            }
                        }
                    }
                },
                "insights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["warning", "recommendation", "achievement"]
                            },
                            "message": {"type": "string"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high"]
                            }
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def get_track_food_request_schema() -> Dict[str, Any]:
        """Schema for food tracking request."""
        return {
            "type": "object",
            "required": ["user_id", "meal_type", "food_items", "timestamp"],
            "properties": {
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "meal_type": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner", "snack"]
                },
                "food_items": {
                    "$ref": "#/definitions/food_items"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time"
                },
                "location": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"}
                    }
                }
            },
            "definitions": {
                "food_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "quantity"],
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "number", "minimum": 0},
                            "unit": {"type": "string", "default": "grams"}
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def get_daily_summary_response_schema() -> Dict[str, Any]:
        """Schema for daily nutrition summary."""
        return {
            "type": "object",
            "required": ["date", "total_nutrition", "meals", "goals_progress"],
            "properties": {
                "date": {
                    "type": "string",
                    "format": "date"
                },
                "total_nutrition": {
                    "$ref": "#/definitions/nutrition_data"
                },
                "meals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["meal_type", "nutrition", "items_count"],
                        "properties": {
                            "meal_type": {
                                "type": "string",
                                "enum": ["breakfast", "lunch", "dinner", "snack"]
                            },
                            "nutrition": {
                                "$ref": "#/definitions/nutrition_data"
                            },
                            "items_count": {
                                "type": "integer",
                                "minimum": 0
                            }
                        }
                    }
                },
                "goals_progress": {
                    "type": "object",
                    "properties": {
                        "calories": {
                            "type": "object",
                            "properties": {
                                "target": {"type": "number"},
                                "consumed": {"type": "number"},
                                "percentage": {"type": "number", "minimum": 0, "maximum": 200}
                            }
                        },
                        "macros": {
                            "type": "object",
                            "properties": {
                                "protein": {"$ref": "#/definitions/goal_progress"},
                                "carbs": {"$ref": "#/definitions/goal_progress"},
                                "fat": {"$ref": "#/definitions/goal_progress"}
                            }
                        }
                    }
                }
            },
            "definitions": {
                "nutrition_data": {
                    "type": "object",
                    "required": ["calories", "macros"],
                    "properties": {
                        "calories": {"type": "number", "minimum": 0},
                        "macros": {
                            "type": "object",
                            "required": ["protein", "carbs", "fat"],
                            "properties": {
                                "protein": {"type": "number", "minimum": 0},
                                "carbs": {"type": "number", "minimum": 0},
                                "fat": {"type": "number", "minimum": 0}
                            }
                        }
                    }
                },
                "goal_progress": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "number"},
                        "consumed": {"type": "number"},
                        "percentage": {"type": "number", "minimum": 0}
                    }
                }
            }
        }
