"""
Clean Architecture Lambda handler example.

This handler demonstrates the new architecture by using dependency injection
and separating concerns between infrastructure, use cases, and business logic.
"""

import json
import os
from typing import Dict, Any

from ..core.use_cases import NutritionChatUseCase, MealPlanGenerationUseCase
from ..adapters import (
    DynamoDBUserRepository,
    AWSMessagingService,
    BedrockAIService
)


class DependencyContainer:
    """Simple dependency injection container."""
    
    def __init__(self):
        # Infrastructure configuration
        self.table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'ai-nutritionist-users')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Initialize adapters
        self.user_repository = DynamoDBUserRepository(self.table_name, self.region)
        self.messaging_service = AWSMessagingService(self.region)
        self.ai_service = BedrockAIService(self.region)
        
        # Initialize use cases
        self.nutrition_chat_use_case = NutritionChatUseCase(
            self.user_repository,
            self.messaging_service,
            self.ai_service,
            None  # nutrition_service would go here
        )
        
        self.meal_plan_use_case = MealPlanGenerationUseCase(
            self.user_repository,
            self.ai_service,
            self.messaging_service
        )


# Global container instance
container = DependencyContainer()


async def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Clean Architecture Lambda handler.
    
    This handler focuses only on HTTP concerns and delegates business logic
    to use cases, maintaining separation of concerns.
    """
    try:
        # Parse incoming request
        body = json.loads(event.get('body', '{}'))
        
        # Route to appropriate use case based on request
        if event['httpMethod'] == 'POST' and '/chat' in event['path']:
            await handle_chat_message(body)
        elif event['httpMethod'] == 'POST' and '/meal-plan' in event['path']:
            await handle_meal_plan_request(body)
        else:
            return create_response(400, {'error': 'Unsupported endpoint'})
        
        return create_response(200, {'status': 'success'})
        
    except Exception as e:
        print(f"Handler error: {e}")
        return create_response(500, {'error': 'Internal server error'})


async def handle_chat_message(body: Dict[str, Any]) -> None:
    """Handle incoming chat message."""
    user_id = body.get('user_id')
    message = body.get('message')
    
    if not user_id or not message:
        raise ValueError("Missing required fields: user_id, message")
    
    await container.nutrition_chat_use_case.handle_message(user_id, message)


async def handle_meal_plan_request(body: Dict[str, Any]) -> None:
    """Handle meal plan generation request."""
    user_id = body.get('user_id')
    
    if not user_id:
        raise ValueError("Missing required field: user_id")
    
    await container.meal_plan_use_case.generate_meal_plan(user_id)


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized Lambda response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }
