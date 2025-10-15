"""Validation types and utilities.

This module provides types and utilities for data validation.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Callable

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from .common import T, ErrorMessage, ErrorDetails
from .result import Result, Success, Failure, AppError

# Validation type variables
TValue = TypeVar('TValue')

@dataclass(frozen=True)
class ValidationIssue:
    """Individual validation issue."""
    
    field: str
    message: ErrorMessage
    code: str
    value: Any = None
    details: Optional[ErrorDetails] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {
            'field': self.field,
            'message': self.message,
            'code': self.code
        }
        if self.value is not None:
            result['value'] = self.value
        if self.details:
            result['details'] = self.details
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationIssue:
        """Create ValidationIssue from dictionary."""
        return cls(
            field=data['field'],
            message=data['message'],
            code=data['code'],
            value=data.get('value'),
            details=data.get('details')
        )

@dataclass
class ValidationResult:
    """Result of validation with any issues found."""
    
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        # Ensure consistency
        if self.is_valid and self.issues:
            self.is_valid = False
        elif not self.is_valid and not self.issues:
            # Add a generic issue if invalid but no specific issues
            self.issues = [ValidationIssue(
                field='',
                message='Validation failed',
                code='validation_error'
            )]
    
    @property
    def is_invalid(self) -> bool:
        """Check if validation failed."""
        return not self.is_valid
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue."""
        self.issues.append(issue)
        self.is_valid = False
    
    def add_field_issue(
        self,
        field: str,
        message: ErrorMessage,
        code: str = 'invalid',
        value: Any = None,
        details: Optional[ErrorDetails] = None
    ) -> None:
        """Add a field-specific validation issue."""
        issue = ValidationIssue(
            field=field,
            message=message,
            code=code,
            value=value,
            details=details
        )
        self.add_issue(issue)
    
    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge another ValidationResult into this one."""
        if other.is_invalid:
            self.issues.extend(other.issues)
            self.is_valid = False
        return self
    
    def get_issues_for_field(self, field: str) -> List[ValidationIssue]:
        """Get all issues for a specific field."""
        return [issue for issue in self.issues if issue.field == field]
    
    def has_field_issues(self, field: str) -> bool:
        """Check if field has validation issues."""
        return any(issue.field == field for issue in self.issues)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'is_valid': self.is_valid,
            'issues': [issue.to_dict() for issue in self.issues]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ValidationResult:
        """Create ValidationResult from dictionary."""
        issues = [ValidationIssue.from_dict(issue_data) for issue_data in data.get('issues', [])]
        return cls(
            is_valid=data['is_valid'],
            issues=issues
        )
    
    @classmethod
    def valid(cls) -> ValidationResult:
        """Create a valid ValidationResult."""
        return cls(is_valid=True)
    
    @classmethod
    def invalid(cls, issues: List[ValidationIssue]) -> ValidationResult:
        """Create an invalid ValidationResult with issues."""
        return cls(is_valid=False, issues=issues)
    
    @classmethod
    def field_error(
        cls,
        field: str,
        message: ErrorMessage,
        code: str = 'invalid',
        value: Any = None
    ) -> ValidationResult:
        """Create ValidationResult with single field error."""
        issue = ValidationIssue(field=field, message=message, code=code, value=value)
        return cls(is_valid=False, issues=[issue])

# Validator type
Validator: TypeAlias = Callable[[TValue], ValidationResult]

class ValidationError(AppError):
    """Extended validation error with structured issues."""
    
    def __init__(
        self,
        validation_result: ValidationResult,
        message: Optional[ErrorMessage] = None
    ) -> None:
        self.validation_result = validation_result
        
        if message is None:
            issue_count = len(validation_result.issues)
            message = f"Validation failed with {issue_count} issue{'s' if issue_count != 1 else ''}"
        
        details = {
            'issues': [issue.to_dict() for issue in validation_result.issues],
            'issue_count': len(validation_result.issues)
        }
        
        super().__init__(
            code='validation_error',
            message=message,
            details=details
        )

# Common validators
class Validators:
    """Collection of common validators."""
    
    @staticmethod
    def required(field_name: str = 'value') -> Validator[Any]:
        """Validate that value is not None or empty."""
        def validate(value: Any) -> ValidationResult:
            if value is None:
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} is required",
                    code='required'
                )
            if isinstance(value, str) and not value.strip():
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} cannot be empty",
                    code='empty'
                )
            if isinstance(value, (list, dict)) and len(value) == 0:
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} cannot be empty",
                    code='empty'
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def min_length(min_len: int, field_name: str = 'value') -> Validator[str]:
        """Validate minimum string length."""
        def validate(value: str) -> ValidationResult:
            if len(value) < min_len:
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} must be at least {min_len} characters",
                    code='min_length',
                    value=value
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def max_length(max_len: int, field_name: str = 'value') -> Validator[str]:
        """Validate maximum string length."""
        def validate(value: str) -> ValidationResult:
            if len(value) > max_len:
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} must be at most {max_len} characters",
                    code='max_length',
                    value=value
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def min_value(min_val: Union[int, float], field_name: str = 'value') -> Validator[Union[int, float]]:
        """Validate minimum numeric value."""
        def validate(value: Union[int, float]) -> ValidationResult:
            if value < min_val:
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} must be at least {min_val}",
                    code='min_value',
                    value=value
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def max_value(max_val: Union[int, float], field_name: str = 'value') -> Validator[Union[int, float]]:
        """Validate maximum numeric value."""
        def validate(value: Union[int, float]) -> ValidationResult:
            if value > max_val:
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} must be at most {max_val}",
                    code='max_value',
                    value=value
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def email(field_name: str = 'email') -> Validator[str]:
        """Validate email format."""
        import re
        pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        def validate(value: str) -> ValidationResult:
            if not pattern.match(value):
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} must be a valid email address",
                    code='invalid_email',
                    value=value
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def phone(field_name: str = 'phone') -> Validator[str]:
        """Validate phone number format."""
        import re
        # Basic phone validation - adjust as needed
        pattern = re.compile(r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$')
        
        def validate(value: str) -> ValidationResult:
            cleaned = value.replace(' ', '').replace('-', '').replace('.', '')
            if not pattern.match(cleaned):
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} must be a valid phone number",
                    code='invalid_phone',
                    value=value
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def one_of(allowed_values: List[Any], field_name: str = 'value') -> Validator[Any]:
        """Validate value is one of allowed values."""
        def validate(value: Any) -> ValidationResult:
            if value not in allowed_values:
                return ValidationResult.field_error(
                    field=field_name,
                    message=f"{field_name} must be one of: {', '.join(map(str, allowed_values))}",
                    code='invalid_choice',
                    value=value
                )
            return ValidationResult.valid()
        return validate
    
    @staticmethod
    def regex(pattern: str, field_name: str = 'value', message: Optional[str] = None) -> Validator[str]:
        """Validate value matches regex pattern."""
        import re
        compiled_pattern = re.compile(pattern)
        
        def validate(value: str) -> ValidationResult:
            if not compiled_pattern.match(value):
                error_message = message or f"{field_name} format is invalid"
                return ValidationResult.field_error(
                    field=field_name,
                    message=error_message,
                    code='invalid_format',
                    value=value
                )
            return ValidationResult.valid()
        return validate

def combine_validators(*validators: Validator[T]) -> Validator[T]:
    """Combine multiple validators into one."""
    def validate(value: T) -> ValidationResult:
        result = ValidationResult.valid()
        for validator in validators:
            validator_result = validator(value)
            result.merge(validator_result)
        return result
    return validate

def validate_field(
    value: T,
    validators: List[Validator[T]],
    field_name: str = 'value'
) -> ValidationResult:
    """Validate a single field with multiple validators."""
    result = ValidationResult.valid()
    for validator in validators:
        validator_result = validator(value)
        result.merge(validator_result)
    return result

def validate_dict(
    data: Dict[str, Any],
    field_validators: Dict[str, List[Validator[Any]]]
) -> ValidationResult:
    """Validate a dictionary of values."""
    result = ValidationResult.valid()
    
    for field_name, validators in field_validators.items():
        if field_name in data:
            field_result = validate_field(data[field_name], validators, field_name)
            result.merge(field_result)
        else:
            # Check if any validator is required
            for validator in validators:
                # This is a simple check - in practice you might want a more sophisticated way
                # to determine if a validator is a "required" validator
                if hasattr(validator, '__name__') and 'required' in validator.__name__:
                    result.add_field_issue(
                        field=field_name,
                        message=f"{field_name} is required",
                        code='required'
                    )
                    break
    
    return result

# Type aliases
FieldValidators: TypeAlias = Dict[str, List[Validator[Any]]]
ValidationFunction: TypeAlias = Callable[[Any], ValidationResult]

# Export all public types and functions
__all__ = [
    # Core types
    'ValidationIssue', 'ValidationResult', 'ValidationError',
    
    # Validator types
    'Validator', 'FieldValidators', 'ValidationFunction',
    
    # Validator utilities
    'Validators', 'combine_validators', 'validate_field', 'validate_dict',
]
