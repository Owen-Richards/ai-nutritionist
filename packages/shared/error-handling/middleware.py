"""
Error Handling Middleware

Provides middleware and decorators for consistent error handling
across all services and endpoints.
"""

import asyncio
import functools
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union, List
from enum import Enum

from .exceptions import BaseError, InfrastructureError, ErrorSeverity
from .metrics import ErrorMetricsCollector
from .formatters import ErrorFormatter

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class ErrorHandlingMiddleware:
    """
    ASGI middleware for comprehensive error handling
    
    Catches all exceptions, formats responses, logs errors,
    and collects metrics.
    """
    
    def __init__(
        self,
        app,
        enable_metrics: bool = True,
        enable_user_friendly_messages: bool = True,
        include_error_details: bool = False,
        max_error_details_length: int = 500
    ):
        self.app = app
        self.enable_metrics = enable_metrics
        self.enable_user_friendly_messages = enable_user_friendly_messages
        self.include_error_details = include_error_details
        self.max_error_details_length = max_error_details_length
        
        self.metrics_collector = ErrorMetricsCollector() if enable_metrics else None
        self.error_formatter = ErrorFormatter()
        
    async def __call__(self, scope: Dict[str, Any], receive, send):
        """ASGI middleware entry point"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            await self._handle_error(exc, scope, send)
    
    async def _handle_error(self, exc: Exception, scope: Dict[str, Any], send):
        """Handle caught exception"""
        
        # Convert to BaseError if needed
        if not isinstance(exc, BaseError):
            exc = self._convert_to_base_error(exc)
        
        # Log the error
        self._log_error(exc, scope)
        
        # Collect metrics
        if self.metrics_collector:
            self.metrics_collector.record_error(exc, scope)
        
        # Format response
        response = self._format_error_response(exc)
        
        # Send HTTP response
        await send({
            "type": "http.response.start",
            "status": self._get_status_code(exc),
            "headers": [
                [b"content-type", b"application/json"],
                [b"x-error-id", exc.error_id.encode()],
            ],
        })
        
        await send({
            "type": "http.response.body",
            "body": json.dumps(response).encode(),
        })
    
    def _convert_to_base_error(self, exc: Exception) -> BaseError:
        """Convert regular exception to BaseError"""
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return InfrastructureError(
                message=str(exc),
                cause=exc,
                severity=ErrorSeverity.HIGH
            )
        
        return BaseError(
            message=str(exc),
            cause=exc,
            severity=ErrorSeverity.MEDIUM
        )
    
    def _log_error(self, error: BaseError, scope: Dict[str, Any]):
        """Log error with context"""
        log_data = {
            'error_id': error.error_id,
            'error_code': error.error_code,
            'message': error.message,
            'severity': error.severity.value,
            'category': error.category.value,
            'path': scope.get('path', ''),
            'method': scope.get('method', ''),
            'user_agent': dict(scope.get('headers', {})).get(b'user-agent', b'').decode(),
            'context': error.context
        }
        
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"Error {error.error_id}: {error.message}", extra=log_data)
        else:
            logger.warning(f"Error {error.error_id}: {error.message}", extra=log_data)
    
    def _format_error_response(self, error: BaseError) -> Dict[str, Any]:
        """Format error response for client"""
        response = {
            'error': True,
            'error_id': error.error_id,
            'error_code': error.error_code,
            'timestamp': error.timestamp.isoformat()
        }
        
        if self.enable_user_friendly_messages:
            response['message'] = error.user_message
        else:
            response['message'] = error.message
            
        if self.include_error_details:
            response['details'] = {
                'severity': error.severity.value,
                'category': error.category.value,
                'recoverable': error.recoverable,
                'retry_after': error.retry_after,
                'context': error.context
            }
            
            if len(error.message) <= self.max_error_details_length:
                response['details']['technical_message'] = error.message
        
        return response
    
    def _get_status_code(self, error: BaseError) -> int:
        """Get appropriate HTTP status code for error"""
        from .exceptions import (
            ValidationError, NotFoundError, AuthenticationError,
            AuthorizationError, RateLimitError, ConflictError
        )
        
        if isinstance(error, ValidationError):
            return 400
        elif isinstance(error, AuthenticationError):
            return 401
        elif isinstance(error, AuthorizationError):
            return 403
        elif isinstance(error, NotFoundError):
            return 404
        elif isinstance(error, ConflictError):
            return 409
        elif isinstance(error, RateLimitError):
            return 429
        elif error.severity == ErrorSeverity.CRITICAL:
            return 503
        else:
            return 500


def error_handler(
    log_errors: bool = True,
    collect_metrics: bool = True,
    reraise: bool = False,
    fallback_value: Any = None,
    fallback_function: Optional[Callable] = None
):
    """
    Decorator for function-level error handling
    
    Args:
        log_errors: Whether to log caught errors
        collect_metrics: Whether to collect error metrics
        reraise: Whether to reraise the error after handling
        fallback_value: Value to return if error occurs
        fallback_function: Function to call if error occurs
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # Convert to BaseError if needed
                if not isinstance(exc, BaseError):
                    exc = BaseError(
                        message=str(exc),
                        cause=exc,
                        context={'function': func.__name__}
                    )
                
                # Log error
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {exc.message}", extra=exc.to_dict())
                
                # Collect metrics
                if collect_metrics:
                    metrics_collector = ErrorMetricsCollector()
                    metrics_collector.record_function_error(func.__name__, exc)
                
                # Handle fallback
                if fallback_function:
                    return fallback_function(exc, *args, **kwargs)
                elif fallback_value is not None:
                    return fallback_value
                
                # Reraise if configured
                if reraise:
                    raise exc
                
                return None
                
        return wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Circuit breaker decorator to prevent cascading failures
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying again
        expected_exception: Exception type that triggers circuit breaker
    """
    def decorator(func: Callable) -> Callable:
        func._circuit_breaker_state = CircuitBreakerState.CLOSED
        func._failure_count = 0
        func._last_failure_time = None
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = datetime.utcnow()
            
            # Check if circuit is open
            if func._circuit_breaker_state == CircuitBreakerState.OPEN:
                if func._last_failure_time and \
                   (now - func._last_failure_time).total_seconds() < recovery_timeout:
                    raise InfrastructureError(
                        message=f"Circuit breaker open for {func.__name__}",
                        context={
                            'function': func.__name__,
                            'failure_count': func._failure_count,
                            'retry_after': recovery_timeout
                        },
                        retry_after=recovery_timeout
                    )
                else:
                    # Try half-open state
                    func._circuit_breaker_state = CircuitBreakerState.HALF_OPEN
            
            try:
                result = func(*args, **kwargs)
                
                # Success - reset circuit breaker
                if func._circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                    func._circuit_breaker_state = CircuitBreakerState.CLOSED
                    func._failure_count = 0
                    func._last_failure_time = None
                    logger.info(f"Circuit breaker closed for {func.__name__}")
                
                return result
                
            except expected_exception as exc:
                func._failure_count += 1
                func._last_failure_time = now
                
                # Open circuit if threshold reached
                if func._failure_count >= failure_threshold:
                    func._circuit_breaker_state = CircuitBreakerState.OPEN
                    logger.warning(
                        f"Circuit breaker opened for {func.__name__} "
                        f"after {func._failure_count} failures"
                    )
                
                raise exc
                
        return wrapper
    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        backoff_multiplier: Multiplier for exponential backoff
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Exception types that should trigger retries
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    
                    if attempt >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {exc}"
                        )
                        raise exc
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                    
                    # Add jitter if enabled
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt + 1}, "
                        f"retrying in {delay:.2f}s: {exc}"
                    )
                    
                    time.sleep(delay)
            
            raise last_exception
            
        return wrapper
    return decorator


# Async versions of decorators
def async_error_handler(
    log_errors: bool = True,
    collect_metrics: bool = True,
    reraise: bool = False,
    fallback_value: Any = None,
    fallback_function: Optional[Callable] = None
):
    """Async version of error_handler decorator"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                # Convert to BaseError if needed
                if not isinstance(exc, BaseError):
                    exc = BaseError(
                        message=str(exc),
                        cause=exc,
                        context={'function': func.__name__}
                    )
                
                # Log error
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {exc.message}", extra=exc.to_dict())
                
                # Collect metrics
                if collect_metrics:
                    metrics_collector = ErrorMetricsCollector()
                    await metrics_collector.record_function_error_async(func.__name__, exc)
                
                # Handle fallback
                if fallback_function:
                    if asyncio.iscoroutinefunction(fallback_function):
                        return await fallback_function(exc, *args, **kwargs)
                    else:
                        return fallback_function(exc, *args, **kwargs)
                elif fallback_value is not None:
                    return fallback_value
                
                # Reraise if configured
                if reraise:
                    raise exc
                
                return None
                
        return wrapper
    return decorator


def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,)
):
    """Async version of retry_with_backoff decorator"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exception = exc
                    
                    if attempt >= max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {exc}"
                        )
                        raise exc
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_multiplier ** attempt), max_delay)
                    
                    # Add jitter if enabled
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt + 1}, "
                        f"retrying in {delay:.2f}s: {exc}"
                    )
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
            
        return wrapper
    return decorator
