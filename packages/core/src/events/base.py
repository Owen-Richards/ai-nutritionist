"""
Base event classes and metadata for the event-driven architecture.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar
from enum import Enum


class EventType(Enum):
    """Event type classifications."""
    DOMAIN = "domain"
    INTEGRATION = "integration"
    SYSTEM = "system"


@dataclass(frozen=True)
class EventMetadata:
    """
    Metadata associated with every event.
    
    Provides traceability, correlation, and operational context.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: EventType = EventType.DOMAIN
    aggregate_id: Optional[str] = None
    aggregate_version: int = 1
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    source: str = "ai-nutritionist"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_version": self.aggregate_version,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "user_id": self.user_id,
            "source": self.source,
        }


T = TypeVar('T', bound='Event')


class Event(ABC):
    """
    Base class for all events in the system.
    
    Events are immutable records of things that have happened.
    They carry both business data and operational metadata.
    """
    
    def __init__(self, metadata: Optional[EventMetadata] = None, **kwargs):
        """Initialize event with metadata and payload data."""
        self._metadata = metadata or EventMetadata()
        self._data = kwargs
        
    @property
    def metadata(self) -> EventMetadata:
        """Get event metadata."""
        return self._metadata
        
    @property
    def data(self) -> Dict[str, Any]:
        """Get event payload data."""
        return self._data.copy()
        
    @property
    def event_name(self) -> str:
        """Get the event name based on class name."""
        return self.__class__.__name__
        
    @property
    def event_id(self) -> str:
        """Get unique event identifier."""
        return self._metadata.event_id
        
    @property
    def timestamp(self) -> datetime:
        """Get event timestamp."""
        return self._metadata.timestamp
        
    @property
    def aggregate_id(self) -> Optional[str]:
        """Get aggregate identifier."""
        return self._metadata.aggregate_id
        
    def with_metadata(self: T, **metadata_kwargs) -> T:
        """Create new event instance with updated metadata."""
        new_metadata = EventMetadata(
            event_id=metadata_kwargs.get('event_id', self._metadata.event_id),
            timestamp=metadata_kwargs.get('timestamp', self._metadata.timestamp),
            event_type=metadata_kwargs.get('event_type', self._metadata.event_type),
            aggregate_id=metadata_kwargs.get('aggregate_id', self._metadata.aggregate_id),
            aggregate_version=metadata_kwargs.get('aggregate_version', self._metadata.aggregate_version),
            correlation_id=metadata_kwargs.get('correlation_id', self._metadata.correlation_id),
            causation_id=metadata_kwargs.get('causation_id', self._metadata.causation_id),
            user_id=metadata_kwargs.get('user_id', self._metadata.user_id),
            source=metadata_kwargs.get('source', self._metadata.source),
        )
        return self.__class__(metadata=new_metadata, **self._data)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_name": self.event_name,
            "metadata": self.metadata.to_dict(),
            "data": self.data,
        }
        
    @classmethod
    def from_dict(cls: Type[T], event_dict: Dict[str, Any]) -> T:
        """Create event instance from dictionary."""
        metadata_dict = event_dict.get("metadata", {})
        metadata = EventMetadata(
            event_id=metadata_dict.get("event_id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(metadata_dict.get("timestamp", datetime.utcnow().isoformat())),
            event_type=EventType(metadata_dict.get("event_type", EventType.DOMAIN.value)),
            aggregate_id=metadata_dict.get("aggregate_id"),
            aggregate_version=metadata_dict.get("aggregate_version", 1),
            correlation_id=metadata_dict.get("correlation_id"),
            causation_id=metadata_dict.get("causation_id"),
            user_id=metadata_dict.get("user_id"),
            source=metadata_dict.get("source", "ai-nutritionist"),
        )
        return cls(metadata=metadata, **event_dict.get("data", {}))
        
    def __repr__(self) -> str:
        """String representation of the event."""
        return f"{self.event_name}(id={self.event_id}, timestamp={self.timestamp})"
        
    def __eq__(self, other) -> bool:
        """Check equality based on event ID."""
        if not isinstance(other, Event):
            return False
        return self.event_id == other.event_id


class DomainEvent(Event):
    """
    Base class for domain events.
    
    Domain events represent business-meaningful occurrences
    within the application's domain model.
    """
    
    def __init__(self, aggregate_id: str, **kwargs):
        """Initialize domain event with aggregate identifier."""
        metadata = kwargs.pop('metadata', None)
        if metadata is None:
            metadata = EventMetadata(
                event_type=EventType.DOMAIN,
                aggregate_id=aggregate_id
            )
        else:
            metadata = EventMetadata(
                event_id=metadata.event_id,
                timestamp=metadata.timestamp,
                event_type=EventType.DOMAIN,
                aggregate_id=aggregate_id,
                aggregate_version=metadata.aggregate_version,
                correlation_id=metadata.correlation_id,
                causation_id=metadata.causation_id,
                user_id=metadata.user_id,
                source=metadata.source,
            )
        super().__init__(metadata=metadata, **kwargs)


class IntegrationEvent(Event):
    """
    Base class for integration events.
    
    Integration events are used for cross-bounded context
    communication and external system integration.
    """
    
    def __init__(self, **kwargs):
        """Initialize integration event."""
        metadata = kwargs.pop('metadata', None)
        if metadata is None:
            metadata = EventMetadata(event_type=EventType.INTEGRATION)
        super().__init__(metadata=metadata, **kwargs)


class SystemEvent(Event):
    """
    Base class for system events.
    
    System events represent operational occurrences
    like errors, monitoring, and infrastructure concerns.
    """
    
    def __init__(self, **kwargs):
        """Initialize system event."""
        metadata = kwargs.pop('metadata', None)
        if metadata is None:
            metadata = EventMetadata(event_type=EventType.SYSTEM)
        super().__init__(metadata=metadata, **kwargs)
