"""FastAPI integration examples for the comprehensive validation system."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import ValidationError

from src.core.validation.base import APIRequestModel, APIResponseModel
from src.models.validation.user_models import (
    UserProfile, UserCreateRequest, UserUpdateRequest, UserHealthMetrics
)
from src.models.validation.meal_planning_models import (
    MealPlan, MealPlanCreateRequest, Recipe, RecipeCreateRequest
)
from src.models.validation.monetization_models import (
    Subscription, SubscriptionCreateRequest, Payment, UsageMetrics
)
from src.services.validation_service import (
    get_validation_service, validate_user_data, validate_meal_plan_data
)


# FastAPI router for validation examples
validation_router = APIRouter(prefix="/api/v1", tags=["validation-examples"])
security = HTTPBearer()


# Custom exception handler for validation errors
def handle_validation_error(e: ValidationError) -> HTTPException:
    """Convert Pydantic ValidationError to FastAPI HTTPException."""
    from src.core.validation.errors import ValidationErrorFormatter
    
    user_friendly_error = ValidationErrorFormatter.format_for_user(e)
    
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": "Validation failed",
            "errors": user_friendly_error.get("errors", []),
            "fields": user_friendly_error.get("field_errors", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Dependency for validation service
def get_validation_service_dependency():
    """FastAPI dependency for validation service."""
    return get_validation_service()


# User management endpoints with validation
@validation_router.post("/users", response_model=APIResponseModel[UserProfile])
async def create_user(
    request: UserCreateRequest,
    validation_service = Depends(get_validation_service_dependency)
):
    """Create a new user with comprehensive validation.
    
    This endpoint demonstrates:
    - Request validation using Pydantic models
    - Custom validation rules (email, phone, password strength)
    - Cross-field validation (age vs date of birth consistency)
    - User-friendly error messages
    """
    try:
        # Validate the request data
        validated_data = validation_service.validate_model(
            UserCreateRequest, 
            request.model_dump(),
            user_friendly_errors=True
        )
        
        # Simulate user creation (replace with actual business logic)
        user_profile = UserProfile(
            user_id=UUID("12345678-1234-5678-9012-123456789012"),
            email=validated_data.email,
            phone_number=validated_data.phone_number,
            first_name=validated_data.first_name,
            last_name=validated_data.last_name,
            date_of_birth=validated_data.date_of_birth,
            gender=validated_data.gender,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
            subscription_tier="free"
        )
        
        return APIResponseModel[UserProfile](
            success=True,
            data=user_profile,
            message="User created successfully",
            timestamp=datetime.utcnow()
        )
    
    except ValidationError as e:
        raise handle_validation_error(e)


@validation_router.patch("/users/{user_id}", response_model=APIResponseModel[UserProfile])
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    validation_service = Depends(get_validation_service_dependency)
):
    """Update user with partial validation.
    
    This endpoint demonstrates:
    - Partial validation for updates (only validate provided fields)
    - UUID validation
    - Conditional validation based on field presence
    """
    try:
        # Validate the update request with partial validation
        validated_data = validation_service.validate_model(
            UserUpdateRequest,
            request.model_dump(exclude_unset=True),
            partial=True,
            user_friendly_errors=True
        )
        
        # Simulate user update (replace with actual business logic)
        updated_user = UserProfile(
            user_id=user_id,
            email=validated_data.email or "existing@example.com",
            first_name=validated_data.first_name or "Existing",
            last_name=validated_data.last_name or "User",
            date_of_birth=validated_data.date_of_birth or datetime(1990, 1, 1).date(),
            gender=validated_data.gender or "other",
            created_at=datetime(2023, 1, 1),
            updated_at=datetime.utcnow(),
            is_active=True,
            subscription_tier="free"
        )
        
        return APIResponseModel[UserProfile](
            success=True,
            data=updated_user,
            message="User updated successfully",
            timestamp=datetime.utcnow()
        )
    
    except ValidationError as e:
        raise handle_validation_error(e)


@validation_router.post("/users/{user_id}/health-metrics", response_model=APIResponseModel[UserHealthMetrics])
async def update_health_metrics(
    user_id: UUID,
    request: UserHealthMetrics,
    validation_service = Depends(get_validation_service_dependency)
):
    """Update user health metrics with nutritional validation.
    
    This endpoint demonstrates:
    - Complex validation for health data
    - Range validation for weight, height, BMI
    - Consistency validation between metrics
    """
    try:
        # Validate health metrics
        validated_metrics = validation_service.validate_model(
            UserHealthMetrics,
            request.model_dump(),
            user_friendly_errors=True
        )
        
        return APIResponseModel[UserHealthMetrics](
            success=True,
            data=validated_metrics,
            message="Health metrics updated successfully",
            timestamp=datetime.utcnow()
        )
    
    except ValidationError as e:
        raise handle_validation_error(e)


# Meal planning endpoints with validation
@validation_router.post("/meal-plans", response_model=APIResponseModel[MealPlan])
async def create_meal_plan(
    request: MealPlanCreateRequest,
    validation_service = Depends(get_validation_service_dependency)
):
    """Create a meal plan with comprehensive nutrition validation.
    
    This endpoint demonstrates:
    - Complex nested validation (meal plan -> meals -> recipes -> ingredients)
    - Nutritional consistency validation
    - Business rule validation (calorie targets, dietary restrictions)
    """
    try:
        # Validate the meal plan request
        validated_data = validation_service.validate_model(
            MealPlanCreateRequest,
            request.model_dump(),
            user_friendly_errors=True
        )
        
        # Simulate meal plan creation (replace with actual business logic)
        meal_plan = MealPlan(
            meal_plan_id=UUID("87654321-4321-8765-2109-876543210987"),
            user_id=validated_data.user_id,
            name=validated_data.name,
            description=validated_data.description,
            start_date=validated_data.start_date,
            end_date=validated_data.end_date,
            meals=[],  # Would be populated with actual meals
            dietary_restrictions=validated_data.dietary_restrictions,
            daily_calorie_target=validated_data.daily_calorie_target,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
            compliance_score=0.95
        )
        
        return APIResponseModel[MealPlan](
            success=True,
            data=meal_plan,
            message="Meal plan created successfully",
            timestamp=datetime.utcnow()
        )
    
    except ValidationError as e:
        raise handle_validation_error(e)


@validation_router.post("/recipes", response_model=APIResponseModel[Recipe])
async def create_recipe(
    request: RecipeCreateRequest,
    validation_service = Depends(get_validation_service_dependency)
):
    """Create a recipe with ingredient and nutrition validation.
    
    This endpoint demonstrates:
    - Ingredient validation with quantities and units
    - Nutrition calculation validation
    - Preparation time and difficulty validation
    """
    try:
        # Validate the recipe request
        validated_data = validation_service.validate_model(
            RecipeCreateRequest,
            request.model_dump(),
            user_friendly_errors=True
        )
        
        # Simulate recipe creation
        recipe = Recipe(
            recipe_id=UUID("11111111-2222-3333-4444-555555555555"),
            name=validated_data.name,
            description=validated_data.description,
            ingredients=validated_data.ingredients,
            instructions=validated_data.instructions,
            prep_time_minutes=validated_data.prep_time_minutes,
            cook_time_minutes=validated_data.cook_time_minutes,
            servings=validated_data.servings,
            difficulty_level=validated_data.difficulty_level,
            cuisine_type=validated_data.cuisine_type,
            meal_type=validated_data.meal_type,
            dietary_tags=validated_data.dietary_tags,
            nutrition_info=validated_data.nutrition_info,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=validated_data.created_by,
            is_public=validated_data.is_public,
            rating=4.5,
            rating_count=10
        )
        
        return APIResponseModel[Recipe](
            success=True,
            data=recipe,
            message="Recipe created successfully",
            timestamp=datetime.utcnow()
        )
    
    except ValidationError as e:
        raise handle_validation_error(e)


# Bulk validation endpoint
@validation_router.post("/users/bulk", response_model=APIResponseModel[List[Dict[str, Any]]])
async def bulk_create_users(
    requests: List[UserCreateRequest],
    validation_service = Depends(get_validation_service_dependency)
):
    """Bulk create users with efficient validation.
    
    This endpoint demonstrates:
    - Bulk validation for performance
    - Error handling for batch operations
    - Performance monitoring and caching
    """
    try:
        # Convert requests to dictionaries for bulk validation
        data_list = [request.model_dump() for request in requests]
        
        # Perform bulk validation
        results = validation_service.validate_bulk(
            UserCreateRequest,
            data_list,
            stop_on_error=False,
            user_friendly_errors=True
        )
        
        # Process results
        successful_users = []
        failed_validations = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_validations.append({
                    "index": i,
                    "error": str(result)
                })
            else:
                successful_users.append({
                    "index": i,
                    "user_id": str(UUID("12345678-1234-5678-9012-123456789012")),
                    "email": result.email
                })
        
        return APIResponseModel[List[Dict[str, Any]]](
            success=len(failed_validations) == 0,
            data={
                "successful": successful_users,
                "failed": failed_validations,
                "summary": {
                    "total": len(requests),
                    "successful_count": len(successful_users),
                    "failed_count": len(failed_validations)
                }
            },
            message=f"Bulk validation completed: {len(successful_users)} successful, {len(failed_validations)} failed",
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk validation failed: {str(e)}"
        )


# Validation utility endpoints
@validation_router.get("/validation/schema/{model_name}")
async def get_model_schema(
    model_name: str,
    validation_service = Depends(get_validation_service_dependency)
):
    """Get JSON schema for a validation model.
    
    This endpoint demonstrates:
    - Dynamic schema retrieval
    - Model introspection
    - API documentation support
    """
    model_mapping = {
        "user": UserProfile,
        "user_create": UserCreateRequest,
        "user_update": UserUpdateRequest,
        "health_metrics": UserHealthMetrics,
        "meal_plan": MealPlan,
        "meal_plan_create": MealPlanCreateRequest,
        "recipe": Recipe,
        "recipe_create": RecipeCreateRequest,
        "subscription": Subscription,
        "subscription_create": SubscriptionCreateRequest,
    }
    
    if model_name not in model_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found"
        )
    
    model_class = model_mapping[model_name]
    schema = validation_service.get_model_schema(model_class)
    
    return {
        "model_name": model_name,
        "schema": schema,
        "timestamp": datetime.utcnow().isoformat()
    }


@validation_router.get("/validation/stats")
async def get_validation_stats(
    validation_service = Depends(get_validation_service_dependency)
):
    """Get validation performance statistics.
    
    This endpoint demonstrates:
    - Performance monitoring
    - Cache statistics
    - Validation metrics
    """
    stats = validation_service.get_performance_stats()
    
    return {
        "validation_stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@validation_router.post("/validation/recommendations")
async def get_validation_recommendations(
    model_name: str,
    data: Dict[str, Any],
    validation_service = Depends(get_validation_service_dependency)
):
    """Get validation recommendations for improving data quality.
    
    This endpoint demonstrates:
    - Data quality analysis
    - Validation recommendations
    - Proactive error prevention
    """
    model_mapping = {
        "user": UserProfile,
        "meal_plan": MealPlan,
        "recipe": Recipe,
    }
    
    if model_name not in model_mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found"
        )
    
    model_class = model_mapping[model_name]
    recommendations = validation_service.get_validation_recommendations(model_class, data)
    
    return {
        "model_name": model_name,
        "recommendations": recommendations,
        "data_quality_score": max(0, 100 - len(recommendations) * 10),
        "timestamp": datetime.utcnow().isoformat()
    }


# Field-level validation endpoint
@validation_router.post("/validation/field")
async def validate_field(
    field_name: str,
    value: Any,
    validator_name: str,
    validation_service = Depends(get_validation_service_dependency)
):
    """Validate a single field using a specific validator.
    
    This endpoint demonstrates:
    - Field-level validation
    - Real-time validation for forms
    - Custom validator usage
    """
    try:
        validated_value = validation_service.validate_field(
            field_name=field_name,
            value=value,
            validator_name=validator_name
        )
        
        return {
            "field_name": field_name,
            "original_value": value,
            "validated_value": validated_value,
            "is_valid": True,
            "validator_used": validator_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        return {
            "field_name": field_name,
            "original_value": value,
            "is_valid": False,
            "error": str(e),
            "validator_used": validator_name,
            "timestamp": datetime.utcnow().isoformat()
        }


# Export the router
__all__ = ["validation_router"]
