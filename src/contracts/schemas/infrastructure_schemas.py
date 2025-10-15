"""
Infrastructure Service Contract Schemas
"""

from typing import Dict, Any


class InfrastructureServiceSchemas:
    """Contract schemas for Infrastructure Services."""
    
    @staticmethod
    def get_observability_metrics_response_schema() -> Dict[str, Any]:
        """Schema for observability metrics response."""
        return {
            "type": "object",
            "required": ["timestamp", "red_metrics", "slo_status"],
            "properties": {
                "timestamp": {
                    "type": "string",
                    "format": "date-time"
                },
                "red_metrics": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                            "type": "object",
                            "required": ["rate", "errors", "duration"],
                            "properties": {
                                "rate": {
                                    "type": "number",
                                    "minimum": 0,
                                    "description": "Requests per second"
                                },
                                "errors": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 100,
                                    "description": "Error rate percentage"
                                },
                                "duration": {
                                    "type": "number",
                                    "minimum": 0,
                                    "description": "Average duration in milliseconds"
                                }
                            }
                        }
                    }
                },
                "slo_status": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-zA-Z_][a-zA-Z0-9_]*$": {
                            "type": "object",
                            "required": ["target", "current", "status"],
                            "properties": {
                                "target": {"type": "number", "minimum": 0, "maximum": 100},
                                "current": {"type": "number", "minimum": 0, "maximum": 100},
                                "status": {
                                    "type": "string",
                                    "enum": ["healthy", "warning", "critical"]
                                },
                                "breach_count": {"type": "integer", "minimum": 0}
                            }
                        }
                    }
                },
                "health_metrics": {
                    "type": "object",
                    "properties": {
                        "cpu_usage": {"type": "number", "minimum": 0, "maximum": 100},
                        "memory_usage": {"type": "number", "minimum": 0, "maximum": 100},
                        "disk_usage": {"type": "number", "minimum": 0, "maximum": 100},
                        "active_connections": {"type": "integer", "minimum": 0}
                    }
                }
            }
        }
    
    @staticmethod
    def get_rate_limit_request_schema() -> Dict[str, Any]:
        """Schema for rate limit check request."""
        return {
            "type": "object",
            "required": ["identifier", "action"],
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "User ID, IP address, or API key"
                },
                "action": {
                    "type": "string",
                    "enum": ["api_call", "message_send", "ai_query", "plan_generation"]
                },
                "weight": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                    "description": "Cost weight of the action"
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "user_tier": {"type": "string"},
                        "ip_address": {"type": "string"},
                        "user_agent": {"type": "string"}
                    }
                }
            }
        }
    
    @staticmethod
    def get_rate_limit_response_schema() -> Dict[str, Any]:
        """Schema for rate limit check response."""
        return {
            "type": "object",
            "required": ["allowed", "identifier", "remaining", "reset_time"],
            "properties": {
                "allowed": {
                    "type": "boolean",
                    "description": "Whether the request is allowed"
                },
                "identifier": {"type": "string"},
                "remaining": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Remaining requests in current window"
                },
                "reset_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "When the rate limit resets"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Total requests allowed in window"
                },
                "window_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Rate limit window in seconds"
                },
                "blocked_until": {
                    "type": "string",
                    "format": "date-time",
                    "description": "When the identifier will be unblocked (if blocked)"
                }
            }
        }
    
    @staticmethod
    def get_secret_create_request_schema() -> Dict[str, Any]:
        """Schema for secret creation request."""
        return {
            "type": "object",
            "required": ["name", "value", "secret_type"],
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": "^[a-zA-Z][a-zA-Z0-9_-]*$",
                    "description": "Secret name (alphanumeric, underscore, hyphen)"
                },
                "value": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Secret value"
                },
                "secret_type": {
                    "type": "string",
                    "enum": ["api_key", "database_url", "jwt_secret", "encryption_key", "service_account", "certificate"]
                },
                "rotation_interval_days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 365,
                    "description": "Auto-rotation interval in days"
                },
                "tags": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-zA-Z][a-zA-Z0-9_-]*$": {"type": "string"}
                    },
                    "additionalProperties": False
                },
                "description": {"type": "string"}
            }
        }
    
    @staticmethod
    def get_incident_create_request_schema() -> Dict[str, Any]:
        """Schema for incident creation request."""
        return {
            "type": "object",
            "required": ["title", "severity", "service"],
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 5,
                    "maxLength": 200
                },
                "description": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"]
                },
                "service": {
                    "type": "string",
                    "description": "Affected service name"
                },
                "category": {
                    "type": "string",
                    "enum": ["performance", "availability", "security", "data", "integration"]
                },
                "impact": {
                    "type": "object",
                    "properties": {
                        "affected_users": {"type": "integer", "minimum": 0},
                        "revenue_impact": {"type": "number", "minimum": 0},
                        "services_down": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "reporter": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "role": {"type": "string"}
                    }
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
