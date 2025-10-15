"""
Business Service Contract Schemas
"""

from typing import Dict, Any


class BusinessServiceSchemas:
    """Contract schemas for Business Services."""
    
    @staticmethod
    def get_subscription_create_request_schema() -> Dict[str, Any]:
        """Schema for subscription creation request."""
        return {
            "type": "object",
            "required": ["user_id", "plan_type", "payment_method"],
            "properties": {
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "plan_type": {
                    "type": "string",
                    "enum": ["basic", "premium", "professional", "enterprise"]
                },
                "billing_cycle": {
                    "type": "string",
                    "enum": ["monthly", "quarterly", "yearly"],
                    "default": "monthly"
                },
                "payment_method": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["credit_card", "debit_card", "paypal", "bank_transfer"]
                        },
                        "token": {"type": "string"},
                        "last_four": {"type": "string"},
                        "expiry_month": {"type": "integer", "minimum": 1, "maximum": 12},
                        "expiry_year": {"type": "integer"}
                    }
                },
                "promo_code": {"type": "string"},
                "auto_renew": {"type": "boolean", "default": True}
            }
        }
    
    @staticmethod
    def get_subscription_response_schema() -> Dict[str, Any]:
        """Schema for subscription response."""
        return {
            "type": "object",
            "required": ["subscription_id", "user_id", "plan", "status", "billing"],
            "properties": {
                "subscription_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "plan": {
                    "type": "object",
                    "required": ["type", "name", "features"],
                    "properties": {
                        "type": {"type": "string"},
                        "name": {"type": "string"},
                        "features": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "limits": {
                            "type": "object",
                            "properties": {
                                "daily_queries": {"type": "integer"},
                                "meal_plans_per_month": {"type": "integer"},
                                "custom_recipes": {"type": "integer"}
                            }
                        }
                    }
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "cancelled", "suspended", "expired"]
                },
                "billing": {
                    "type": "object",
                    "required": ["amount", "currency", "cycle"],
                    "properties": {
                        "amount": {"type": "number", "minimum": 0},
                        "currency": {"type": "string"},
                        "cycle": {"type": "string"},
                        "next_billing_date": {"type": "string", "format": "date"},
                        "payment_method": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "last_four": {"type": "string"}
                            }
                        }
                    }
                },
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"}
            }
        }
    
    @staticmethod
    def get_revenue_tracking_request_schema() -> Dict[str, Any]:
        """Schema for revenue tracking request."""
        return {
            "type": "object",
            "required": ["event_type", "user_id", "amount"],
            "properties": {
                "event_type": {
                    "type": "string",
                    "enum": ["subscription_created", "payment_received", "refund_issued", "affiliate_commission", "upgrade", "downgrade"]
                },
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "amount": {
                    "type": "number",
                    "minimum": 0
                },
                "currency": {
                    "type": "string",
                    "default": "USD"
                },
                "transaction_id": {"type": "string"},
                "subscription_id": {"type": "string"},
                "affiliate_data": {
                    "type": "object",
                    "properties": {
                        "affiliate_id": {"type": "string"},
                        "commission_rate": {"type": "number", "minimum": 0, "maximum": 1},
                        "partner_name": {"type": "string"}
                    }
                },
                "metadata": {
                    "type": "object",
                    "additionalProperties": True
                }
            }
        }
    
    @staticmethod
    def get_cost_tracking_request_schema() -> Dict[str, Any]:
        """Schema for cost tracking request."""
        return {
            "type": "object",
            "required": ["cost_type", "amount", "service"],
            "properties": {
                "cost_type": {
                    "type": "string",
                    "enum": ["ai_api", "messaging", "storage", "compute", "third_party"]
                },
                "amount": {
                    "type": "number",
                    "minimum": 0
                },
                "currency": {"type": "string", "default": "USD"},
                "service": {"type": "string"},
                "user_id": {"type": "string", "format": "uuid"},
                "request_id": {"type": "string"},
                "usage_metrics": {
                    "type": "object",
                    "properties": {
                        "tokens_used": {"type": "integer"},
                        "api_calls": {"type": "integer"},
                        "data_processed": {"type": "number"},
                        "duration_seconds": {"type": "number"}
                    }
                },
                "timestamp": {"type": "string", "format": "date-time"}
            }
        }
