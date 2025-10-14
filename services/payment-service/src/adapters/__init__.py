"""Adapters layer for service.

Infrastructure adapters for external dependencies.
"""

from .repositories import (
    DynamoDBUserRepository,
    DynamoDBMealPlanRepository,
    DynamoDBSubscriptionRepository
)
from .external_services import (
    EdamamNutritionService,
    StripePaymentService,
    BedrockAIService
)
from .messaging import (
    PinpointMessagingAdapter,
    SQSMessageAdapter,
    EventBridgeAdapter
)

__all__ = [
    # Repositories
    "DynamoDBUserRepository",
    "DynamoDBMealPlanRepository",
    "DynamoDBSubscriptionRepository",
    
    # External Services
    "EdamamNutritionService",
    "StripePaymentService", 
    "BedrockAIService",
    
    # Messaging
    "PinpointMessagingAdapter",
    "SQSMessageAdapter",
    "EventBridgeAdapter",
]
