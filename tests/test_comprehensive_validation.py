"""Comprehensive tests for the Pydantic validation system."""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from uuid import UUID, uuid4

from pydantic import ValidationError

from src.core.validation.base import (
    BaseValidationModel, APIRequestModel, APIResponseModel, 
    DomainEntityModel, ConfigurationModel, EventModel
)
from src.core.validation.validators import (
    ValidatorRegistry, CustomValidators, CrossFieldValidator, ConditionalValidator
)
from src.core.validation.errors import (
    ValidationErrorHandler, ValidationErrorFormatter, FieldValidationError
)
from src.core.validation.performance import (
    ValidationCache, LazyValidator, BulkValidator, PerformanceOptimizer
)
from src.core.validation.fields import (
    SafeStr, SafeEmail, SafeUUID, ConstrainedStr, NutritionalValue, MonetaryAmount
)
from src.models.validation.user_models import (
    UserProfile, UserCreateRequest, UserUpdateRequest, UserHealthMetrics
)
from src.models.validation.meal_planning_models import (
    Recipe, MealPlan, MealPlanCreateRequest, NutritionInfo, Ingredient
)
from src.models.validation.monetization_models import (
    Subscription, Payment, UsageMetrics, AnalyticsEvent
)
from src.services.validation_service import ValidationService, get_validation_service


class TestBaseValidationModels:
    """Test base validation model functionality."""
    
    def test_base_validation_model_creation(self):
        """Test BaseValidationModel basic functionality."""
        class TestModel(BaseValidationModel):
            name: str
            age: int
        
        # Valid data
        model = TestModel(name="John", age=30)
        assert model.name == "John"
        assert model.age == 30
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'validation_metadata')
    
    def test_api_request_model(self):
        """Test APIRequestModel functionality."""
        class TestRequest(APIRequestModel):
            username: str
            email: str
        
        data = {"username": "testuser", "email": "test@example.com"}
        request = TestRequest(**data)
        
        assert request.username == "testuser"
        assert request.email == "test@example.com"
        assert request.request_id is not None
    
    def test_api_response_model(self):
        """Test APIResponseModel functionality."""
        data = {"id": 1, "name": "Test"}
        response = APIResponseModel[Dict[str, Any]](
            success=True,
            data=data,
            message="Success"
        )
        
        assert response.success is True
        assert response.data == data
        assert response.message == "Success"
        assert response.timestamp is not None
    
    def test_domain_entity_model(self):
        """Test DomainEntityModel functionality."""
        class TestEntity(DomainEntityModel):
            name: str
            value: int
        
        entity = TestEntity(
            entity_id=uuid4(),
            name="Test Entity",
            value=100
        )
        
        assert entity.name == "Test Entity"
        assert entity.value == 100
        assert entity.entity_id is not None
        assert entity.created_at is not None
        assert entity.updated_at is not None


class TestCustomValidators:
    """Test custom validation functionality."""
    
    def test_email_validator(self):
        """Test email validation."""
        # Valid emails
        assert CustomValidators.validate_email("test@example.com") == "test@example.com"
        assert CustomValidators.validate_email("user+tag@domain.co.uk") == "user+tag@domain.co.uk"
        
        # Invalid emails
        with pytest.raises(ValueError):
            CustomValidators.validate_email("invalid-email")
        
        with pytest.raises(ValueError):
            CustomValidators.validate_email("@domain.com")
    
    def test_phone_number_validator(self):
        """Test phone number validation."""
        # Valid phone numbers
        assert CustomValidators.validate_phone_number("+1234567890")
        assert CustomValidators.validate_phone_number("(555) 123-4567")
        
        # Invalid phone numbers
        with pytest.raises(ValueError):
            CustomValidators.validate_phone_number("123")
        
        with pytest.raises(ValueError):
            CustomValidators.validate_phone_number("invalid-phone")
    
    def test_password_strength_validator(self):
        """Test password strength validation."""
        # Strong passwords
        assert CustomValidators.validate_password_strength("StrongP@ss1") == "StrongP@ss1"
        assert CustomValidators.validate_password_strength("MySecure123!") == "MySecure123!"
        
        # Weak passwords
        with pytest.raises(ValueError):
            CustomValidators.validate_password_strength("weak")
        
        with pytest.raises(ValueError):
            CustomValidators.validate_password_strength("12345678")
    
    def test_nutritional_value_validator(self):
        """Test nutritional value validation."""
        # Valid values
        assert CustomValidators.validate_nutritional_value(100.5) == 100.5
        assert CustomValidators.validate_nutritional_value(0) == 0
        
        # Invalid values
        with pytest.raises(ValueError):
            CustomValidators.validate_nutritional_value(-10)
        
        with pytest.raises(ValueError):
            CustomValidators.validate_nutritional_value(10001)
    
    def test_validator_registry(self):
        """Test validator registry functionality."""
        # Test registration
        def custom_validator(value: str) -> str:
            if len(value) < 5:
                raise ValueError("Value too short")
            return value
        
        ValidatorRegistry.register("custom_test", custom_validator)
        
        # Test retrieval
        validator = ValidatorRegistry.get("custom_test")
        assert validator is not None
        assert validator("hello world") == "hello world"
        
        with pytest.raises(ValueError):
            validator("hi")


