"""
Analytics Service Contract Schemas
"""

from typing import Dict, Any


class AnalyticsServiceSchemas:
    """Contract schemas for Analytics Service."""
    
    @staticmethod
    def get_track_event_request_schema() -> Dict[str, Any]:
        """Schema for event tracking request."""
        return {
            "type": "object",
            "required": ["event_name", "user_id", "timestamp"],
            "properties": {
                "event_name": {
                    "type": "string",
                    "pattern": "^[a-zA-Z][a-zA-Z0-9_]*$",
                    "description": "Event name (alphanumeric and underscore)"
                },
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time"
                },
                "properties": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Custom event properties"
                },
                "session_id": {"type": "string"},
                "device_info": {
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string"},
                        "version": {"type": "string"},
                        "device_id": {"type": "string"}
                    }
                },
                "location": {
                    "type": "object",
                    "properties": {
                        "country": {"type": "string"},
                        "region": {"type": "string"},
                        "city": {"type": "string"},
                        "timezone": {"type": "string"}
                    }
                }
            }
        }
    
    @staticmethod
    def get_user_metrics_response_schema() -> Dict[str, Any]:
        """Schema for user metrics response."""
        return {
            "type": "object",
            "required": ["user_id", "metrics", "period"],
            "properties": {
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "period": {
                    "type": "object",
                    "required": ["start_date", "end_date"],
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    }
                },
                "metrics": {
                    "type": "object",
                    "required": ["engagement", "nutrition", "goals"],
                    "properties": {
                        "engagement": {
                            "type": "object",
                            "properties": {
                                "total_sessions": {"type": "integer", "minimum": 0},
                                "avg_session_duration": {"type": "number", "minimum": 0},
                                "messages_sent": {"type": "integer", "minimum": 0},
                                "messages_received": {"type": "integer", "minimum": 0},
                                "feature_usage": {
                                    "type": "object",
                                    "additionalProperties": {"type": "integer"}
                                }
                            }
                        },
                        "nutrition": {
                            "type": "object",
                            "properties": {
                                "meals_logged": {"type": "integer", "minimum": 0},
                                "days_active": {"type": "integer", "minimum": 0},
                                "avg_daily_calories": {"type": "number", "minimum": 0},
                                "macro_adherence": {
                                    "type": "object",
                                    "properties": {
                                        "protein": {"type": "number", "minimum": 0, "maximum": 100},
                                        "carbs": {"type": "number", "minimum": 0, "maximum": 100},
                                        "fat": {"type": "number", "minimum": 0, "maximum": 100}
                                    }
                                }
                            }
                        },
                        "goals": {
                            "type": "object",
                            "properties": {
                                "total_goals": {"type": "integer", "minimum": 0},
                                "completed_goals": {"type": "integer", "minimum": 0},
                                "completion_rate": {"type": "number", "minimum": 0, "maximum": 100},
                                "streak_days": {"type": "integer", "minimum": 0}
                            }
                        }
                    }
                },
                "insights": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "message": {"type": "string"},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def get_funnel_metrics_response_schema() -> Dict[str, Any]:
        """Schema for funnel metrics response."""
        return {
            "type": "object",
            "required": ["funnel_name", "period", "stages"],
            "properties": {
                "funnel_name": {"type": "string"},
                "period": {
                    "type": "object",
                    "required": ["start_date", "end_date"],
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    }
                },
                "stages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "users", "conversion_rate"],
                        "properties": {
                            "name": {"type": "string"},
                            "users": {"type": "integer", "minimum": 0},
                            "conversion_rate": {"type": "number", "minimum": 0, "maximum": 100},
                            "drop_off_rate": {"type": "number", "minimum": 0, "maximum": 100},
                            "avg_time_to_convert": {"type": "number", "minimum": 0}
                        }
                    }
                },
                "total_users": {"type": "integer", "minimum": 0},
                "overall_conversion_rate": {"type": "number", "minimum": 0, "maximum": 100},
                "generated_at": {"type": "string", "format": "date-time"}
            }
        }
    
    @staticmethod
    def get_cohort_analysis_response_schema() -> Dict[str, Any]:
        """Schema for cohort analysis response."""
        return {
            "type": "object",
            "required": ["cohort_type", "cohorts", "metric"],
            "properties": {
                "cohort_type": {
                    "type": "string",
                    "enum": ["registration", "first_purchase", "first_meal_plan"]
                },
                "metric": {
                    "type": "string",  
                    "enum": ["retention", "revenue", "engagement"]
                },
                "cohorts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["period", "size", "data_points"],
                        "properties": {
                            "period": {"type": "string"},
                            "size": {"type": "integer", "minimum": 0},
                            "data_points": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "period_offset": {"type": "integer", "minimum": 0},
                                        "value": {"type": "number", "minimum": 0},
                                        "percentage": {"type": "number", "minimum": 0, "maximum": 100}
                                    }
                                }
                            }
                        }
                    }
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "avg_retention_rate": {"type": "number", "minimum": 0, "maximum": 100},
                        "best_cohort": {"type": "string"},
                        "worst_cohort": {"type": "string"},
                        "trend": {"type": "string", "enum": ["improving", "declining", "stable"]}
                    }
                }
            }
        }
    
    @staticmethod
    def get_revenue_metrics_response_schema() -> Dict[str, Any]:
        """Schema for revenue metrics response."""
        return {
            "type": "object",
            "required": ["period", "total_revenue", "breakdown"],
            "properties": {
                "period": {
                    "type": "object",
                    "required": ["start_date", "end_date"],
                    "properties": {
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    }
                },
                "total_revenue": {
                    "type": "number",
                    "minimum": 0
                },
                "currency": {"type": "string", "default": "USD"},
                "breakdown": {
                    "type": "object",
                    "properties": {
                        "subscriptions": {"type": "number", "minimum": 0},
                        "affiliates": {"type": "number", "minimum": 0},
                        "partnerships": {"type": "number", "minimum": 0},
                        "one_time": {"type": "number", "minimum": 0}
                    }
                },
                "metrics": {
                    "type": "object",
                    "properties": {
                        "mrr": {"type": "number", "minimum": 0, "description": "Monthly Recurring Revenue"},
                        "arr": {"type": "number", "minimum": 0, "description": "Annual Recurring Revenue"},
                        "ltv": {"type": "number", "minimum": 0, "description": "Customer Lifetime Value"},
                        "churn_rate": {"type": "number", "minimum": 0, "maximum": 100},
                        "arpu": {"type": "number", "minimum": 0, "description": "Average Revenue Per User"}
                    }
                },
                "growth": {
                    "type": "object",
                    "properties": {
                        "revenue_growth_rate": {"type": "number"},
                        "user_growth_rate": {"type": "number"},
                        "mrr_growth_rate": {"type": "number"}
                    }
                }
            }
        }
