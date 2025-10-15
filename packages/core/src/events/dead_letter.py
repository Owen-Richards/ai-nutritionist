"""
Dead letter queue for handling failed event processing.

Provides a mechanism to capture and retry events that fail during processing.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from .base import Event

logger = logging.getLogger(__name__)


class FailureReason(Enum):
    """Reasons why event processing might fail."""
    HANDLER_ERROR = "handler_error"
    TIMEOUT = "timeout"
    SERIALIZATION_ERROR = "serialization_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class FailedEvent:
    """
    Represents a failed event with failure context.
    """
    event: Event
    failure_reason: FailureReason
    error_message: str
    handler_name: Optional[str] = None
    failed_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Calculate next retry time."""
        if self.next_retry_at is None and self.retry_count < self.max_retries:
            # Exponential backoff: 2^retry_count minutes
            delay_minutes = 2 ** self.retry_count
            self.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
    
    def is_retry_due(self) -> bool:
        """Check if the event is due for retry."""
        if self.retry_count >= self.max_retries:
            return False
        
        if self.next_retry_at is None:
            return False
        
        return datetime.utcnow() >= self.next_retry_at
    
    def increment_retry(self) -> None:
        """Increment retry count and update retry time."""
        self.retry_count += 1
        self.last_retry_at = datetime.utcnow()
        
        if self.retry_count < self.max_retries:
            delay_minutes = 2 ** self.retry_count
            self.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        else:
            self.next_retry_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event": self.event.to_dict(),
            "failure_reason": self.failure_reason.value,
            "error_message": self.error_message,
            "handler_name": self.handler_name,
            "failed_at": self.failed_at.isoformat(),
            "retry_count": self.retry_count,
            "last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
            "max_retries": self.max_retries,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], event_class: type) -> 'FailedEvent':
        """Create from dictionary."""
        event = event_class.from_dict(data["event"])
        
        return cls(
            event=event,
            failure_reason=FailureReason(data["failure_reason"]),
            error_message=data["error_message"],
            handler_name=data.get("handler_name"),
            failed_at=datetime.fromisoformat(data["failed_at"]),
            retry_count=data["retry_count"],
            last_retry_at=datetime.fromisoformat(data["last_retry_at"]) if data.get("last_retry_at") else None,
            max_retries=data["max_retries"],
            next_retry_at=datetime.fromisoformat(data["next_retry_at"]) if data.get("next_retry_at") else None,
        )


