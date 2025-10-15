"""Comprehensive validation service that orchestrates all validation models and operations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from .base import BaseValidationModel, ValidationModelRegistry
from .validators import ValidatorRegistry
from .errors import ValidationErrorHandler, ValidationErrorFormatter, FieldValidationError
from .performance import PerformanceOptimizer, ValidationCache, BulkValidator

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class ValidationService:
    """Central service for all validation operations across the application."""
    
    def __init__(self, 
                 enable_caching: bool = True,
                 enable_performance_monitoring: bool = True,
                 cache_ttl_seconds: int = 300):
        self.enable_caching = enable_caching
        self.enable_performance_monitoring = enable_performance_monitoring
        self.cache = ValidationCache(ttl_seconds=cache_ttl_seconds) if enable_caching else None
        
        # Initialize performance monitoring
        if enable_performance_monitoring:
            self._performance_stats = {
                'validations_performed': 0,
                'validation_errors': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'average_validation_time_ms': 0.0
            }
        
        logger.info("ValidationService initialized", extra={
            'caching_enabled': enable_caching,
            'performance_monitoring': enable_performance_monitoring
        })
    
    def validate_model(self, 
                      model_class: Type[T], 
                      data: Dict[str, Any],
                      user_friendly_errors: bool = True,
                      partial: bool = False) -> T:
        """Validate data against a Pydantic model with comprehensive error handling.
        
        Args:
            model_class: The Pydantic model class to validate against
            data: The data to validate
            user_friendly_errors: Whether to return user-friendly error messages
            partial: Whether to perform partial validation (for updates)
        
        Returns:
            Validated model instance
        
        Raises:
            ValidationError: If validation fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Check cache first
            if self.cache and not partial:
                cached_result = self.cache.get(model_class, data)
                if cached_result:
                    self._update_performance_stats(cache_hit=True)
                    return cached_result
            
            # Perform validation
            if partial:
                # For partial validation, filter out None values
                filtered_data = {k: v for k, v in data.items() if v is not None}
                validated_instance = model_class.model_validate(filtered_data)
            else:
                validated_instance = model_class.model_validate(data)
            
            # Cache successful result
            if self.cache and not partial:
                self.cache.set(model_class, data, validated_instance)
            
            # Update performance stats
            validation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_performance_stats(
                validation_time_ms=validation_time,
                cache_hit=False
            )
            
            logger.debug(
                f"Validation successful: {model_class.__name__}",
                extra={
                    'model_class': model_class.__name__,
                    'field_count': len(data),
                    'validation_time_ms': validation_time,
                    'partial': partial
                }
            )
            
            return validated_instance
            
        except ValidationError as e:
            self._update_performance_stats(error=True)
            
            # Format error based on user preference
            if user_friendly_errors:
                formatted_error = ValidationErrorFormatter.format_for_user(e)
                logger.warning(
                    f"Validation failed: {model_class.__name__}",
                    extra={
                        'model_class': model_class.__name__,
                        'error_count': e.error_count(),
                        'user_friendly_error': formatted_error
                    }
                )
            else:
                formatted_error = ValidationErrorFormatter.format_for_developer(e)
                logger.warning(
                    f"Validation failed: {model_class.__name__}",
                    extra={
                        'model_class': model_class.__name__,
                        'error_details': formatted_error
                    }
                )
            
            raise e
        
        except Exception as e:
            self._update_performance_stats(error=True)
            ValidationErrorHandler.handle_init_error(e, model_class, data)
            raise
    
    def validate_field(self, 
                      field_name: str,
                      value: Any,
                      validator_name: str,
                      **validator_kwargs) -> Any:
        """Validate a single field using a registered validator.
        
        Args:
            field_name: Name of the field being validated
            value: Value to validate
            validator_name: Name of the validator to use
            **validator_kwargs: Additional arguments for the validator
        
        Returns:
            Validated value
        
        Raises:
            FieldValidationError: If validation fails
        """
        validator = ValidatorRegistry.get(validator_name)
        if not validator:
            raise ValueError(f"Validator '{validator_name}' not found")
        
        try:
            if validator_kwargs:
                return validator(value, **validator_kwargs)
            else:
                return validator(value)
        
        except ValueError as e:
            error = ValidationErrorHandler.handle_field_validation_error(
                field=field_name,
                value=value,
                error_message=str(e),
                error_code=validator_name
            )
            raise error
    
    def validate_bulk(self, 
                     model_class: Type[T], 
                     data_list: List[Dict[str, Any]],
                     stop_on_error: bool = False,
                     user_friendly_errors: bool = True) -> List[Union[T, Exception]]:
        """Validate multiple data instances efficiently.
        
        Args:
            model_class: The Pydantic model class to validate against
            data_list: List of data dictionaries to validate
            stop_on_error: Whether to stop on first error
            user_friendly_errors: Whether to return user-friendly error messages
        
        Returns:
            List of validated instances or exceptions
        """
        bulk_validator = BulkValidator(model_class)
        
        results = bulk_validator.validate_batch(
            data_list,
            stop_on_error=stop_on_error,
            use_cache=self.enable_caching
        )
        
        # Update performance stats
        successful_validations = sum(1 for r in results if not isinstance(r, Exception))
        failed_validations = len(results) - successful_validations
        
        self._update_performance_stats(
            bulk_validations=len(results),
            bulk_errors=failed_validations
        )
        
        logger.info(
            f"Bulk validation completed: {model_class.__name__}",
            extra={
                'model_class': model_class.__name__,
                'total_items': len(data_list),
                'successful': successful_validations,
                'failed': failed_validations
            }
        )
        
        return results
    
    def get_model_schema(self, model_class: Type[BaseModel]) -> Dict[str, Any]:
        """Get JSON schema for a model class.
        
        Args:
            model_class: The Pydantic model class
        
        Returns:
            JSON schema dictionary
        """
        return model_class.model_json_schema()
    
    def validate_against_schema(self, 
                               schema: Dict[str, Any], 
                               data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against a JSON schema.
        
        Args:
            schema: JSON schema to validate against
            data: Data to validate
        
        Returns:
            Validated data
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            import jsonschema
            jsonschema.validate(instance=data, schema=schema)
            return data
        except ImportError:
            logger.warning("jsonschema package not available for schema validation")
            return data
        except Exception as e:
            raise ValidationError(f"Schema validation failed: {e}")
    
    def get_validation_recommendations(self, 
                                     model_class: Type[BaseModel],
                                     data: Dict[str, Any]) -> List[str]:
        """Get validation recommendations for improving data quality.
        
        Args:
            model_class: The Pydantic model class
            data: Data to analyze
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        try:
            # Try validation to get specific errors
            model_class.model_validate(data)
        except ValidationError as e:
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                error_type = error['type']
                
                if error_type == 'missing':
                    recommendations.append(f"Field '{field}' is required but missing")
                elif error_type == 'string_too_short':
                    recommendations.append(f"Field '{field}' should be longer")
                elif error_type == 'string_too_long':
                    recommendations.append(f"Field '{field}' should be shorter")
                elif error_type == 'value_error':
                    recommendations.append(f"Field '{field}' has an invalid value")
                elif error_type == 'type_error':
                    recommendations.append(f"Field '{field}' has the wrong data type")
        
        # Add general recommendations
        schema = self.get_model_schema(model_class)
        if 'properties' in schema:
            for field_name, field_schema in schema['properties'].items():
                if field_name not in data:
                    if field_name not in schema.get('required', []):
                        recommendations.append(f"Consider providing optional field '{field_name}'")
        
        return recommendations
    
    def clear_cache(self) -> None:
        """Clear validation cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Validation cache cleared")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get validation performance statistics.
        
        Returns:
            Performance statistics dictionary
        """
        if not self.enable_performance_monitoring:
            return {}
        
        stats = self._performance_stats.copy()
        
        # Add cache statistics if available
        if self.cache:
            cache_stats = self.cache.get_stats()
            stats.update(cache_stats)
        
        # Add global performance statistics
        global_stats = PerformanceOptimizer.get_global_stats()
        stats.update(global_stats)
        
        return stats
    
    def _update_performance_stats(self, 
                                 validation_time_ms: Optional[float] = None,
                                 cache_hit: bool = False,
                                 error: bool = False,
                                 bulk_validations: Optional[int] = None,
                                 bulk_errors: Optional[int] = None) -> None:
        """Update internal performance statistics."""
        if not self.enable_performance_monitoring:
            return
        
        if bulk_validations:
            self._performance_stats['validations_performed'] += bulk_validations
        else:
            self._performance_stats['validations_performed'] += 1
        
        if bulk_errors:
            self._performance_stats['validation_errors'] += bulk_errors
        elif error:
            self._performance_stats['validation_errors'] += 1
        
        if cache_hit:
            self._performance_stats['cache_hits'] += 1
        elif validation_time_ms is not None:
            self._performance_stats['cache_misses'] += 1
            
            # Update average validation time
            current_avg = self._performance_stats['average_validation_time_ms']
            total_validations = self._performance_stats['validations_performed']
            
            if total_validations > 1:
                self._performance_stats['average_validation_time_ms'] = (
                    (current_avg * (total_validations - 1) + validation_time_ms) / total_validations
                )
            else:
                self._performance_stats['average_validation_time_ms'] = validation_time_ms


# Global validation service instance
_validation_service_instance: Optional[ValidationService] = None


def get_validation_service() -> ValidationService:
    """Get the global validation service instance."""
    global _validation_service_instance
    
    if _validation_service_instance is None:
        _validation_service_instance = ValidationService()
    
    return _validation_service_instance


def configure_validation_service(
    enable_caching: bool = True,
    enable_performance_monitoring: bool = True,
    cache_ttl_seconds: int = 300
) -> ValidationService:
    """Configure and return the global validation service instance."""
    global _validation_service_instance
    
    _validation_service_instance = ValidationService(
        enable_caching=enable_caching,
        enable_performance_monitoring=enable_performance_monitoring,
        cache_ttl_seconds=cache_ttl_seconds
    )
    
    return _validation_service_instance


# Convenience functions for common validation operations

def validate_user_data(data: Dict[str, Any], partial: bool = False) -> Any:
    """Validate user profile data."""
    from .user_models import UserProfile, UserUpdateRequest
    
    service = get_validation_service()
    model_class = UserUpdateRequest if partial else UserProfile
    return service.validate_model(model_class, data, partial=partial)


def validate_meal_plan_data(data: Dict[str, Any], partial: bool = False) -> Any:
    """Validate meal plan data."""
    from .meal_planning_models import MealPlan, MealPlanUpdateRequest
    
    service = get_validation_service()
    model_class = MealPlanUpdateRequest if partial else MealPlan
    return service.validate_model(model_class, data, partial=partial)


def validate_subscription_data(data: Dict[str, Any], partial: bool = False) -> Any:
    """Validate subscription data."""
    from .monetization_models import Subscription, SubscriptionUpdateRequest
    
    service = get_validation_service()
    model_class = SubscriptionUpdateRequest if partial else Subscription
    return service.validate_model(model_class, data, partial=partial)


def validate_config_data(data: Dict[str, Any]) -> Any:
    """Validate configuration data."""
    from .config_models import ApplicationConfig
    
    service = get_validation_service()
    return service.validate_model(ApplicationConfig, data)


# Export key classes and functions
__all__ = [
    'ValidationService',
    'get_validation_service',
    'configure_validation_service',
    'validate_user_data',
    'validate_meal_plan_data',
    'validate_subscription_data',
    'validate_config_data',
]
