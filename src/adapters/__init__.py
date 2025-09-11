"""
External adapters for integrating with third-party services and AWS.
"""

from .dynamodb_repository import DynamoDBUserRepository
from .messaging_adapters import AWSMessagingService, WhatsAppMessagingService
from .bedrock_ai import BedrockAIService

__all__ = [
    'DynamoDBUserRepository',
    'AWSMessagingService', 
    'WhatsAppMessagingService',
    'BedrockAIService'
]
