"""Result types for error handling.

This module provides a Result type for handling success and error cases
without exceptions.
"""

from __future__ import annotations

import sys
from typing import Any, Callable, Generic, TypeVar, Union, Optional, cast

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from .common import T, U, ErrorCode, ErrorMessage, ErrorDetails

# Result type aliases
TSuccess = TypeVar('TSuccess')
TError = TypeVar('TError')

class Success(Generic[TSuccess]):
    """Represents a successful result."""
    
    def __init__(self, value: TSuccess) -> None:
        self._value = value
    
    @property
    def value(self) -> TSuccess:
        """Get the success value."""
        return self._value
    
    def is_success(self) -> bool:
        """Check if this is a success result."""
        return True
    
    def is_failure(self) -> bool:
        """Check if this is a failure result."""
        return False
    
    def unwrap(self) -> TSuccess:
        """Unwrap the success value."""
        return self._value
    
    def unwrap_or(self, default: U) -> TSuccess:
        """Unwrap the success value or return default."""
        return self._value
    
    def unwrap_or_else(self, func: Callable[[Any], U]) -> TSuccess:
        """Unwrap the success value or call function."""
        return self._value
    
    def map(self, func: Callable[[TSuccess], U]) -> Success[U]:
        """Transform the success value."""
        return Success(func(self._value))
    
    def and_then(self, func: Callable[[TSuccess], Result[U, TError]]) -> Result[U, TError]:
        """Chain another operation that returns a Result."""
        return func(self._value)
    
    def __repr__(self) -> str:
        return f"Success({self._value!r})"
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Success) and self._value == other._value
    
    def __hash__(self) -> int:
        return hash(('success', self._value))

class Failure(Generic[TError]):
    """Represents a failed result."""
    
    def __init__(self, error: TError) -> None:
        self._error = error
    
    @property
    def error(self) -> TError:
        """Get the error value."""
        return self._error
    
    def is_success(self) -> bool:
        """Check if this is a success result."""
        return False
    
    def is_failure(self) -> bool:
        """Check if this is a failure result."""
        return True
    
    def unwrap(self) -> TSuccess:
        """Unwrap the success value (raises RuntimeError)."""
        raise RuntimeError(f"Called unwrap on Failure: {self._error}")
    
    def unwrap_or(self, default: U) -> U:
        """Unwrap the success value or return default."""
        return default
    
    def unwrap_or_else(self, func: Callable[[TError], U]) -> U:
        """Unwrap the success value or call function."""
        return func(self._error)
    
    def map(self, func: Callable[[Any], U]) -> Failure[TError]:
        """Transform the success value (no-op for Failure)."""
        return cast(Failure[TError], self)
    
    def and_then(self, func: Callable[[Any], Result[U, TError]]) -> Failure[TError]:
        """Chain another operation (no-op for Failure)."""
        return cast(Failure[TError], self)
    
    def __repr__(self) -> str:
        return f"Failure({self._error!r})"
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Failure) and self._error == other._error
    
    def __hash__(self) -> int:
        return hash(('failure', self._error))

# Result type union
Result: TypeAlias = Union[Success[TSuccess], Failure[TError]]

# Common error types
class AppError:
    """Base application error."""
    
    def __init__(
        self,
        code: ErrorCode,
        message: ErrorMessage,
        details: Optional[ErrorDetails] = None,
        cause: Optional[Exception] = None
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def __repr__(self) -> str:
        return f"AppError(code={self.code!r}, message={self.message!r})"
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AppError):
            return False
        return (
            self.code == other.code and
            self.message == other.message and
            self.details == other.details
        )
    
    def __hash__(self) -> int:
        return hash((self.code, self.message, tuple(sorted(self.details.items()))))

class ValidationError(AppError):
    """Validation error."""
    
    def __init__(
        self,
        message: ErrorMessage,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[ErrorDetails] = None
    ) -> None:
        error_details = details or {}
        if field is not None:
            error_details['field'] = field
        if value is not None:
            error_details['value'] = value
        
        super().__init__(
            code='validation_error',
            message=message,
            details=error_details
        )
        self.field = field
        self.value = value

class NotFoundError(AppError):
    """Resource not found error."""
    
    def __init__(
        self,
        resource: str,
        identifier: str,
        details: Optional[ErrorDetails] = None
    ) -> None:
        error_details = details or {}
        error_details.update({
            'resource': resource,
            'identifier': identifier
        })
        
        super().__init__(
            code='not_found',
            message=f"{resource} with identifier '{identifier}' not found",
            details=error_details
        )
        self.resource = resource
        self.identifier = identifier

