"""
Messaging Service Provider Contracts
"""

from typing import List, Dict, Any
from ..core.contract_manager import ContractManager
from ..schemas.messaging_schemas import MessagingServiceSchemas


class MessagingServiceProvider:
    """Messaging Service as a contract provider."""
    
    def __init__(self, contract_manager: ContractManager):
        self.contract_manager = contract_manager
        self.service_name = "messaging-service"
        self.schemas = MessagingServiceSchemas()
    
    def create_contracts(self) -> List[str]:
        """Create all contracts for the Messaging Service as a provider."""
        contracts = []
        
        # Send Message Contract
        send_message_contract = self.contract_manager.create_contract(
            consumer="notification-service",
            provider=self.service_name,
            contract_type="rest",
            interactions=[
                {
                    "description": "Send message to user",
                    "request": {
                        "method": "POST",
                        "path": "/api/v1/messages/send",
                        "headers": {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer {token}"
                        },
                        "body": {
                            "user_id": "550e8400-e29b-41d4-a716-446655440000",
                            "message": {
                                "content": "Your meal plan for today is ready! 🍽️",
                                "type": "text"
                            },
                            "channel": "whatsapp",
                            "priority": "normal",
                            "template_id": "meal_plan_ready",
                            "personalization": {
                                "user_name": "John",
                                "plan_name": "Weekly Vegetarian Plan"
                            }
                        },
                        "schema": self.schemas.get_send_message_request_schema()
                    },
                    "response": {
                        "status": 201,
                        "headers": {
                            "Content-Type": "application/json",
                            "Location": "/api/v1/messages/123e4567-e89b-12d3-a456-426614174000"
                        },
                        "body": {
                            "message_id": "123e4567-e89b-12d3-a456-426614174000", 
                            "status": "sent",
                            "channel": "whatsapp",
                            "timestamp": "2024-01-15T14:30:00Z",
                            "cost": {
                                "amount": 0.05,
                                "currency": "USD"
                            }
                        },
                        "schema": self.schemas.get_message_response_schema()
                    }
                }
            ],
            metadata={
                "version": "1.0.0",
                "description": "Message sending service contract",
                "owner": "messaging-team",
                "sla": {
                    "response_time_ms": 1000,
                    "availability": 99.95
                }
            }
        )
        contracts.append(send_message_contract)
        
        # Webhook Events Contract (AsyncAPI-style)
        webhook_contract = self.contract_manager.create_contract(
            consumer="analytics-service",
            provider=self.service_name,
            contract_type="event",
            interactions=[
                {
                    "description": "Message status update event",
                    "event_type": "message.status.updated",
                    "channel": "messaging.events",
                    "schema": {
                        "type": "object",
                        "required": ["event_id", "message_id", "status", "timestamp"],
                        "properties": {
                            "event_id": {"type": "string", "format": "uuid"},
                            "message_id": {"type": "string", "format": "uuid"},
                            "status": {
                                "type": "string",
                                "enum": ["delivered", "read", "failed"]
                            },
                            "timestamp": {"type": "string", "format": "date-time"},
                            "user_id": {"type": "string", "format": "uuid"},
                            "channel": {"type": "string"},
                            "metadata": {
                                "type": "object",
                                "additionalProperties": True
                            }
                        }
                    },
                    "example": {
                        "event_id": "evt_123456789",
                        "message_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "delivered",
                        "timestamp": "2024-01-15T14:35:00Z",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "channel": "whatsapp",
                        "metadata": {
                            "delivery_timestamp": "2024-01-15T14:35:00Z",
                            "provider_message_id": "wamid.abc123"
                        }
                    }
                },
                {
                    "description": "Incoming message received event",
                    "event_type": "message.received",
                    "channel": "messaging.inbound",
                    "schema": {
                        "type": "object",
                        "required": ["event_id", "user_id", "message", "timestamp"],
                        "properties": {
                            "event_id": {"type": "string", "format": "uuid"},
                            "user_id": {"type": "string", "format": "uuid"},
                            "channel": {"type": "string"},
                            "timestamp": {"type": "string", "format": "date-time"},
                            "message": {
                                "type": "object",
                                "required": ["content", "type"],
                                "properties": {
                                    "content": {"type": "string"},
                                    "type": {"type": "string"},
                                    "attachments": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "type": {"type": "string"},
                                                "url": {"type": "string"},
                                                "mime_type": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "example": {
                        "event_id": "evt_987654321",
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "channel": "whatsapp",
                        "timestamp": "2024-01-15T15:00:00Z",
                        "message": {
                            "content": "Can you suggest a healthy dinner recipe?",
                            "type": "text"
                        }
                    }
                }
            ],
            metadata={
                "async_api_version": "2.6.0",
                "description": "Messaging events for real-time updates",
                "owner": "messaging-team"
            }
        )
        contracts.append(webhook_contract)
        
        return contracts
