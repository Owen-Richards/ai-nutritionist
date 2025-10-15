"""Validation error handling and formatting."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union
from uuid import uuid4

from pydantic import ValidationError
from pydantic_core import ErrorDetails

logger = logging.getLogger(__name__)


class ValidationErrorContext:
    """Context information for validation errors."""
    
    def __init__(self,
                 model_class: Optional[Type] = None,
                 field_name: Optional[str] = None,
                 input_data: Optional[Dict[str, Any]] = None,
                 user_id: Optional[str] = None,
                 request_id: Optional[str] = None):
        self.model_class = model_class
        self.field_name = field_name
        self.input_data = input_data
        self.user_id = user_id
        self.request_id = request_id
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid4())


class FieldValidationError(Exception):
    """Custom exception for field-level validation errors."""
    
    def __init__(self,
                 field: str,
                 message: str,
                 code: str,
                 value: Any = None,
                 context: Optional[ValidationErrorContext] = None):
        self.field = field
        self.message = message
        self.code = code
        self.value = value
        self.context = context
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            'field': self.field,
            'message': self.message,
            'code': self.code,
            'error_type': 'field_validation'
        }
        
        if self.value is not None:
            result['value'] = str(self.value)
        
        if self.context:
            result['error_id'] = self.context.error_id
            result['timestamp'] = self.context.timestamp.isoformat()
        
        return result


class CrossFieldValidationError(Exception):
    """Custom exception for cross-field validation errors."""
    
    def __init__(self,
                 fields: List[str],
                 message: str,
                 code: str,
                 values: Optional[Dict[str, Any]] = None,
                 context: Optional[ValidationErrorContext] = None):
        self.fields = fields
        self.message = message
        self.code = code
        self.values = values
        self.context = context
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            'fields': self.fields,
            'message': self.message,
            'code': self.code,
            'error_type': 'cross_field_validation'
        }
        
        if self.values:
            result['values'] = {k: str(v) for k, v in self.values.items()}
        
        if self.context:
            result['error_id'] = self.context.error_id
            result['timestamp'] = self.context.timestamp.isoformat()
        
        return result


class ValidationErrorFormatter:
    """Formats validation errors for different audiences."""
    
    @staticmethod
    def format_for_user(error: Union[FieldValidationError, CrossFieldValidationError, ValidationError]) -> Dict[str, Any]:
        """Format error for end users with friendly messages."""
        if isinstance(error, FieldValidationError):
            return {
                'message': ValidationErrorFormatter._humanize_field_error(error),
                'field': error.field,
                'code': error.code
            }
        
        elif isinstance(error, CrossFieldValidationError):
            return {
                'message': ValidationErrorFormatter._humanize_cross_field_error(error),
                'fields': error.fields,
                'code': error.code
            }
        
        elif isinstance(error, ValidationError):
            return ValidationErrorFormatter._format_pydantic_error_for_user(error)
        
        return {
            'message': 'A validation error occurred. Please check your input and try again.',
            'code': 'validation_error'
        }
    
    @staticmethod
    def format_for_developer(error: Union[FieldValidationError, CrossFieldValidationError, ValidationError]) -> Dict[str, Any]:
        """Format error for developers with detailed information."""
        base_info = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__
        }
        
        if isinstance(error, FieldValidationError):
            base_info.update(error.to_dict())
        
        elif isinstance(error, CrossFieldValidationError):
            base_info.update(error.to_dict())
        
        elif isinstance(error, ValidationError):
            base_info.update({
                'errors': error.errors(),
                'error_count': error.error_count(),
                'model': str(error.model) if hasattr(error, 'model') else None
            })
        
        return base_info
    
    @staticmethod
    def _humanize_field_error(error: FieldValidationError) -> str:
        """Convert field error to human-readable message."""
        field_display = error.field.replace('_', ' ').title()
        
        # Common error code mappings
        message_mappings = {
            'required': f'{field_display} is required.',
            'min_length': f'{field_display} is too short.',
            'max_length': f'{field_display} is too long.',
            'invalid_format': f'{field_display} format is invalid.',
            'invalid_email': f'Please enter a valid email address.',
            'invalid_phone': f'Please enter a valid phone number.',
            'weak_password': f'Password must be stronger. Include uppercase, lowercase, numbers, and special characters.',
            'invalid_date': f'Please enter a valid date.',
            'out_of_range': f'{field_display} value is outside the allowed range.',
        }
        
        return message_mappings.get(error.code, error.message)
    
    @staticmethod
    def _humanize_cross_field_error(error: CrossFieldValidationError) -> str:
        """Convert cross-field error to human-readable message."""
        fields_display = ', '.join(field.replace('_', ' ').title() for field in error.fields)
        
        message_mappings = {
            'inconsistent_data': f'The values for {fields_display} are inconsistent.',
            'conflicting_options': f'The selected options for {fields_display} conflict with each other.',
            'missing_dependency': f'{fields_display} are required together.',
        }
        
        return message_mappings.get(error.code, error.message)
    
    @staticmethod
    def _format_pydantic_error_for_user(error: ValidationError) -> Dict[str, Any]:
        """Format Pydantic validation error for users."""
        errors = error.errors()
        
        if len(errors) == 1:
            pydantic_error = errors[0]
            field = '.'.join(str(loc) for loc in pydantic_error['loc'])
            field_display = field.replace('_', ' ').title()
            
            error_type = pydantic_error['type']
            message_mappings = {
                'missing': f'{field_display} is required.',
                'string_too_short': f'{field_display} is too short.',
                'string_too_long': f'{field_display} is too long.',
                'value_error': f'{field_display} has an invalid value.',
                'type_error': f'{field_display} has the wrong type.',
            }
            
            message = message_mappings.get(error_type, f'{field_display} is invalid.')
            
            return {
                'message': message,
                'field': field,
                'code': error_type
            }
        
        else:
            return {
                'message': f'Please correct {len(errors)} validation errors and try again.',
                'code': 'multiple_validation_errors',
                'error_count': len(errors)
            }


class ValidationErrorHandler:
    """Centralized validation error handling."""
    
    @staticmethod
    def handle_init_error(error: Exception, 
                         model_class: Type,
                         input_data: Dict[str, Any]) -> None:
        """Handle errors during model initialization."""
        context = ValidationErrorContext(
            model_class=model_class,
            input_data=input_data
        )
        
        logger.error(
            f"Validation error in {model_class.__name__} initialization",
            extra={
                'error_type': type(error).__name__,
                'error_message': str(error),
                'model_class': model_class.__name__,
                'input_data_keys': list(input_data.keys()),
                'error_id': context.error_id
            }
        )
    
    @staticmethod
    def handle_partial_validation_error(error: Exception,
                                      model_class: Type,
                                      data: Dict[str, Any]) -> None:
        """Handle errors during partial validation."""
        context = ValidationErrorContext(
            model_class=model_class,
            input_data=data
        )
        
        logger.warning(
            f"Partial validation error in {model_class.__name__}",
            extra={
                'error_type': type(error).__name__,
                'error_message': str(error),
                'model_class': model_class.__name__,
                'validated_fields': list(data.keys()),
                'error_id': context.error_id
            }
        )
    
    @staticmethod
    def handle_field_validation_error(field: str,
                                    value: Any,
                                    error_message: str,
                                    error_code: str,
                                    model_class: Optional[Type] = None) -> FieldValidationError:
        """Create and log field validation error."""
        context = ValidationErrorContext(
            model_class=model_class,
            field_name=field
        )
        
        error = FieldValidationError(
            field=field,
            message=error_message,
            code=error_code,
            value=value,
            context=context
        )
        
        logger.warning(
            f"Field validation error: {field}",
            extra={
                'field': field,
                'value': str(value)[:100],  # Truncate long values
                'error_code': error_code,
                'error_message': error_message,
                'model_class': model_class.__name__ if model_class else None,
                'error_id': context.error_id
            }
        )
        
        return error
    
    @staticmethod
    def handle_cross_field_validation_error(fields: List[str],
                                          values: Dict[str, Any],
                                          error_message: str,
                                          error_code: str,
                                          model_class: Optional[Type] = None) -> CrossFieldValidationError:
        """Create and log cross-field validation error."""
        context = ValidationErrorContext(
            model_class=model_class,
            input_data=values
        )
        
        error = CrossFieldValidationError(
            fields=fields,
            message=error_message,
            code=error_code,
            values=values,
            context=context
        )
        
        logger.warning(
            f"Cross-field validation error: {', '.join(fields)}",
            extra={
                'fields': fields,
                'values': {k: str(v)[:100] for k, v in values.items()},  # Truncate long values
                'error_code': error_code,
                'error_message': error_message,
                'model_class': model_class.__name__ if model_class else None,
                'error_id': context.error_id
            }
        )
        
        return error
    
    @staticmethod
    def log_validation_success(model_class: Type,
                             field_count: int,
                             validation_time_ms: float) -> None:
        """Log successful validation for monitoring."""
        logger.debug(
            f"Validation successful: {model_class.__name__}",
            extra={
                'model_class': model_class.__name__,
                'field_count': field_count,
                'validation_time_ms': validation_time_ms,
                'status': 'success'
            }
        )