class ConflictError(AppError):
    """Resource conflict error."""
    
    def __init__(
        self,
        resource: str,
        reason: str,
        details: Optional[ErrorDetails] = None
    ) -> None:
        error_details = details or {}
        error_details.update({
            'resource': resource,
            'reason': reason
        })
        
        super().__init__(
            code='conflict',
            message=f"Conflict with {resource}: {reason}",
            details=error_details
        )
        self.resource = resource
        self.reason = reason

class AuthenticationError(AppError):
    """Authentication error."""
    
    def __init__(
        self,
        message: ErrorMessage = "Authentication failed",
        details: Optional[ErrorDetails] = None
    ) -> None:
        super().__init__(
            code='authentication_error',
            message=message,
            details=details
        )

class AuthorizationError(AppError):
    """Authorization error."""
    
    def __init__(
        self,
        message: ErrorMessage = "Access denied",
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[ErrorDetails] = None
    ) -> None:
        error_details = details or {}
        if resource is not None:
            error_details['resource'] = resource
        if action is not None:
            error_details['action'] = action
        
        super().__init__(
            code='authorization_error',
            message=message,
            details=error_details
        )
        self.resource = resource
        self.action = action

class RateLimitError(AppError):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        retry_after_seconds: Optional[int] = None,
        details: Optional[ErrorDetails] = None
    ) -> None:
        error_details = details or {}
        error_details.update({
            'limit': limit,
            'window_seconds': window_seconds
        })
        if retry_after_seconds is not None:
            error_details['retry_after_seconds'] = retry_after_seconds
        
        super().__init__(
            code='rate_limit_exceeded',
            message=f"Rate limit of {limit} requests per {window_seconds} seconds exceeded",
            details=error_details
        )
        self.limit = limit
        self.window_seconds = window_seconds
        self.retry_after_seconds = retry_after_seconds

class ExternalServiceError(AppError):
    """External service error."""
    
    def __init__(
        self,
        service: str,
        status_code: Optional[int] = None,
        message: ErrorMessage = "External service error",
        details: Optional[ErrorDetails] = None
    ) -> None:
        error_details = details or {}
        error_details['service'] = service
        if status_code is not None:
            error_details['status_code'] = status_code
        
        super().__init__(
            code='external_service_error',
            message=f"{service}: {message}",
            details=error_details
        )
        self.service = service
        self.status_code = status_code

# Result factory functions
def success(value: TSuccess) -> Success[TSuccess]:
    """Create a Success result."""
    return Success(value)

def failure(error: TError) -> Failure[TError]:
    """Create a Failure result."""
    return Failure(error)

# Result utility functions
def from_optional(value: Optional[T], error: TError) -> Result[T, TError]:
    """Convert Optional to Result."""
    if value is not None:
        return success(value)
    return failure(error)

def from_exception(func: Callable[[], T], error_mapper: Callable[[Exception], TError]) -> Result[T, TError]:
    """Execute function and convert exceptions to Result."""
    try:
        return success(func())
    except Exception as e:
        return failure(error_mapper(e))

def collect_results(results: list[Result[T, TError]]) -> Result[list[T], TError]:
    """Collect a list of Results into a single Result of a list."""
    values: list[T] = []
    
    for result in results:
        if result.is_failure():
            return result  # type: ignore
        values.append(result.unwrap())
    
    return success(values)

# Type aliases for common Result patterns
StrResult: TypeAlias = Result[str, AppError]
IntResult: TypeAlias = Result[int, AppError]
BoolResult: TypeAlias = Result[bool, AppError]
DictResult: TypeAlias = Result[dict[str, Any], AppError]
ListResult: TypeAlias = Result[list[Any], AppError]
VoidResult: TypeAlias = Result[None, AppError]

# Export all public types and functions
__all__ = [
    # Core types
    'Success', 'Failure', 'Result',
    
    # Error types
    'AppError', 'ValidationError', 'NotFoundError', 'ConflictError',
    'AuthenticationError', 'AuthorizationError', 'RateLimitError', 'ExternalServiceError',
    
    # Factory functions
    'success', 'failure',
    
    # Utility functions
    'from_optional', 'from_exception', 'collect_results',
    
    # Type aliases
    'StrResult', 'IntResult', 'BoolResult', 'DictResult', 'ListResult', 'VoidResult',
]
