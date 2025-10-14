"""
Error handling utilities for the AI Nutritionist application
"""

import logging
import functools
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class APIError(Exception):
    """Base exception for API-related errors"""
    def __init__(self, message: str, status_code: int = 500, error_type: str = "api_error"):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(self.message)


class ValidationError(APIError):
    """Exception for validation errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_type="validation_error")


class AuthenticationError(APIError):
    """Exception for authentication errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=401, error_type="authentication_error")


class AuthorizationError(APIError):
    """Exception for authorization errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=403, error_type="authorization_error")


class ResourceNotFoundError(APIError):
    """Exception for resource not found errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=404, error_type="not_found_error")


class RateLimitError(APIError):
    """Exception for rate limit errors"""
    def __init__(self, message: str):
        super().__init__(message, status_code=429, error_type="rate_limit_error")


class ExternalServiceError(APIError):
    """Exception for external service errors"""
    def __init__(self, message: str, service_name: str = "unknown"):
        self.service_name = service_name
        super().__init__(message, status_code=502, error_type="external_service_error")


def handle_exceptions(
    return_default: Any = None,
    error_severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    log_error: bool = True,
    raise_on_critical: bool = True
):
    """
    Decorator for handling exceptions in service methods
    
    Args:
        return_default: Default value to return on exception
        error_severity: Severity level of the error
        log_error: Whether to log the error
        raise_on_critical: Whether to re-raise critical errors
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    if error_severity == ErrorSeverity.CRITICAL:
                        logger.critical(f"Critical error in {func.__name__}: {str(e)}", exc_info=True)
                    elif error_severity == ErrorSeverity.HIGH:
                        logger.error(f"High severity error in {func.__name__}: {str(e)}", exc_info=True)
                    elif error_severity == ErrorSeverity.MEDIUM:
                        logger.warning(f"Medium severity error in {func.__name__}: {str(e)}")
                    else:  # LOW
                        logger.info(f"Low severity error in {func.__name__}: {str(e)}")
                
                # Re-raise critical errors if configured to do so
                if error_severity == ErrorSeverity.CRITICAL and raise_on_critical:
                    raise
                
                # Return default value for non-critical errors
                return return_default
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    if error_severity == ErrorSeverity.CRITICAL:
                        logger.critical(f"Critical error in {func.__name__}: {str(e)}", exc_info=True)
                    elif error_severity == ErrorSeverity.HIGH:
                        logger.error(f"High severity error in {func.__name__}: {str(e)}", exc_info=True)
                    elif error_severity == ErrorSeverity.MEDIUM:
                        logger.warning(f"Medium severity error in {func.__name__}: {str(e)}")
                    else:  # LOW
                        logger.info(f"Low severity error in {func.__name__}: {str(e)}")
                
                # Re-raise critical errors if configured to do so
                if error_severity == ErrorSeverity.CRITICAL and raise_on_critical:
                    raise
                
                # Return default value for non-critical errors
                return return_default
        
        # Return appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_and_return_error_response(
    error: Exception,
    default_message: str = "An error occurred",
    include_details: bool = False
) -> dict:
    """
    Log an error and return a standardized error response
    
    Args:
        error: The exception that occurred
        default_message: Default error message if none provided
        include_details: Whether to include error details in response
    
    Returns:
        Standardized error response dictionary
    """
    error_message = str(error) if str(error) else default_message
    
    # Log the error
    if isinstance(error, APIError):
        logger.warning(f"API Error: {error_message}")
    else:
        logger.error(f"Unexpected error: {error_message}", exc_info=True)
    
    # Build response
    response = {
        "success": False,
        "error": error_message,
        "error_type": getattr(error, 'error_type', 'unknown_error')
    }
    
    if include_details and hasattr(error, '__dict__'):
        response["details"] = {
            k: v for k, v in error.__dict__.items() 
            if not k.startswith('_') and not callable(v)
        }
    
    return response


# Import asyncio at module level to avoid issues in decorators
import asyncio
