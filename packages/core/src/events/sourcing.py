"""
Event sourcing implementation for aggregate reconstruction.

Provides capabilities to rebuild aggregate state from stored events.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from .base import Event
from .store import EventStore, get_event_store

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='EventSourcedAggregate')


class EventSourcedAggregate(ABC):
    """
    Base class for event-sourced aggregates.
    
    Aggregates that inherit from this class can be reconstructed
    from their event history and can track uncommitted changes.
    """
    
    def __init__(self, aggregate_id: str):
        """
        Initialize the aggregate.
        
        Args:
            aggregate_id: Unique identifier for the aggregate
        """
        self._aggregate_id = aggregate_id
        self._version = 0
        self._uncommitted_events: List[Event] = []
        self._is_deleted = False
    
    @property
    def aggregate_id(self) -> str:
        """Get the aggregate identifier."""
        return self._aggregate_id
    
    @property
    def version(self) -> int:
        """Get the current version of the aggregate."""
        return self._version
    
    @property
    def uncommitted_events(self) -> List[Event]:
        """Get uncommitted events."""
        return self._uncommitted_events.copy()
    
    @property
    def is_deleted(self) -> bool:
        """Check if the aggregate has been deleted."""
        return self._is_deleted
    
    def mark_events_as_committed(self) -> None:
        """Mark all uncommitted events as committed."""
        self._uncommitted_events.clear()
    
    def load_from_history(self, events: List[Event]) -> None:
        """
        Reconstruct aggregate state from event history.
        
        Args:
            events: List of events in chronological order
        """
        for event in events:
            self._apply_event(event, is_replay=True)
        
        logger.debug(f"Loaded aggregate {self._aggregate_id} from {len(events)} events (version {self._version})")
    
    def apply_event(self, event: Event) -> None:
        """
        Apply a new event to the aggregate.
        
        Args:
            event: The event to apply
        """
        # Update event metadata with aggregate info
        event = event.with_metadata(
            aggregate_id=self._aggregate_id,
            aggregate_version=self._version + 1
        )
        
        self._apply_event(event, is_replay=False)
        self._uncommitted_events.append(event)
    
    def _apply_event(self, event: Event, is_replay: bool) -> None:
        """
        Apply an event to the aggregate state.
        
        Args:
            event: The event to apply
            is_replay: Whether this is a replay from history
        """
        # Update version
        if is_replay:
            self._version = event.metadata.aggregate_version
        else:
            self._version += 1
        
        # Apply the event to the aggregate state
        self._when(event)
    
    @abstractmethod
    def _when(self, event: Event) -> None:
        """
        Apply an event to update aggregate state.
        
        This method should contain the business logic for how
        each event type affects the aggregate's state.
        
        Args:
            event: The event to apply
        """
        pass
    
    def _mark_as_deleted(self) -> None:
        """Mark the aggregate as deleted."""
        self._is_deleted = True


class EventSourcing:
    """
    Event sourcing service for managing event-sourced aggregates.
    
    Provides functionality to save and load aggregates using event stores.
    """
    
    def __init__(self, event_store: Optional[EventStore] = None):
        """
        Initialize the event sourcing service.
        
        Args:
            event_store: Event store to use (uses default if None)
        """
        self._event_store = event_store or get_event_store()
        self._aggregate_factories: Dict[str, Type[EventSourcedAggregate]] = {}
    
    def register_aggregate(self, aggregate_class: Type[EventSourcedAggregate]) -> None:
        """
        Register an aggregate type for loading.
        
        Args:
            aggregate_class: The aggregate class to register
        """
        class_name = aggregate_class.__name__
        self._aggregate_factories[class_name] = aggregate_class
        logger.debug(f"Registered aggregate type: {class_name}")
    
    def save_aggregate(self, aggregate: EventSourcedAggregate) -> None:
        """
        Save an aggregate by persisting its uncommitted events.
        
        Args:
            aggregate: The aggregate to save
        """
        uncommitted_events = aggregate.uncommitted_events
        if not uncommitted_events:
            logger.debug(f"No uncommitted events for aggregate {aggregate.aggregate_id}")
            return
        
        # Save events to store
        self._event_store.save_events(uncommitted_events)
        
        # Mark events as committed
        aggregate.mark_events_as_committed()
        
        logger.info(f"Saved aggregate {aggregate.aggregate_id} with {len(uncommitted_events)} events")
    
    def load_aggregate(
        self,
        aggregate_class: Type[T],
        aggregate_id: str,
        expected_version: Optional[int] = None
    ) -> Optional[T]:
        """
        Load an aggregate from its event history.
        
        Args:
            aggregate_class: The aggregate class to instantiate
            aggregate_id: The aggregate identifier
            expected_version: Expected version for concurrency control
            
        Returns:
            The reconstructed aggregate or None if not found
            
        Raises:
            ConcurrencyError: If version doesn't match expected
        """
        # Load events for the aggregate
        events = self._event_store.load_aggregate_events(aggregate_id)
        
        if not events:
            logger.debug(f"No events found for aggregate {aggregate_id}")
            return None
        
        # Create aggregate instance
        aggregate = aggregate_class(aggregate_id)
        
        # Reconstruct from history
        aggregate.load_from_history(events)
        
        # Check version if specified
        if expected_version is not None and aggregate.version != expected_version:
            raise ConcurrencyError(
                f"Expected version {expected_version} but got {aggregate.version} "
                f"for aggregate {aggregate_id}"
            )
        
        logger.debug(f"Loaded aggregate {aggregate_id} (version {aggregate.version})")
        return aggregate
    
    def exists(self, aggregate_id: str) -> bool:
        """
        Check if an aggregate exists.
        
        Args:
            aggregate_id: The aggregate identifier
            
        Returns:
            True if the aggregate exists
        """
        event_count = self._event_store.get_event_count(aggregate_id=aggregate_id)
        return event_count > 0
    
    def get_version(self, aggregate_id: str) -> int:
        """
        Get the current version of an aggregate.
        
        Args:
            aggregate_id: The aggregate identifier
            
        Returns:
            Current version (0 if not found)
        """
        return self._event_store.get_aggregate_version(aggregate_id)
    
    def delete_aggregate(self, aggregate_id: str) -> int:
        """
        Delete all events for an aggregate.
        
        Args:
            aggregate_id: The aggregate identifier
            
        Returns:
            Number of deleted events
        """
        deleted_count = self._event_store.delete_events(aggregate_id=aggregate_id)
        logger.info(f"Deleted aggregate {aggregate_id} ({deleted_count} events)")
        return deleted_count
    
    def replay_aggregate(
        self,
        aggregate_class: Type[T],
        aggregate_id: str,
        to_version: Optional[int] = None
    ) -> Optional[T]:
        """
        Replay an aggregate to a specific version.
        
        Args:
            aggregate_class: The aggregate class to instantiate
            aggregate_id: The aggregate identifier
            to_version: Target version (None for latest)
            
        Returns:
            The aggregate at the specified version
        """
        # Load events up to the target version
        events = self._event_store.replay_events(
            aggregate_id=aggregate_id,
            from_version=1,
            to_version=to_version
        )
        
        if not events:
            return None
        
        # Create and reconstruct aggregate
        aggregate = aggregate_class(aggregate_id)
        aggregate.load_from_history(events)
        
        logger.debug(f"Replayed aggregate {aggregate_id} to version {aggregate.version}")
        return aggregate
    
    def get_aggregate_timeline(
        self,
        aggregate_id: str,
        event_types: Optional[List[Type[Event]]] = None
    ) -> List[Event]:
        """
        Get the complete event timeline for an aggregate.
        
        Args:
            aggregate_id: The aggregate identifier
            event_types: Filter by specific event types
            
        Returns:
            List of events in chronological order
        """
        return self._event_store.load_events(
            aggregate_id=aggregate_id,
            event_types=event_types
        )


class ConcurrencyError(Exception):
    """Exception raised when aggregate version conflicts occur."""
    pass


class Snapshot:
    """
    Snapshot of aggregate state for performance optimization.
    
    Snapshots can be used to avoid replaying all events
    for aggregates with long histories.
    """
    
    def __init__(
        self,
        aggregate_id: str,
        aggregate_type: str,
        version: int,
        state: Dict[str, Any],
        timestamp: Optional[str] = None
    ):
        """
        Initialize the snapshot.
        
        Args:
            aggregate_id: The aggregate identifier
            aggregate_type: The aggregate type name  
            version: The version at snapshot time
            state: The aggregate state data
            timestamp: When the snapshot was taken
        """
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        self.version = version
        self.state = state
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "version": self.version,
            "state": self.state,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Snapshot':
        """Create snapshot from dictionary."""
        return cls(
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            version=data["version"],
            state=data["state"],
            timestamp=data.get("timestamp"),
        )


# Default event sourcing instance
_default_event_sourcing: Optional[EventSourcing] = None


def get_event_sourcing() -> EventSourcing:
    """Get the default event sourcing service."""
    global _default_event_sourcing
    if _default_event_sourcing is None:
        _default_event_sourcing = EventSourcing()
    return _default_event_sourcing


def set_default_event_sourcing(event_sourcing: EventSourcing) -> None:
    """Set the default event sourcing service."""
    global _default_event_sourcing
    _default_event_sourcing = event_sourcing


def reset_event_sourcing() -> None:
    """Reset the default event sourcing service (mainly for testing)."""
    global _default_event_sourcing
    _default_event_sourcing = None