class TestErrorHandling:
    """Test error handling functionality."""
    
    def test_validation_error_formatter(self):
        """Test validation error formatting."""
        try:
            class TestModel(BaseValidationModel):
                name: str
                age: int
            
            TestModel(name="", age="invalid")
        except ValidationError as e:
            user_friendly = ValidationErrorFormatter.format_for_user(e)
            developer_friendly = ValidationErrorFormatter.format_for_developer(e)
            
            assert "errors" in user_friendly
            assert "field_errors" in user_friendly
            assert "error_details" in developer_friendly
    
    def test_field_validation_error(self):
        """Test field validation error handling."""
        error = ValidationErrorHandler.handle_field_validation_error(
            field="email",
            value="invalid-email",
            error_message="Invalid email format",
            error_code="email_validation"
        )
        
        assert isinstance(error, FieldValidationError)
        assert error.field == "email"
        assert error.value == "invalid-email"
        assert "Invalid email format" in str(error)


class TestPerformanceOptimization:
    """Test performance optimization features."""
    
    def test_validation_cache(self):
        """Test validation caching."""
        cache = ValidationCache(ttl_seconds=60)
        
        class TestModel(BaseValidationModel):
            name: str
            value: int
        
        data = {"name": "test", "value": 123}
        result = TestModel(**data)
        
        # Test cache set/get
        cache.set(TestModel, data, result)
        cached_result = cache.get(TestModel, data)
        
        assert cached_result is not None
        assert cached_result.name == result.name
        assert cached_result.value == result.value
    
    def test_bulk_validator(self):
        """Test bulk validation."""
        class TestModel(BaseValidationModel):
            name: str
            age: int
        
        bulk_validator = BulkValidator(TestModel)
        
        data_list = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
            {"name": "Invalid", "age": "not_a_number"}  # This should fail
        ]
        
        results = bulk_validator.validate_batch(data_list, stop_on_error=False)
        
        assert len(results) == 3
        assert isinstance(results[0], TestModel)
        assert isinstance(results[1], TestModel)
        assert isinstance(results[2], Exception)


class TestUserValidationModels:
    """Test user-related validation models."""
    
    def test_user_create_request_valid(self):
        """Test valid user creation request."""
        data = {
            "email": "test@example.com",
            "phone_number": "+1234567890",
            "password": "StrongP@ss1",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "gender": "male"
        }
        
        user_request = UserCreateRequest(**data)
        
        assert user_request.email == "test@example.com"
        assert user_request.first_name == "John"
        assert user_request.date_of_birth == date(1990, 1, 1)
    
    def test_user_create_request_invalid(self):
        """Test invalid user creation request."""
        # Missing required fields
        with pytest.raises(ValidationError):
            UserCreateRequest(email="test@example.com")
        
        # Invalid email
        with pytest.raises(ValidationError):
            UserCreateRequest(
                email="invalid-email",
                password="StrongP@ss1",
                first_name="John",
                last_name="Doe",
                date_of_birth="1990-01-01"
            )
        
        # Weak password
        with pytest.raises(ValidationError):
            UserCreateRequest(
                email="test@example.com",
                password="weak",
                first_name="John",
                last_name="Doe",
                date_of_birth="1990-01-01"
            )
    
    def test_user_health_metrics_validation(self):
        """Test user health metrics validation."""
        # Valid health metrics
        health_data = {
            "weight_kg": 70.5,
            "height_cm": 175.0,
            "body_fat_percentage": 15.5,
            "muscle_mass_kg": 55.0,
            "daily_calorie_goal": 2500,
            "activity_level": "moderate"
        }
        
        health_metrics = UserHealthMetrics(**health_data)
        
        assert health_metrics.weight_kg == 70.5
        assert health_metrics.height_cm == 175.0
        assert health_metrics.bmi == pytest.approx(23.02, rel=1e-2)
        
        # Invalid health metrics (negative weight)
        with pytest.raises(ValidationError):
            UserHealthMetrics(
                weight_kg=-10,
                height_cm=175.0,
                activity_level="moderate"
            )


