"""
Structured logging framework for AI Nutritionist application.

Provides:
- JSON structured logging
- Correlation ID tracking
- Performance metrics
- Business event logging
- Privacy-compliant logging (PII masking)
- CloudWatch integration
"""

import asyncio
import json
import logging
import time
import uuid
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import traceback
import boto3
from botocore.exceptions import ClientError


class LogLevel(Enum):
    """Log levels for structured logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class EventType(Enum):
    """Business event types for categorization."""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    BUSINESS_EVENT = "business_event"
    SECURITY_EVENT = "security_event"
    PERFORMANCE_EVENT = "performance_event"
    ERROR_EVENT = "error_event"
    AUDIT_EVENT = "audit_event"


@dataclass
class LogContext:
    """Context information for correlation and tracing."""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    service_name: str = "ai-nutritionist"
    operation: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""
    duration_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    operation_count: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class BusinessEvent:
    """Business event data structure."""
    event_type: EventType
    entity_type: str
    entity_id: Optional[str] = None
    action: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = asdict(self)
        result["event_type"] = self.event_type.value
        return result


class PIIMasker:
    """Handles PII masking for GDPR compliance."""
    
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}-?\d{3}-?\d{4}\b',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
    }
    
    @classmethod
    def mask_data(cls, data: Any) -> Any:
        """Mask PII data in any structure."""
        if isinstance(data, dict):
            return {k: cls.mask_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.mask_data(item) for item in data]
        elif isinstance(data, str):
            return cls._mask_string(data)
        else:
            return data
    
    @classmethod
    def _mask_string(cls, text: str) -> str:
        """Mask PII patterns in string."""
        import re
        masked = text
        for pattern_name, pattern in cls.PII_PATTERNS.items():
            masked = re.sub(pattern, f"[MASKED_{pattern_name.upper()}]", masked)
        return masked


class LogFormatter:
    """Formats logs as structured JSON."""
    
    @staticmethod
    def format_log(
        level: LogLevel,
        message: str,
        context: LogContext,
        event: Optional[BusinessEvent] = None,
        metrics: Optional[PerformanceMetrics] = None,
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a log entry as JSON."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "message": message,
            "context": context.to_dict(),
        }
        
        if event:
            log_entry["business_event"] = event.to_dict()
        
        if metrics:
            log_entry["performance"] = metrics.to_dict()
        
        if error:
            log_entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc() if hasattr(error, "__traceback__") else None
            }
        
        if extra:
            log_entry["extra"] = PIIMasker.mask_data(extra)
        
        # Mask PII in the entire log entry
        log_entry = PIIMasker.mask_data(log_entry)
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class LogHandler(ABC):
    """Abstract base class for log handlers."""
    
    @abstractmethod
    def handle(self, formatted_log: str) -> None:
        """Handle a formatted log entry."""
        pass


class ConsoleLogHandler(LogHandler):
    """Handles logging to console."""
    
    def handle(self, formatted_log: str) -> None:
        """Print log to console."""
        print(formatted_log)


class CloudWatchLogHandler(LogHandler):
    """Handles logging to AWS CloudWatch."""
    
    def __init__(self, log_group: str, log_stream: str, region: str = "us-east-1"):
        self.log_group = log_group
        self.log_stream = log_stream
        self.region = region
        self._client = None
        self._sequence_token = None
        self._lock = threading.Lock()
    
    @property
    def client(self):
        """Lazy initialization of CloudWatch client."""
        if self._client is None:
            self._client = boto3.client('logs', region_name=self.region)
            self._ensure_log_group_exists()
            self._ensure_log_stream_exists()
        return self._client
    
    def _ensure_log_group_exists(self):
        """Ensure the log group exists."""
        try:
            self.client.create_log_group(logGroupName=self.log_group)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def _ensure_log_stream_exists(self):
        """Ensure the log stream exists."""
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def handle(self, formatted_log: str) -> None:
        """Send log to CloudWatch."""
        with self._lock:
            try:
                log_event = {
                    'timestamp': int(time.time() * 1000),
                    'message': formatted_log
                }
                
                put_args = {
                    'logGroupName': self.log_group,
                    'logStreamName': self.log_stream,
                    'logEvents': [log_event]
                }
                
                if self._sequence_token:
                    put_args['sequenceToken'] = self._sequence_token
                
                response = self.client.put_log_events(**put_args)
                self._sequence_token = response.get('nextSequenceToken')
                
            except Exception as e:
                # Fallback to console if CloudWatch fails
                print(f"CloudWatch logging failed: {e}")
                print(formatted_log)


class StructuredLogger:
    """Main structured logger class."""
    
    _instance = None
    _lock = threading.Lock()
    _context = threading.local()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, service_name: str = "ai-nutritionist"):
        if hasattr(self, '_initialized'):
            return
        
        self.service_name = service_name
        self.handlers: List[LogHandler] = []
        self.min_level = LogLevel.INFO
        self._initialized = True
    
    def add_handler(self, handler: LogHandler) -> None:
        """Add a log handler."""
        self.handlers.append(handler)
    
    def set_min_level(self, level: LogLevel) -> None:
        """Set minimum log level."""
        self.min_level = level
    
    @property
    def context(self) -> LogContext:
        """Get current thread's log context."""
        if not hasattr(self._context, 'current'):
            self._context.current = LogContext(service_name=self.service_name)
        return self._context.current
    
    @context.setter
    def context(self, value: LogContext) -> None:
        """Set current thread's log context."""
        self._context.current = value
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if we should log at this level."""
        level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARN: 2,
            LogLevel.ERROR: 3,
            LogLevel.FATAL: 4
        }
        return level_order[level] >= level_order[self.min_level]
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        event: Optional[BusinessEvent] = None,
        metrics: Optional[PerformanceMetrics] = None,
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Internal logging method."""
        if not self._should_log(level):
            return
        
        formatted_log = LogFormatter.format_log(
            level=level,
            message=message,
            context=self.context,
            event=event,
            metrics=metrics,
            error=error,
            extra=extra
        )
        
        for handler in self.handlers:
            try:
                handler.handle(formatted_log)
            except Exception as e:
                # Don't let handler errors break the application
                print(f"Log handler error: {e}")
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warn(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(LogLevel.WARN, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def fatal(self, message: str, **kwargs) -> None:
        """Log fatal message."""
        self._log(LogLevel.FATAL, message, **kwargs)
    
    def business_event(
        self,
        event_type: EventType,
        entity_type: str,
        action: str,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: LogLevel = LogLevel.INFO
    ) -> None:
        """Log a business event."""
        event = BusinessEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            metadata=metadata or {}
        )
        
        message = f"{event_type.value}: {entity_type}.{action}"
        if entity_id:
            message += f" (id: {entity_id})"
        
        self._log(level, message, event=event)
    
    @contextmanager
    def operation_context(
        self,
        operation: str,
        user_id: Optional[str] = None,
        additional_context: Optional[Dict[str, str]] = None
    ):
        """Context manager for operation logging with performance tracking."""
        start_time = time.time()
        original_context = self.context
        
        # Create new context for this operation
        new_context = LogContext(
            correlation_id=original_context.correlation_id,
            user_id=user_id or original_context.user_id,
            session_id=original_context.session_id,
            request_id=original_context.request_id,
            trace_id=original_context.trace_id,
            service_name=self.service_name,
            operation=operation
        )
        
        if additional_context:
            for key, value in additional_context.items():
                setattr(new_context, key, value)
        
        self.context = new_context
        
        self.info(f"Operation started: {operation}")
        
        try:
            yield self
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            metrics = PerformanceMetrics(duration_ms=duration_ms)
            
            self.error(
                f"Operation failed: {operation}",
                error=e,
                metrics=metrics
            )
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            metrics = PerformanceMetrics(duration_ms=duration_ms)
            
            self.info(
                f"Operation completed: {operation}",
                metrics=metrics
            )
            
            # Restore original context
            self.context = original_context


def performance_monitor(operation_name: Optional[str] = None):
    """Decorator for monitoring function performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with logger.operation_context(op_name):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = StructuredLogger()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with logger.operation_context(op_name):
                return await func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


def audit_log(event_type: EventType, entity_type: str, action: str):
    """Decorator for audit logging."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger()
            
            # Try to extract entity_id from function arguments
            entity_id = None
            if args and hasattr(args[0], 'id'):
                entity_id = getattr(args[0], 'id')
            elif 'id' in kwargs:
                entity_id = kwargs['id']
            elif 'entity_id' in kwargs:
                entity_id = kwargs['entity_id']
            
            try:
                result = func(*args, **kwargs)
                logger.business_event(
                    event_type=event_type,
                    entity_type=entity_type,
                    action=action,
                    entity_id=entity_id,
                    metadata={"status": "success"}
                )
                return result
            except Exception as e:
                logger.business_event(
                    event_type=event_type,
                    entity_type=entity_type,
                    action=action,
                    entity_id=entity_id,
                    metadata={"status": "failed", "error": str(e)},
                    level=LogLevel.ERROR
                )
                raise
        
        return wrapper
    return decorator


# Global logger instance
logger = StructuredLogger()

# Convenience functions
def get_logger(service_name: str = "ai-nutritionist") -> StructuredLogger:
    """Get logger instance for a service."""
    if service_name != "ai-nutritionist":
        # Create a new logger instance for different services
        return StructuredLogger(service_name)
    return logger


def setup_logging(
    service_name: str = "ai-nutritionist",
    log_level: LogLevel = LogLevel.INFO,
    use_cloudwatch: bool = False,
    cloudwatch_log_group: Optional[str] = None,
    cloudwatch_log_stream: Optional[str] = None,
    cloudwatch_region: str = "us-east-1"
) -> StructuredLogger:
    """Setup logging for the application."""
    logger_instance = get_logger(service_name)
    logger_instance.set_min_level(log_level)
    
    # Add console handler
    logger_instance.add_handler(ConsoleLogHandler())
    
    # Add CloudWatch handler if requested
    if use_cloudwatch and cloudwatch_log_group:
        if not cloudwatch_log_stream:
            cloudwatch_log_stream = f"{service_name}-{datetime.now().strftime('%Y-%m-%d')}"
        
        cloudwatch_handler = CloudWatchLogHandler(
            log_group=cloudwatch_log_group,
            log_stream=cloudwatch_log_stream,
            region=cloudwatch_region
        )
        logger_instance.add_handler(cloudwatch_handler)
    
    return logger_instance