class DeadLetterQueue:
    """
    Dead letter queue for managing failed events.
    
    Captures events that fail processing and provides
    retry mechanisms with exponential backoff.
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        retention_days: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize the dead letter queue.
        
        Args:
            max_queue_size: Maximum number of failed events to keep
            retention_days: How long to keep failed events
            max_retries: Maximum retry attempts per event
        """
        self._failed_events: List[FailedEvent] = []
        self._max_queue_size = max_queue_size
        self._retention_days = retention_days
        self._max_retries = max_retries
        self._lock = asyncio.Lock() if asyncio.get_running_loop() else None
    
    def add(
        self,
        event: Event,
        failures: List[Tuple[Union[str, object], Exception]],
        max_retries: Optional[int] = None
    ) -> None:
        """
        Add a failed event to the dead letter queue.
        
        Args:
            event: The event that failed
            failures: List of (handler, exception) tuples
            max_retries: Override default max retries
        """
        max_retries = max_retries or self._max_retries
        
        for handler, exception in failures:
            handler_name = handler if isinstance(handler, str) else handler.__class__.__name__
            failure_reason = self._classify_error(exception)
            
            failed_event = FailedEvent(
                event=event,
                failure_reason=failure_reason,
                error_message=str(exception),
                handler_name=handler_name,
                max_retries=max_retries
            )
            
            self._failed_events.append(failed_event)
            logger.warning(
                f"Added event to dead letter queue: {event.event_name} "
                f"(handler: {handler_name}, reason: {failure_reason.value})"
            )
        
        # Cleanup if needed
        self._cleanup_old_events()
        self._enforce_size_limit()
    
    async def add_async(
        self,
        event: Event,
        failures: List[Tuple[Union[str, object], Exception]],
        max_retries: Optional[int] = None
    ) -> None:
        """
        Add a failed event to the dead letter queue asynchronously.
        
        Args:
            event: The event that failed
            failures: List of (handler, exception) tuples
            max_retries: Override default max retries
        """
        if self._lock:
            async with self._lock:
                self.add(event, failures, max_retries)
        else:
            self.add(event, failures, max_retries)
    
    def get_retry_ready_events(self) -> List[FailedEvent]:
        """
        Get events that are ready for retry.
        
        Returns:
            List of failed events ready for retry
        """
        retry_ready = []
        
        for failed_event in self._failed_events:
            if failed_event.is_retry_due():
                retry_ready.append(failed_event)
        
        logger.debug(f"Found {len(retry_ready)} events ready for retry")
        return retry_ready
    
    def mark_retry_attempted(self, failed_event: FailedEvent) -> None:
        """
        Mark that a retry attempt was made.
        
        Args:
            failed_event: The failed event that was retried
        """
        failed_event.increment_retry()
        logger.debug(f"Incremented retry count for event {failed_event.event.event_id} to {failed_event.retry_count}")
    
    def mark_retry_successful(self, failed_event: FailedEvent) -> None:
        """
        Mark that a retry was successful and remove from queue.
        
        Args:
            failed_event: The failed event that succeeded on retry
        """
        if failed_event in self._failed_events:
            self._failed_events.remove(failed_event)
            logger.info(f"Removed successfully retried event {failed_event.event.event_id} from dead letter queue")
    
    def get_failed_events(
        self,
        failure_reason: Optional[FailureReason] = None,
        handler_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FailedEvent]:
        """
        Get failed events with optional filtering.
        
        Args:
            failure_reason: Filter by failure reason
            handler_name: Filter by handler name
            limit: Maximum number of events to return
            
        Returns:
            List of failed events matching criteria
        """
        filtered_events = []
        
        for failed_event in self._failed_events:
            # Apply filters
            if failure_reason and failed_event.failure_reason != failure_reason:
                continue
            
            if handler_name and failed_event.handler_name != handler_name:
                continue
            
            filtered_events.append(failed_event)
        
        # Sort by failed_at descending (newest first)
        filtered_events.sort(key=lambda fe: fe.failed_at, reverse=True)
        
        # Apply limit
        if limit is not None:
            filtered_events = filtered_events[:limit]
        
        return filtered_events
    
    def remove_event(self, event_id: str) -> bool:
        """
        Remove a specific event from the dead letter queue.
        
        Args:
            event_id: ID of the event to remove
            
        Returns:
            True if event was found and removed
        """
        for i, failed_event in enumerate(self._failed_events):
            if failed_event.event.event_id == event_id:
                del self._failed_events[i]
                logger.info(f"Removed event {event_id} from dead letter queue")
                return True
        
        return False
    
    def clear(self) -> int:
        """
        Clear all events from the dead letter queue.
        
        Returns:
            Number of events that were cleared
        """
        count = len(self._failed_events)
        self._failed_events.clear()
        logger.info(f"Cleared {count} events from dead letter queue")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the dead letter queue.
        
        Returns:
            Dictionary with queue statistics
        """
        if not self._failed_events:
            return {
                "total_events": 0,
                "by_reason": {},
                "by_handler": {},
                "retry_ready": 0,
                "exhausted_retries": 0,
            }
        
        by_reason = {}
        by_handler = {}
        retry_ready = 0
        exhausted_retries = 0
        
        for failed_event in self._failed_events:
            # Count by reason
            reason = failed_event.failure_reason.value
            by_reason[reason] = by_reason.get(reason, 0) + 1
            
            # Count by handler
            handler = failed_event.handler_name or "unknown"
            by_handler[handler] = by_handler.get(handler, 0) + 1
            
            # Count retry states
            if failed_event.is_retry_due():
                retry_ready += 1
            elif failed_event.retry_count >= failed_event.max_retries:
                exhausted_retries += 1
        
        return {
            "total_events": len(self._failed_events),
            "by_reason": by_reason,
            "by_handler": by_handler,
            "retry_ready": retry_ready,
            "exhausted_retries": exhausted_retries,
        }
    
    def _classify_error(self, exception: Exception) -> FailureReason:
        """
        Classify an exception into a failure reason.
        
        Args:
            exception: The exception to classify
            
        Returns:
            The appropriate failure reason
        """
        exception_name = exception.__class__.__name__
        exception_message = str(exception).lower()
        
        if "timeout" in exception_message or "timeout" in exception_name.lower():
            return FailureReason.TIMEOUT
        
        if "validation" in exception_message or "validation" in exception_name.lower():
            return FailureReason.VALIDATION_ERROR
        
        if any(term in exception_message for term in ["serializ", "json", "pickle"]):
            return FailureReason.SERIALIZATION_ERROR
        
        if any(term in exception_message for term in ["connection", "network", "socket", "database"]):
            return FailureReason.INFRASTRUCTURE_ERROR
        
        return FailureReason.HANDLER_ERROR
    
    def _cleanup_old_events(self) -> None:
        """Remove events older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(days=self._retention_days)
        
        initial_count = len(self._failed_events)
        self._failed_events = [
            fe for fe in self._failed_events 
            if fe.failed_at > cutoff_time
        ]
        
        removed_count = initial_count - len(self._failed_events)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old events from dead letter queue")
    
    def _enforce_size_limit(self) -> None:
        """Enforce maximum queue size by removing oldest events."""
        if len(self._failed_events) <= self._max_queue_size:
            return
        
        # Sort by failed_at and keep only the newest events
        self._failed_events.sort(key=lambda fe: fe.failed_at, reverse=True)
        excess_count = len(self._failed_events) - self._max_queue_size
        self._failed_events = self._failed_events[:self._max_queue_size]
        
        logger.warning(f"Removed {excess_count} oldest events to enforce size limit")


# Default dead letter queue instance
_default_dead_letter_queue: Optional[DeadLetterQueue] = None


def get_dead_letter_queue() -> DeadLetterQueue:
    """Get the default dead letter queue."""
    global _default_dead_letter_queue
    if _default_dead_letter_queue is None:
        _default_dead_letter_queue = DeadLetterQueue()
    return _default_dead_letter_queue


def set_default_dead_letter_queue(dlq: DeadLetterQueue) -> None:
    """Set the default dead letter queue."""
    global _default_dead_letter_queue
    _default_dead_letter_queue = dlq


def reset_dead_letter_queue() -> None:
    """Reset the default dead letter queue (mainly for testing)."""
    global _default_dead_letter_queue
    _default_dead_letter_queue = None