class TestMealPlanningValidationModels:
    """Test meal planning validation models."""
    
    def test_nutrition_info_validation(self):
        """Test nutrition info validation."""
        nutrition_data = {
            "calories": 250.5,
            "protein_g": 20.0,
            "carbohydrates_g": 30.0,
            "fat_g": 8.5,
            "fiber_g": 5.0,
            "sugar_g": 10.0,
            "sodium_mg": 400.0
        }
        
        nutrition = NutritionInfo(**nutrition_data)
        
        assert nutrition.calories == 250.5
        assert nutrition.protein_g == 20.0
        assert nutrition.macronutrient_balance == pytest.approx(58.5, rel=1e-2)
        
        # Invalid nutrition (negative calories)
        with pytest.raises(ValidationError):
            NutritionInfo(calories=-100)
    
    def test_recipe_validation(self):
        """Test recipe validation."""
        recipe_data = {
            "recipe_id": str(uuid4()),
            "name": "Test Recipe",
            "description": "A test recipe",
            "ingredients": [
                {
                    "ingredient_id": str(uuid4()),
                    "name": "Chicken",
                    "quantity": 200.0,
                    "unit": "g",
                    "nutrition_per_100g": {
                        "calories": 165,
                        "protein_g": 31.0,
                        "carbohydrates_g": 0.0,
                        "fat_g": 3.6
                    }
                }
            ],
            "instructions": ["Cook the chicken"],
            "prep_time_minutes": 15,
            "cook_time_minutes": 20,
            "servings": 2,
            "difficulty_level": "easy",
            "cuisine_type": "american",
            "meal_type": "dinner",
            "nutrition_info": {
                "calories": 330,
                "protein_g": 62.0,
                "carbohydrates_g": 0.0,
                "fat_g": 7.2
            },
            "created_by": str(uuid4())
        }
        
        recipe = Recipe(**recipe_data)
        
        assert recipe.name == "Test Recipe"
        assert len(recipe.ingredients) == 1
        assert recipe.total_time_minutes == 35
    
    def test_meal_plan_validation(self):
        """Test meal plan validation."""
        meal_plan_data = {
            "meal_plan_id": str(uuid4()),
            "user_id": str(uuid4()),
            "name": "Test Meal Plan",
            "description": "A test meal plan",
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "meals": [],
            "daily_calorie_target": 2000,
            "dietary_restrictions": ["vegetarian"]
        }
        
        meal_plan = MealPlan(**meal_plan_data)
        
        assert meal_plan.name == "Test Meal Plan"
        assert meal_plan.duration_days == 7
        assert "vegetarian" in meal_plan.dietary_restrictions


class TestMonetizationValidationModels:
    """Test monetization validation models."""
    
    def test_subscription_validation(self):
        """Test subscription validation."""
        subscription_data = {
            "subscription_id": str(uuid4()),
            "user_id": str(uuid4()),
            "plan_type": "premium",
            "status": "active",
            "start_date": datetime.utcnow(),
            "billing_cycle": "monthly",
            "amount": "29.99",
            "currency": "USD"
        }
        
        subscription = Subscription(**subscription_data)
        
        assert subscription.plan_type == "premium"
        assert subscription.amount == Decimal("29.99")
        assert subscription.is_active is True
    
    def test_payment_validation(self):
        """Test payment validation."""
        payment_data = {
            "payment_id": str(uuid4()),
            "user_id": str(uuid4()),
            "subscription_id": str(uuid4()),
            "amount": "29.99",
            "currency": "USD",
            "payment_method": "credit_card",
            "status": "completed",
            "transaction_date": datetime.utcnow()
        }
        
        payment = Payment(**payment_data)
        
        assert payment.amount == Decimal("29.99")
        assert payment.status == "completed"
        assert payment.is_successful is True


