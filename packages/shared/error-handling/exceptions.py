"""
Custom Exception Hierarchy

Provides a comprehensive set of exception classes for different error scenarios
with context information and severity levels.
"""

import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification and routing"""
    BUSINESS_LOGIC = "business_logic"
    VALIDATION = "validation"
    INFRASTRUCTURE = "infrastructure"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMITING = "rate_limiting"
    PAYMENT = "payment"
    EXTERNAL_SERVICE = "external_service"
    DATA_INTEGRITY = "data_integrity"
    CONFIGURATION = "configuration"


class BaseError(Exception):
    """
    Base exception class for all application errors.
    
    Provides common functionality like error context, severity,
    user messages, and telemetry data.
    """
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC,
        user_message: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = True,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        
        self.message = message
        self.severity = severity
        self.category = category
        self.user_message = user_message or self._get_default_user_message()
        self.error_code = error_code or self._generate_error_code()
        self.context = context or {}
        self.cause = cause
        self.recoverable = recoverable
        self.retry_after = retry_after
        
        # Metadata
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()
        self.error_id = self._generate_error_id()
        
    def _get_default_user_message(self) -> str:
        """Get default user-friendly message based on error category"""
        default_messages = {
            ErrorCategory.BUSINESS_LOGIC: "Sorry, I couldn't complete that request. Please try again.",
            ErrorCategory.VALIDATION: "There seems to be an issue with your input. Please check and try again.",
            ErrorCategory.INFRASTRUCTURE: "I'm experiencing technical difficulties. Please try again in a moment.",
            ErrorCategory.AUTHENTICATION: "Please log in to continue.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.RATE_LIMITING: "You're making requests too quickly. Please wait a moment and try again.",
            ErrorCategory.PAYMENT: "There was an issue processing your payment. Please check your payment method.",
            ErrorCategory.EXTERNAL_SERVICE: "I'm having trouble connecting to external services. Please try again.",
            ErrorCategory.DATA_INTEGRITY: "There was a data consistency issue. Please contact support.",
            ErrorCategory.CONFIGURATION: "There's a configuration issue. Please contact support."
        }
        return default_messages.get(self.category, "An unexpected error occurred. Please try again.")
    
    def _generate_error_code(self) -> str:
        """Generate unique error code"""
        return f"{self.category.value.upper()}_{self.__class__.__name__.upper()}"
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking"""
        timestamp = int(self.timestamp.timestamp() * 1000)
        return f"ERR_{timestamp}_{hash(self.message) % 10000:04d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging and monitoring"""
        return {
            'error_id': self.error_id,
            'error_code': self.error_code,
            'message': self.message,
            'user_message': self.user_message,
            'severity': self.severity.value,
            'category': self.category.value,
            'timestamp': self.timestamp.isoformat(),
            'recoverable': self.recoverable,
            'retry_after': self.retry_after,
            'context': self.context,
            'cause': str(self.cause) if self.cause else None,
            'traceback': self.traceback
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class DomainError(BaseError):
    """Business rule violations and domain logic errors"""
    
    def __init__(self, message: str, business_rule: Optional[str] = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.BUSINESS_LOGIC)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)
        self.business_rule = business_rule
        if business_rule:
            self.context['business_rule'] = business_rule


class ValidationError(BaseError):
    """Input validation errors"""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        invalid_value: Any = None,
        validation_rules: Optional[List[str]] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.VALIDATION)
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        kwargs.setdefault('user_message', f"Invalid input: {message}")
        super().__init__(message, **kwargs)
        
        self.field = field
        self.invalid_value = invalid_value
        self.validation_rules = validation_rules or []
        
        if field:
            self.context['field'] = field
        if invalid_value is not None:
            self.context['invalid_value'] = str(invalid_value)
        if validation_rules:
            self.context['validation_rules'] = validation_rules


class NotFoundError(BaseError):
    """Resource not found errors"""
    
    def __init__(
        self, 
        message: str, 
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.BUSINESS_LOGIC)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('user_message', "The requested item could not be found.")
        super().__init__(message, **kwargs)
        
        self.resource_type = resource_type
        self.resource_id = resource_id
        
        if resource_type:
            self.context['resource_type'] = resource_type
        if resource_id:
            self.context['resource_id'] = resource_id


