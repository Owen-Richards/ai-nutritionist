"""Custom field types with built-in validation."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Pattern, Union
from uuid import UUID

from pydantic import Field, field_validator
from pydantic_core import PydanticCustomError

from .validators import CustomValidators, ValidatorRegistry


class SafeStr(str):
    """String type with automatic sanitization and validation."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> 'SafeStr':
        """Validate and sanitize string input."""
        if not isinstance(v, str):
            raise PydanticCustomError('string_type', 'String required', {'input': v})
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in v if ord(char) >= 32 or char in '\t\n\r')
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        return cls(sanitized)


class SafeEmail(str):
    """Email type with comprehensive validation."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> 'SafeEmail':
        """Validate email address."""
        if not isinstance(v, str):
            raise PydanticCustomError('string_type', 'String required', {'input': v})
        
        validated_email = CustomValidators.validate_email(v)
        return cls(validated_email)


class SafeUUID(UUID):
    """UUID type with validation and normalization."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> 'SafeUUID':
        """Validate UUID input."""
        validated_uuid = CustomValidators.validate_uuid(v)
        return cls(str(validated_uuid))


class SafeDateTime(datetime):
    """DateTime type with timezone and range validation."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v: Any) -> 'SafeDateTime':
        """Validate datetime input."""
        if isinstance(v, str):
            try:
                # Try ISO format first
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise PydanticCustomError(
                    'datetime_parsing',
                    'Invalid datetime format',
                    {'input': v}
                )
        elif isinstance(v, datetime):
            dt = v
        else:
            raise PydanticCustomError(
                'datetime_type',
                'DateTime or string required',
                {'input': v}
            )
        
        # Validate reasonable date range (1900-2100)
        if dt.year < 1900 or dt.year > 2100:
            raise PydanticCustomError(
                'datetime_range',
                'DateTime must be between 1900 and 2100',
                {'input': v}
            )
        
        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, dt.tzinfo)


def ConstrainedStr(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[Union[str, Pattern]] = None,
    strip_whitespace: bool = True,
    to_lower: bool = False,
    to_upper: bool = False
):
    """Factory function for constrained string fields."""
    
    def validate(v: Any) -> str:
        if not isinstance(v, str):
            raise PydanticCustomError('string_type', 'String required', {'input': v})
        
        # Apply transformations
        if strip_whitespace:
            v = v.strip()
        if to_lower:
            v = v.lower()
        if to_upper:
            v = v.upper()
        
        # Length validation
        if min_length is not None and len(v) < min_length:
            raise PydanticCustomError(
                'string_too_short',
                f'String too short (minimum {min_length} characters)',
                {'input': v, 'min_length': min_length}
            )
        
        if max_length is not None and len(v) > max_length:
            raise PydanticCustomError(
                'string_too_long',
                f'String too long (maximum {max_length} characters)',
                {'input': v, 'max_length': max_length}
            )
        
        # Pattern validation
        if pattern is not None:
            if isinstance(pattern, str):
                compiled_pattern = ValidatorRegistry.get_pattern('constrained_str', pattern)
            else:
                compiled_pattern = pattern
            
            if not compiled_pattern.match(v):
                raise PydanticCustomError(
                    'string_pattern_mismatch',
                    'String does not match pattern',
                    {'input': v, 'pattern': pattern}
                )
        
        return v
    
    return Field(validator=validate)


def ConstrainedInt(
    gt: Optional[int] = None,
    ge: Optional[int] = None,
    lt: Optional[int] = None,
    le: Optional[int] = None,
    multiple_of: Optional[int] = None
):
    """Factory function for constrained integer fields."""
    
    def validate(v: Any) -> int:
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise PydanticCustomError('int_parsing', 'Invalid integer', {'input': v})
        elif not isinstance(v, int):
            raise PydanticCustomError('int_type', 'Integer required', {'input': v})
        
        # Range validation
        if gt is not None and v <= gt:
            raise PydanticCustomError(
                'greater_than',
                f'Value must be greater than {gt}',
                {'input': v, 'gt': gt}
            )
        
        if ge is not None and v < ge:
            raise PydanticCustomError(
                'greater_than_equal',
                f'Value must be greater than or equal to {ge}',
                {'input': v, 'ge': ge}
            )
        
        if lt is not None and v >= lt:
            raise PydanticCustomError(
                'less_than',
                f'Value must be less than {lt}',
                {'input': v, 'lt': lt}
            )
        
        if le is not None and v > le:
            raise PydanticCustomError(
                'less_than_equal',
                f'Value must be less than or equal to {le}',
                {'input': v, 'le': le}
            )
        
        if multiple_of is not None and v % multiple_of != 0:
            raise PydanticCustomError(
                'multiple_of',
                f'Value must be a multiple of {multiple_of}',
                {'input': v, 'multiple_of': multiple_of}
            )
        
        return v
    
    return Field(validator=validate)


def ConstrainedFloat(
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    allow_inf_nan: bool = True,
    decimal_places: Optional[int] = None
):
    """Factory function for constrained float fields."""
    
    def validate(v: Any) -> float:
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                raise PydanticCustomError('float_parsing', 'Invalid float', {'input': v})
        elif not isinstance(v, (int, float)):
            raise PydanticCustomError('float_type', 'Float required', {'input': v})
        
        v = float(v)
        
        # Check for inf/nan
        if not allow_inf_nan:
            import math
            if math.isinf(v) or math.isnan(v):
                raise PydanticCustomError(
                    'finite_number',
                    'Finite number required',
                    {'input': v}
                )
        
        # Range validation
        if gt is not None and v <= gt:
            raise PydanticCustomError(
                'greater_than',
                f'Value must be greater than {gt}',
                {'input': v, 'gt': gt}
            )
        
        if ge is not None and v < ge:
            raise PydanticCustomError(
                'greater_than_equal',
                f'Value must be greater than or equal to {ge}',
                {'input': v, 'ge': ge}
            )
        
        if lt is not None and v >= lt:
            raise PydanticCustomError(
                'less_than',
                f'Value must be less than {lt}',
                {'input': v, 'lt': lt}
            )
        
        if le is not None and v > le:
            raise PydanticCustomError(
                'less_than_equal',
                f'Value must be less than or equal to {le}',
                {'input': v, 'le': le}
            )
        
        # Decimal places validation
        if decimal_places is not None:
            decimal_value = Decimal(str(v))
            if decimal_value.as_tuple().exponent < -decimal_places:
                raise PydanticCustomError(
                    'decimal_max_digits',
                    f'Value cannot have more than {decimal_places} decimal places',
                    {'input': v, 'decimal_places': decimal_places}
                )
        
        return v
    
    return Field(validator=validate)


def NutritionalValue(
    nutrient_type: str,
    min_value: float = 0.0,
    max_value: Optional[float] = None
):
    """Specialized field for nutritional values."""
    
    def validate(v: Any) -> float:
        if isinstance(v, str):
            try:
                v = float(v)
            except ValueError:
                raise PydanticCustomError('float_parsing', 'Invalid nutritional value', {'input': v})
        elif not isinstance(v, (int, float)):
            raise PydanticCustomError('float_type', 'Nutritional value must be a number', {'input': v})
        
        v = float(v)
        
        # Use custom nutritional validator
        validated_value = CustomValidators.validate_nutritional_value(v, nutrient_type)
        
        # Additional range checks
        if v < min_value:
            raise PydanticCustomError(
                'value_too_low',
                f'{nutrient_type} cannot be less than {min_value}',
                {'input': v, 'min_value': min_value}
            )
        
        if max_value is not None and v > max_value:
            raise PydanticCustomError(
                'value_too_high',
                f'{nutrient_type} cannot exceed {max_value}',
                {'input': v, 'max_value': max_value}
            )
        
        return validated_value
    
    return Field(validator=validate, description=f"Nutritional value for {nutrient_type}")


def MonetaryAmount(currency: str = "USD"):
    """Specialized field for monetary amounts."""
    
    def validate(v: Any) -> Decimal:
        return CustomValidators.validate_monetary_amount(v, currency)
    
    return Field(
        validator=validate,
        description=f"Monetary amount in {currency}",
        json_schema_extra={'currency': currency}
    )


def PhoneNumber(country_code: Optional[str] = None):
    """Specialized field for phone numbers."""
    
    def validate(v: Any) -> str:
        if not isinstance(v, str):
            raise PydanticCustomError('string_type', 'Phone number must be a string', {'input': v})
        
        return CustomValidators.validate_phone_number(v, country_code)
    
    return Field(
        validator=validate,
        description="Phone number with validation",
        json_schema_extra={'country_code': country_code}
    )
