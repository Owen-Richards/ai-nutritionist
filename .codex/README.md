# AI Nutritionist - Codex Integration Guide

## Overview

This guide optimizes the AI Nutritionist codebase for seamless GitHub Codex integration, ensuring efficient AI-assisted development workflows.

## Project Structure for AI Assistance

### Clean Architecture Implementation

```
src/
├── core/           # Domain entities and business rules
├── models/         # Data models and schemas
├── services/       # Application services (organized by domain)
├── adapters/       # External service integrations
├── api/           # Web API layer (FastAPI)
├── handlers/      # AWS Lambda handlers
├── config/        # Configuration management
├── utils/         # Shared utilities
└── templates/     # UI templates and widgets
```

### Service Layer Organization

```
services/
├── meal_planning/     # Core meal planning logic
├── nutrition/         # Nutrition analysis and recommendations
├── messaging/         # Multi-channel messaging (Pinpoint, SMS)
├── personalization/   # User preferences and AI learning
├── business/          # Business logic and workflows
├── gamification/      # User engagement features
├── monetization/      # Billing and subscription management
├── analytics/         # Usage tracking and insights
├── infrastructure/    # AWS service integrations
├── integrations/      # Third-party API connections
└── community/         # Social features and sharing
```

## Codex-Friendly Practices

### 1. Consistent Naming Conventions