class TestValidationService:
    """Test the comprehensive validation service."""
    
    def test_validation_service_initialization(self):
        """Test validation service initialization."""
        service = ValidationService(
            enable_caching=True,
            enable_performance_monitoring=True,
            cache_ttl_seconds=300
        )
        
        assert service.enable_caching is True
        assert service.enable_performance_monitoring is True
        assert service.cache is not None
    
    def test_model_validation(self):
        """Test model validation through service."""
        service = get_validation_service()
        
        # Valid data
        user_data = {
            "email": "test@example.com",
            "password": "StrongP@ss1",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01"
        }
        
        result = service.validate_model(UserCreateRequest, user_data)
        assert isinstance(result, UserCreateRequest)
        assert result.email == "test@example.com"
        
        # Invalid data
        invalid_data = {"email": "invalid-email"}
        
        with pytest.raises(ValidationError):
            service.validate_model(UserCreateRequest, invalid_data)
    
    def test_bulk_validation(self):
        """Test bulk validation through service."""
        service = get_validation_service()
        
        data_list = [
            {
                "email": "user1@example.com",
                "password": "StrongP@ss1",
                "first_name": "User",
                "last_name": "One",
                "date_of_birth": "1990-01-01"
            },
            {
                "email": "user2@example.com",
                "password": "StrongP@ss2",
                "first_name": "User",
                "last_name": "Two",
                "date_of_birth": "1991-01-01"
            },
            {
                "email": "invalid-email",  # This should fail
                "password": "weak",
                "first_name": "Invalid",
                "last_name": "User"
            }
        ]
        
        results = service.validate_bulk(
            UserCreateRequest,
            data_list,
            stop_on_error=False
        )
        
        assert len(results) == 3
        assert isinstance(results[0], UserCreateRequest)
        assert isinstance(results[1], UserCreateRequest)
        assert isinstance(results[2], Exception)
    
    def test_field_validation(self):
        """Test field validation through service."""
        service = get_validation_service()
        
        # Valid field
        result = service.validate_field(
            "email",
            "test@example.com",
            "email"
        )
        assert result == "test@example.com"
        
        # Invalid field
        with pytest.raises(Exception):
            service.validate_field(
                "email",
                "invalid-email",
                "email"
            )
    
    def test_performance_stats(self):
        """Test performance statistics."""
        service = ValidationService(enable_performance_monitoring=True)
        
        # Perform some validations
        user_data = {
            "email": "test@example.com",
            "password": "StrongP@ss1",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01"
        }
        
        service.validate_model(UserCreateRequest, user_data)
        
        stats = service.get_performance_stats()
        
        assert "validations_performed" in stats
        assert stats["validations_performed"] >= 1
    
    def test_validation_recommendations(self):
        """Test validation recommendations."""
        service = get_validation_service()
        
        # Incomplete data
        incomplete_data = {
            "email": "test@example.com",
            "first_name": "John"
            # Missing required fields
        }
        
        recommendations = service.get_validation_recommendations(
            UserCreateRequest,
            incomplete_data
        )
        
        assert len(recommendations) > 0
        assert any("required" in rec.lower() for rec in recommendations)


# Integration test
class TestValidationIntegration:
    """Test integration between different validation components."""
    
    def test_end_to_end_user_validation(self):
        """Test complete user validation flow."""
        service = get_validation_service()
        
        # Create user request
        user_data = {
            "email": "integration@example.com",
            "phone_number": "+1234567890",
            "password": "IntegrationTest123!",
            "first_name": "Integration",
            "last_name": "Test",
            "date_of_birth": "1985-06-15",
            "gender": "other"
        }
        
        # Validate user creation
        user_request = service.validate_model(UserCreateRequest, user_data)
        
        # Create user profile
        profile_data = {
            "user_id": str(uuid4()),
            "email": user_request.email,
            "first_name": user_request.first_name,
            "last_name": user_request.last_name,
            "date_of_birth": user_request.date_of_birth,
            "gender": user_request.gender,
            "phone_number": user_request.phone_number,
            "subscription_tier": "free",
            "is_active": True
        }
        
        user_profile = service.validate_model(UserProfile, profile_data)
        
        # Validate health metrics
        health_data = {
            "weight_kg": 75.0,
            "height_cm": 180.0,
            "activity_level": "active",
            "daily_calorie_goal": 2200
        }
        
        health_metrics = service.validate_model(UserHealthMetrics, health_data)
        
        # All validations should succeed
        assert user_request.email == "integration@example.com"
        assert user_profile.user_id is not None
        assert health_metrics.bmi == pytest.approx(23.15, rel=1e-2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
