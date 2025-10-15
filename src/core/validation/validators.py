"""Custom validators for comprehensive data validation."""

from __future__ import annotations

import re
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Pattern, Type, Union
from uuid import UUID

from pydantic import field_validator, model_validator
from pydantic.functional_validators import ValidationInfo

logger = logging.getLogger(__name__)


class ValidatorRegistry:
    """Registry for custom validators with caching and performance optimization."""
    
    _validators: Dict[str, Callable] = {}
    _compiled_patterns: Dict[str, Pattern] = {}
    
    @classmethod
    def register(cls, name: str, validator: Callable) -> None:
        """Register a custom validator."""
        cls._validators[name] = validator
        logger.debug(f"Registered validator: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[Callable]:
        """Get a validator by name."""
        return cls._validators.get(name)
    
    @classmethod
    def get_pattern(cls, name: str, pattern: str) -> Pattern:
        """Get compiled regex pattern with caching."""
        cache_key = f"{name}:{pattern}"
        if cache_key not in cls._compiled_patterns:
            cls._compiled_patterns[cache_key] = re.compile(pattern)
        return cls._compiled_patterns[cache_key]


class CustomValidators:
    """Collection of reusable custom validators."""
    
    @staticmethod
    def validate_email(v: str) -> str:
        """Enhanced email validation with security checks."""
        if not v:
            raise ValueError("Email cannot be empty")
        
        # Basic format validation
        pattern = ValidatorRegistry.get_pattern(
            'email',
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        if not pattern.match(v):
            raise ValueError("Invalid email format")
        
        # Security checks
        if len(v) > 254:  # RFC 5321 limit
            raise ValueError("Email address too long")
        
        local, domain = v.rsplit('@', 1)
        if len(local) > 64:  # RFC 5321 limit
            raise ValueError("Email local part too long")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.{2,}',  # Multiple consecutive dots
            r'^\.|\.$',  # Leading or trailing dots
            r'[<>"\'\\\x00-\x1f\x7f-\xff]',  # Control characters and quotes
        ]
        
        for pattern_str in suspicious_patterns:
            pattern = ValidatorRegistry.get_pattern(f'email_security_{pattern_str}', pattern_str)
            if pattern.search(v):
                raise ValueError("Email contains invalid characters")
        
        return v.lower().strip()
    
    @staticmethod
    def validate_phone_number(v: str, country_code: Optional[str] = None) -> str:
        """Validate phone number with international format support."""
        if not v:
            raise ValueError("Phone number cannot be empty")
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Basic validation
        if not cleaned:
            raise ValueError("Phone number must contain digits")
        
        # International format validation
        if cleaned.startswith('+'):
            if len(cleaned) < 8 or len(cleaned) > 16:
                raise ValueError("International phone number must be 8-16 digits including country code")
        else:
            # Domestic format validation
            if country_code == 'US':
                if len(cleaned) != 10:
                    raise ValueError("US phone number must be 10 digits")
                if cleaned[0] in '01':
                    raise ValueError("US phone number cannot start with 0 or 1")
            else:
                if len(cleaned) < 7 or len(cleaned) > 15:
                    raise ValueError("Phone number must be 7-15 digits")
        
        return cleaned
    
    @staticmethod
    def validate_password_strength(v: str) -> str:
        """Validate password strength with configurable requirements."""
        if not v:
            raise ValueError("Password cannot be empty")
        
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if len(v) > 128:
            raise ValueError("Password cannot exceed 128 characters")
        
        # Check for required character types
        requirements = {
            'lowercase': r'[a-z]',
            'uppercase': r'[A-Z]',
            'digit': r'\d',
            'special': r'[!@#$%^&*(),.?":{}|<>]'
        }
        
        missing_requirements = []
        for req_name, req_pattern in requirements.items():
            pattern = ValidatorRegistry.get_pattern(f'password_{req_name}', req_pattern)
            if not pattern.search(v):
                missing_requirements.append(req_name)
        
        if len(missing_requirements) > 1:  # Allow missing one requirement
            raise ValueError(f"Password must contain {' and '.join(missing_requirements)} characters")
        
        # Check for common weak patterns
        weak_patterns = [
            r'(.)\1{2,}',  # Repeated characters
            r'123|abc|qwe|password|admin',  # Common sequences
        ]
        
        for pattern_str in weak_patterns:
            pattern = ValidatorRegistry.get_pattern(f'password_weak_{pattern_str}', pattern_str)
            if pattern.search(v.lower()):
                raise ValueError("Password contains weak patterns")
        
        return v
    
    @staticmethod
    def validate_uuid(v: Union[str, UUID]) -> UUID:
        """Validate UUID with format standardization."""
        if isinstance(v, UUID):
            return v
        
        if not isinstance(v, str):
            raise ValueError("UUID must be a string or UUID object")
        
        try:
            return UUID(v)
        except ValueError:
            raise ValueError("Invalid UUID format")
    
    @staticmethod
    def validate_monetary_amount(v: Union[str, int, float, Decimal], 
                                currency: str = "USD") -> Decimal:
        """Validate monetary amounts with currency-specific rules."""
        try:
            amount = Decimal(str(v))
        except (ValueError, TypeError):
            raise ValueError("Invalid monetary amount format")
        
        if amount < 0:
            raise ValueError("Monetary amount cannot be negative")
        
        # Currency-specific validation
        if currency == "USD":
            if amount > Decimal('999999999.99'):
                raise ValueError("USD amount exceeds maximum limit")
            # Round to 2 decimal places
            amount = amount.quantize(Decimal('0.01'))
        elif currency == "JPY":
            if amount != amount.quantize(Decimal('1')):
                raise ValueError("JPY amounts must be whole numbers")
        
        return amount
    
    @staticmethod
    def validate_date_range(start_date: date, end_date: date) -> tuple[date, date]:
        """Validate date range with business logic."""
        if start_date > end_date:
            raise ValueError("Start date must be before end date")
        
        # Check for reasonable date ranges
        max_range_days = 365 * 5  # 5 years
        if (end_date - start_date).days > max_range_days:
            raise ValueError(f"Date range cannot exceed {max_range_days} days")
        
        return start_date, end_date
    
    @staticmethod
    def validate_nutritional_value(v: float, nutrient_type: str) -> float:
        """Validate nutritional values with nutrient-specific rules."""
        if v < 0:
            raise ValueError(f"{nutrient_type} cannot be negative")
        
        # Nutrient-specific validation
        limits = {
            'calories': 10000,  # kcal per serving
            'protein': 200,     # grams per serving
            'carbs': 500,       # grams per serving
            'fat': 200,         # grams per serving
            'fiber': 100,       # grams per serving
            'sugar': 200,       # grams per serving
            'sodium': 5000,     # mg per serving
            'cholesterol': 1000, # mg per serving
        }
        
        limit = limits.get(nutrient_type.lower())
        if limit and v > limit:
            raise ValueError(f"{nutrient_type} value {v} exceeds reasonable limit of {limit}")
        
        return round(v, 2)


class CrossFieldValidator:
    """Validator for cross-field validation logic."""
    
    @staticmethod
    def validate_user_profile_consistency(values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user profile field consistency."""
        birth_date = values.get('birth_date')
        age = values.get('age')
        
        if birth_date and age:
            calculated_age = (date.today() - birth_date).days // 365
            if abs(calculated_age - age) > 1:  # Allow 1 year variance
                raise ValueError("Age and birth date are inconsistent")
        
        # Validate weight/height/BMI consistency
        weight = values.get('weight_kg')
        height = values.get('height_cm')
        bmi = values.get('bmi')
        
        if weight and height and bmi:
            calculated_bmi = weight / ((height / 100) ** 2)
            if abs(calculated_bmi - bmi) > 1.0:
                raise ValueError("BMI is inconsistent with weight and height")
        
        return values
    
    @staticmethod
    def validate_meal_plan_consistency(values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate meal plan field consistency."""
        total_calories = values.get('total_calories')
        meals = values.get('meals', [])
        
        if total_calories and meals:
            calculated_calories = sum(meal.get('calories', 0) for meal in meals)
            tolerance = total_calories * 0.05  # 5% tolerance
            
            if abs(calculated_calories - total_calories) > tolerance:
                raise ValueError("Total calories don't match sum of meal calories")
        
        return values


class ConditionalValidator:
    """Validator for conditional validation logic."""
    
    @staticmethod
    def validate_subscription_requirements(values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate fields based on subscription tier."""
        subscription_tier = values.get('subscription_tier', 'free')
        
        # Premium features validation
        if subscription_tier == 'free':
            premium_fields = ['custom_macros', 'meal_prep_plans', 'nutrition_coaching']
            for field in premium_fields:
                if values.get(field):
                    raise ValueError(f"{field} requires premium subscription")
        
        return values
    
    @staticmethod
    def validate_dietary_restrictions(values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate dietary restriction combinations."""
        restrictions = values.get('dietary_restrictions', [])
        
        # Check for conflicting restrictions
        conflicts = [
            (['vegetarian', 'vegan'], 'Cannot be both vegetarian and vegan'),
            (['keto', 'high_carb'], 'Keto and high-carb diets conflict'),
        ]
        
        for conflict_set, message in conflicts:
            if all(restriction in restrictions for restriction in conflict_set):
                raise ValueError(message)
        
        return values


# Register all validators
ValidatorRegistry.register('email', CustomValidators.validate_email)
ValidatorRegistry.register('phone', CustomValidators.validate_phone_number)
ValidatorRegistry.register('password', CustomValidators.validate_password_strength)
ValidatorRegistry.register('uuid', CustomValidators.validate_uuid)
ValidatorRegistry.register('money', CustomValidators.validate_monetary_amount)
ValidatorRegistry.register('date_range', CustomValidators.validate_date_range)
ValidatorRegistry.register('nutrition', CustomValidators.validate_nutritional_value)
ValidatorRegistry.register('profile_consistency', CrossFieldValidator.validate_user_profile_consistency)
ValidatorRegistry.register('meal_consistency', CrossFieldValidator.validate_meal_plan_consistency)
ValidatorRegistry.register('subscription_requirements', ConditionalValidator.validate_subscription_requirements)
ValidatorRegistry.register('dietary_restrictions', ConditionalValidator.validate_dietary_restrictions)
