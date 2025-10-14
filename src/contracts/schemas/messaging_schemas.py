"""
Messaging Service Contract Schemas
"""

from typing import Dict, Any


class MessagingServiceSchemas:
    """Contract schemas for Messaging Service."""
    
    @staticmethod
    def get_send_message_request_schema() -> Dict[str, Any]:
        """Schema for send message request."""
        return {
            "type": "object",
            "required": ["user_id", "message", "channel"],
            "properties": {
                "user_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "message": {
                    "type": "object",
                    "required": ["content", "type"],
                    "properties": {
                        "content": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["text", "image", "audio", "document", "location"]
                        },
                        "metadata": {
                            "type": "object",
                            "additionalProperties": True
                        }
                    }
                },
                "channel": {
                    "type": "string",
                    "enum": ["whatsapp", "sms", "telegram", "messenger"]
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "default": "normal"
                },
                "schedule_time": {
                    "type": "string",
                    "format": "date-time"
                },
                "template_id": {"type": "string"},
                "personalization": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                }
            }
        }
    
    @staticmethod
    def get_message_response_schema() -> Dict[str, Any]:
        """Schema for message response."""
        return {
            "type": "object",
            "required": ["message_id", "status", "channel", "timestamp"],
            "properties": {
                "message_id": {
                    "type": "string",
                    "format": "uuid"
                },
                "status": {
                    "type": "string",
                    "enum": ["sent", "delivered", "read", "failed", "scheduled"]
                },
                "channel": {"type": "string"},
                "timestamp": {
                    "type": "string",
                    "format": "date-time"
                },
                "delivery_info": {
                    "type": "object",
                    "properties": {
                        "delivered_at": {"type": "string", "format": "date-time"},
                        "read_at": {"type": "string", "format": "date-time"},
                        "failure_reason": {"type": "string"},
                        "retry_count": {"type": "integer", "minimum": 0}
                    }
                },
                "cost": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "minimum": 0},
                        "currency": {"type": "string"}
                    }
                }
            }
        }
    
    @staticmethod
    def get_webhook_event_schema() -> Dict[str, Any]:
        """Schema for incoming webhook events."""
        return {
            "type": "object",
            "required": ["event_type", "user_id", "channel", "timestamp"],
            "properties": {
                "event_type": {
                    "type": "string",
                    "enum": ["message_received", "delivery_status", "read_receipt", "user_action"]
                },
                "user_id": {"type": "string"},
                "channel": {"type": "string"},
                "timestamp": {
                    "type": "string",
                    "format": "date-time"
                },
                "message": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "content": {"type": "string"},
                        "type": {"type": "string"},
                        "attachments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "url": {"type": "string", "format": "uri"},
                                    "size": {"type": "integer"},
                                    "mime_type": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "status_update": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "new_status": {"type": "string"},
                        "error_code": {"type": "string"},
                        "error_message": {"type": "string"}
                    }
                }
            }
        }