class ConflictError(BaseError):
    """State conflicts and concurrency issues"""
    
    def __init__(
        self, 
        message: str, 
        conflicting_resource: Optional[str] = None,
        expected_state: Optional[str] = None,
        actual_state: Optional[str] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.DATA_INTEGRITY)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('user_message', "There was a conflict with your request. Please try again.")
        super().__init__(message, **kwargs)
        
        self.conflicting_resource = conflicting_resource
        self.expected_state = expected_state
        self.actual_state = actual_state
        
        if conflicting_resource:
            self.context['conflicting_resource'] = conflicting_resource
        if expected_state:
            self.context['expected_state'] = expected_state
        if actual_state:
            self.context['actual_state'] = actual_state


class InfrastructureError(BaseError):
    """External service and infrastructure failures"""
    
    def __init__(
        self, 
        message: str, 
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.INFRASTRUCTURE)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('user_message', "I'm experiencing technical difficulties. Please try again.")
        kwargs.setdefault('recoverable', True)
        kwargs.setdefault('retry_after', 30)
        super().__init__(message, **kwargs)
        
        self.service_name = service_name
        self.operation = operation
        self.status_code = status_code
        
        if service_name:
            self.context['service_name'] = service_name
        if operation:
            self.context['operation'] = operation
        if status_code:
            self.context['status_code'] = status_code


class AuthenticationError(BaseError):
    """Authentication failures"""
    
    def __init__(
        self, 
        message: str = "Authentication required",
        auth_method: Optional[str] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.AUTHENTICATION)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('user_message', "Please log in to continue.")
        kwargs.setdefault('recoverable', False)
        super().__init__(message, **kwargs)
        
        self.auth_method = auth_method
        if auth_method:
            self.context['auth_method'] = auth_method


class AuthorizationError(BaseError):
    """Authorization failures"""
    
    def __init__(
        self, 
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        user_permissions: Optional[List[str]] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.AUTHORIZATION)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('user_message', "You don't have permission to perform this action.")
        kwargs.setdefault('recoverable', False)
        super().__init__(message, **kwargs)
        
        self.required_permission = required_permission
        self.user_permissions = user_permissions or []
        
        if required_permission:
            self.context['required_permission'] = required_permission
        if user_permissions:
            self.context['user_permissions'] = user_permissions


class RateLimitError(BaseError):
    """Rate limiting errors"""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[int] = None,
        reset_time: Optional[datetime] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.RATE_LIMITING)
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('user_message', "You're making requests too quickly. Please wait and try again.")
        kwargs.setdefault('recoverable', True)
        
        # Set retry_after based on reset_time
        if reset_time:
            retry_after = int((reset_time - datetime.utcnow()).total_seconds())
            kwargs.setdefault('retry_after', max(retry_after, 60))
        else:
            kwargs.setdefault('retry_after', 60)
            
        super().__init__(message, **kwargs)
        
        self.limit = limit
        self.window = window
        self.reset_time = reset_time
        
        if limit:
            self.context['limit'] = limit
        if window:
            self.context['window'] = window
        if reset_time:
            self.context['reset_time'] = reset_time.isoformat()


class PaymentError(BaseError):
    """Payment processing errors"""
    
    def __init__(
        self, 
        message: str,
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        provider_error_code: Optional[str] = None,
        **kwargs
    ):
        kwargs.setdefault('category', ErrorCategory.PAYMENT)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('user_message', "There was an issue processing your payment. Please check your payment method.")
        kwargs.setdefault('recoverable', True)
        super().__init__(message, **kwargs)
        
        self.payment_method = payment_method
        self.transaction_id = transaction_id
        self.amount = amount
        self.currency = currency
        self.provider_error_code = provider_error_code
        
        if payment_method:
            self.context['payment_method'] = payment_method
        if transaction_id:
            self.context['transaction_id'] = transaction_id
        if amount:
            self.context['amount'] = amount
        if currency:
            self.context['currency'] = currency
        if provider_error_code:
            self.context['provider_error_code'] = provider_error_code


# Utility functions for error creation
def create_validation_error(field: str, value: Any, rule: str) -> ValidationError:
    """Create a validation error with standard formatting"""
    return ValidationError(
        message=f"Validation failed for field '{field}': {rule}",
        field=field,
        invalid_value=value,
        validation_rules=[rule]
    )


def create_not_found_error(resource_type: str, resource_id: str) -> NotFoundError:
    """Create a not found error with standard formatting"""
    return NotFoundError(
        message=f"{resource_type} with ID '{resource_id}' not found",
        resource_type=resource_type,
        resource_id=resource_id
    )


def create_infrastructure_error(service: str, operation: str, cause: Exception) -> InfrastructureError:
    """Create an infrastructure error with standard formatting"""
    return InfrastructureError(
        message=f"Failed to {operation} with {service}: {str(cause)}",
        service_name=service,
        operation=operation,
        cause=cause
    )