- **Classes**: PascalCase (`UserPreferences`, `MealPlanService`)
- **Functions**: snake_case (`generate_meal_plan`, `calculate_nutrition`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRY_ATTEMPTS`, `DEFAULT_TIMEOUT`)
- **Files**: snake_case (`meal_plan_service.py`, `nutrition_calculator.py`)

### 2. Comprehensive Type Hints

```python
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class MealPlan:
    plan_id: UUID
    user_id: str
    meals: List[Dict[str, Any]]
    created_at: datetime
    preferences: Optional[Dict[str, Union[str, bool, int]]] = None
```

### 3. Clear Function Signatures

```python
async def generate_personalized_meal_plan(
    user_id: str,
    dietary_preferences: Dict[str, Any],
    budget_constraints: Optional[Dict[str, float]] = None,
    timeframe_days: int = 7
) -> MealPlan:
    """Generate a personalized meal plan using AI and user preferences.

    Args:
        user_id: Unique identifier for the user
        dietary_preferences: User's dietary restrictions and preferences
        budget_constraints: Optional budget limits per meal type
        timeframe_days: Number of days to plan for (default 7)

    Returns:
        MealPlan: Generated meal plan with nutrition analysis

    Raises:
        ValueError: If user_id is invalid or preferences are malformed
        AIServiceError: If Bedrock AI service is unavailable
    """
```

### 4. Structured Error Handling

```python
# Custom exception hierarchy
class AINutritionistError(Exception):
    """Base exception for AI Nutritionist application"""
    pass

class UserError(AINutritionistError):
    """User-related errors (validation, authentication)"""
    pass

class ExternalServiceError(AINutritionistError):
    """External service integration errors"""
    pass

class AIServiceError(ExternalServiceError):
    """AWS Bedrock AI service specific errors"""
    pass
```

## AWS Integration Patterns

### 1. Service Client Initialization

```python
import boto3
from typing import Optional
from src.config.settings import AWSConfig

class AWSServiceBase:
    """Base class for AWS service integrations"""

    def __init__(self, config: Optional[AWSConfig] = None):
        self.config = config or AWSConfig.from_env()
        self.region = self.config.region

    def _get_client(self, service_name: str):
        """Get boto3 client with consistent configuration"""
        return boto3.client(
            service_name,
            region_name=self.region
        )
```

### 2. Environment Variable Management

```python
# Use centralized configuration
from src.config.environment import get_env_var, get_env_bool

DATABASE_TABLE = get_env_var('DYNAMODB_USER_TABLE', 'ai-nutritionist-users-dev')
ENABLE_CACHING = get_env_bool('ENABLE_PROMPT_CACHING', True)
AI_MODEL_ID = get_env_var('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
```

### 3. Lambda Handler Pattern

```python
import json
import logging
from typing import Dict, Any
from src.handlers.base_handler import BaseLambdaHandler

logger = logging.getLogger(__name__)

class MealPlanHandler(BaseLambdaHandler):
    """AWS Lambda handler for meal planning requests"""

    async def handle_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process meal planning request"""
        try:
            # Extract and validate request
            request_data = self.parse_event(event)

            # Business logic
            meal_plan = await self.meal_plan_service.generate_plan(
                user_id=request_data['user_id'],
                preferences=request_data.get('preferences', {})
            )

            # Format response
            return self.success_response({
                'meal_plan': meal_plan.to_dict(),
                'plan_id': str(meal_plan.plan_id)
            })

        except Exception as e:
            logger.exception("Error generating meal plan")
            return self.error_response(str(e), 500)
```

## Testing Patterns for AI Systems

### 1. Mock External Services

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.services.infrastructure.ai import AIService

@pytest.fixture
def mock_bedrock_client():
    """Mock AWS Bedrock client for testing"""
    with patch('boto3.client') as mock_client:
        mock_bedrock = AsyncMock()
        mock_client.return_value = mock_bedrock
        yield mock_bedrock

async def test_generate_meal_plan_success(mock_bedrock_client):
    """Test successful meal plan generation"""
    # Arrange
    mock_bedrock_client.invoke_model.return_value = {
        'body': json.dumps({
            'completion': 'Generated meal plan content'
        })
    }

    ai_service = AIService()

    # Act
    result = await ai_service.generate_meal_plan(
        user_preferences={'diet': 'vegetarian'},
        budget=50.0
    )

    # Assert
    assert result is not None
    assert 'meals' in result
    mock_bedrock_client.invoke_model.assert_called_once()
```

### 2. Integration Test Patterns

```python
@pytest.mark.integration
async def test_end_to_end_meal_planning():
    """Test complete meal planning workflow"""
    # Use test database and real AWS services
    user_id = "test_user_123"

    # Create test user profile
    await user_service.create_profile(
        user_id=user_id,
        preferences={'diet': 'mediterranean', 'budget': 75.0}
    )

    # Generate meal plan
    meal_plan = await meal_plan_service.create_weekly_plan(user_id)

    # Verify results
    assert meal_plan.user_id == user_id
    assert len(meal_plan.meals) == 21  # 3 meals × 7 days

    # Cleanup
    await user_service.delete_profile(user_id)
```

## Code Documentation Standards

### 1. Module Documentation

```python
"""
Meal Planning Service

This module provides AI-powered meal planning capabilities using AWS Bedrock
and the Edamam nutrition database. It supports:

- Personalized meal recommendations based on dietary preferences
- Budget-aware meal planning with cost optimization
- Nutritional analysis and goal tracking
- Integration with calendar and grocery services

Key Classes:
    MealPlanService: Main service for meal plan generation
    NutritionCalculator: Nutritional analysis and recommendations
    BudgetOptimizer: Cost-aware meal selection

Dependencies:
    - AWS Bedrock (AI generation)
    - DynamoDB (user data persistence)
    - Edamam API (nutrition data)
"""
```

### 2. Function Documentation

```python
def calculate_nutritional_balance(
    meals: List[Dict[str, Any]],
    user_goals: Dict[str, float]
) -> Dict[str, float]:
    """Calculate nutritional balance against user goals.

    Analyzes the nutritional content of a meal plan and compares it
    against user-defined health goals and dietary requirements.

    Args:
        meals: List of meal dictionaries containing nutritional data
        user_goals: Target values for calories, protein, carbs, fat, etc.

    Returns:
        Dictionary mapping nutrient names to percentage of goal achieved

    Example:
        >>> meals = [{'calories': 500, 'protein': 25}, ...]
        >>> goals = {'calories': 2000, 'protein': 150}
        >>> calculate_nutritional_balance(meals, goals)
        {'calories': 85.5, 'protein': 90.2, ...}

    Note:
        Assumes meals contain standardized nutrition keys from Edamam API
    """
```

## Performance Optimization

### 1. Async/Await Patterns

```python
import asyncio
from typing import List, Dict, Any

class MealPlanService:
    """Service for generating optimized meal plans"""

    async def generate_weekly_plan(self, user_id: str) -> Dict[str, Any]:
        """Generate a complete weekly meal plan"""

        # Fetch user data concurrently
        user_profile, preferences, history = await asyncio.gather(
            self.user_service.get_profile(user_id),
            self.user_service.get_preferences(user_id),
            self.meal_service.get_recent_meals(user_id, days=30)
        )

        # Generate meals for each day concurrently
        daily_plans = await asyncio.gather(*[
            self._generate_daily_meals(user_profile, preferences, day)
            for day in range(7)
        ])

        return {
            'weekly_plan': daily_plans,
            'nutrition_summary': self._calculate_weekly_nutrition(daily_plans)
        }
```

### 2. Caching Strategies

```python
from functools import wraps
from typing import Callable, Any
import hashlib
import json

def cache_ai_response(ttl_seconds: int = 3600):
    """Decorator to cache AI-generated responses"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Create cache key from function arguments
            cache_key = hashlib.sha256(
                json.dumps({
                    'function': func.__name__,
                    'args': args,
                    'kwargs': kwargs
                }, sort_keys=True).encode()
            ).hexdigest()

            # Check cache first
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                return cached_result

            # Generate and cache result
            result = await func(*args, **kwargs)
            await self.cache_service.set(cache_key, result, ttl_seconds)

            return result
        return wrapper
    return decorator
```

## Environment Configuration

### 1. Environment-Specific Settings

```python
# src/config/environments.py
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any

class Environment(Enum):
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"

@dataclass
class EnvironmentConfig:
    """Environment-specific configuration"""

    # Database settings
    dynamodb_table_prefix: str
    enable_point_in_time_recovery: bool

    # AI service settings
    bedrock_model_id: str
    prompt_cache_ttl: int

    # Monitoring settings
    log_level: str
    enable_xray_tracing: bool

    # Cost optimization
    enable_cost_optimization: bool
    monthly_budget_limit: float

def get_environment_config(env: Environment) -> EnvironmentConfig:
    """Get configuration for specific environment"""
    configs = {
        Environment.DEVELOPMENT: EnvironmentConfig(
            dynamodb_table_prefix="ai-nutritionist-dev",
            enable_point_in_time_recovery=False,
            bedrock_model_id="amazon.titan-text-express-v1",
            prompt_cache_ttl=3600,
            log_level="DEBUG",
            enable_xray_tracing=False,
            enable_cost_optimization=True,
            monthly_budget_limit=50.0
        ),
        Environment.PRODUCTION: EnvironmentConfig(
            dynamodb_table_prefix="ai-nutritionist-prod",
            enable_point_in_time_recovery=True,
            bedrock_model_id="anthropic.claude-3-haiku-20240307-v1:0",
            prompt_cache_ttl=7200,
            log_level="INFO",
            enable_xray_tracing=True,
            enable_cost_optimization=True,
            monthly_budget_limit=500.0
        )
    }
    return configs[env]
```

## Security Best Practices

### 1. Input Validation

```python
from pydantic import BaseModel, validator, Field
from typing import Optional, List
from enum import Enum

class DietaryRestriction(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    PALEO = "paleo"

class MealPlanRequest(BaseModel):
    """Validated request for meal plan generation"""

    user_id: str = Field(..., regex=r'^[a-zA-Z0-9_-]+$', max_length=50)
    dietary_restrictions: Optional[List[DietaryRestriction]] = []
    budget_limit: Optional[float] = Field(None, gt=0, le=1000)
    servings: int = Field(default=4, gt=0, le=12)

    @validator('dietary_restrictions')
    def validate_restrictions(cls, v):
        if len(v) > 5:
            raise ValueError('Maximum 5 dietary restrictions allowed')
        return v
```

### 2. Secret Management

```python
import boto3
from typing import Optional
from functools import lru_cache

class SecretManager:
    """Secure secret management using AWS Systems Manager"""

    def __init__(self):
        self.ssm_client = boto3.client('ssm')

    @lru_cache(maxsize=100)
    def get_secret(self, parameter_name: str) -> str:
        """Retrieve and cache secret from Parameter Store"""
        try:
            response = self.ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            return response['Parameter']['Value']
        except Exception as e:
            raise SecretRetrievalError(f"Failed to retrieve {parameter_name}: {str(e)}")
```

## AI Service Integration

### 1. Bedrock Service Wrapper

```python
import boto3
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AIRequest:
    """Structured request for AI service"""
    prompt: str
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: Optional[str] = None

class BedrockAIService:
    """AWS Bedrock AI service integration"""

    def __init__(self, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.model_id = model_id

    async def generate_response(self, request: AIRequest) -> Dict[str, Any]:
        """Generate AI response using Bedrock"""

        # Prepare request payload
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": request.prompt
                }
            ]
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        # Invoke model
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(payload)
        )

        # Parse response
        result = json.loads(response['body'].read())
        return {
            'content': result['content'][0]['text'],
            'usage': result.get('usage', {}),
            'model': self.model_id
        }
```

This configuration and guide will optimize your codebase for GitHub Codex integration, providing:

1. **Enhanced AI Understanding**: Clear structure and consistent patterns
2. **Better Code Generation**: Type hints and documentation standards
3. **AWS-Specific Optimization**: Service integration patterns
4. **Testing Framework**: Comprehensive test patterns for AI systems
5. **Security Best Practices**: Input validation and secret management
6. **Performance Optimization**: Async patterns and caching strategies

The updated `config.toml` includes project-specific settings that will help Codex understand your AWS serverless architecture and provide more relevant suggestions.
