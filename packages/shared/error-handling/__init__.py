"""
Comprehensive Error Handling Package

This package provides a complete error handling system with:
- Custom exception hierarchy
- Error handling middleware
- Recovery strategies
- Metrics and monitoring

Usage:
    from packages.shared.error_handling import (
        BaseError, DomainError, ValidationError,
        error_handler, ErrorHandlingMiddleware
    )
"""

from .exceptions import (
    BaseError,
    DomainError,
    ValidationError,
    NotFoundError,
    ConflictError,
    InfrastructureError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    PaymentError,
    ErrorSeverity,
    ErrorCategory
)

from .middleware import (
    ErrorHandlingMiddleware,
    error_handler,
    circuit_breaker,
    retry_with_backoff
)

from .recovery import (
    ErrorRecoveryManager,
    RecoveryStrategy,
    CircuitBreakerState
)

from .formatters import (
    ErrorFormatter,
    UserFriendlyMessages
)

from .metrics import (
    ErrorMetricsCollector,
    ErrorAnalytics
)

__all__ = [
    # Exception classes
    'BaseError',
    'DomainError', 
    'ValidationError',
    'NotFoundError',
    'ConflictError',
    'InfrastructureError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'PaymentError',
    'ErrorSeverity',
    'ErrorCategory',
    
    # Middleware and decorators
    'ErrorHandlingMiddleware',
    'error_handler',
    'circuit_breaker',
    'retry_with_backoff',
    
    # Recovery management
    'ErrorRecoveryManager',
    'RecoveryStrategy',
    'CircuitBreakerState',
    
    # Formatters and messages
    'ErrorFormatter',
    'UserFriendlyMessages',
    
    # Metrics and analytics
    'ErrorMetricsCollector',
    'ErrorAnalytics'
]
