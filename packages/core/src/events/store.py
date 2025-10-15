"""
Event store for persisting and retrieving events.

Provides event sourcing capabilities with support for different storage backends.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol, Type
from .base import Event, EventMetadata

logger = logging.getLogger(__name__)


class EventStoreError(Exception):
    """Base exception for event store operations."""
    pass


class StorageBackend(Protocol):
    """Protocol for event storage backends."""
    
    def save_event(self, event_data: Dict[str, Any]) -> None:
        """Save an event to storage."""
        ...
    
    def load_events(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Load events from storage."""
        ...
    
    def delete_events(
        self,
        aggregate_id: Optional[str] = None,
        before_time: Optional[datetime] = None
    ) -> int:
        """Delete events from storage."""
        ...


class InMemoryStorageBackend:
    """In-memory storage backend for testing and development."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        self._events: List[Dict[str, Any]] = []
    
    def save_event(self, event_data: Dict[str, Any]) -> None:
        """Save an event to memory."""
        self._events.append(event_data.copy())
    
    def load_events(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Load events from memory."""
        filtered_events = []
        
        for event_data in self._events:
            # Filter by aggregate_id
            if aggregate_id is not None:
                event_aggregate_id = event_data.get("metadata", {}).get("aggregate_id")
                if event_aggregate_id != aggregate_id:
                    continue
            
            # Filter by event types
            if event_types is not None:
                event_name = event_data.get("event_name")
                if event_name not in event_types:
                    continue
            
            # Filter by time range
            event_timestamp_str = event_data.get("metadata", {}).get("timestamp")
            if event_timestamp_str:
                event_timestamp = datetime.fromisoformat(event_timestamp_str)
                
                if start_time is not None and event_timestamp < start_time:
                    continue
                
                if end_time is not None and event_timestamp > end_time:
                    continue
            
            filtered_events.append(event_data)
        
        # Sort by timestamp
        filtered_events.sort(key=lambda e: e.get("metadata", {}).get("timestamp", ""))
        
        # Apply limit
        if limit is not None:
            filtered_events = filtered_events[:limit]
        
        return filtered_events
    
    def delete_events(
        self,
        aggregate_id: Optional[str] = None,
        before_time: Optional[datetime] = None
    ) -> int:
        """Delete events from memory."""
        initial_count = len(self._events)
        remaining_events = []
        
        for event_data in self._events:
            should_delete = False
            
            # Check aggregate_id filter
            if aggregate_id is not None:
                event_aggregate_id = event_data.get("metadata", {}).get("aggregate_id")
                if event_aggregate_id == aggregate_id:
                    should_delete = True
            
            # Check time filter
            if before_time is not None:
                event_timestamp_str = event_data.get("metadata", {}).get("timestamp")
                if event_timestamp_str:
                    event_timestamp = datetime.fromisoformat(event_timestamp_str)
                    if event_timestamp < before_time:
                        should_delete = True
            
            # If no filters specified, don't delete anything
            if aggregate_id is None and before_time is None:
                should_delete = False
            
            if not should_delete:
                remaining_events.append(event_data)
        
        self._events = remaining_events
        deleted_count = initial_count - len(self._events)
        return deleted_count
    
    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()


class EventStore:
    """
    Event store for persisting and retrieving domain events.
    
    Provides event sourcing capabilities with support for
    different storage backends and event replay.
    """
    
    def __init__(self, storage_backend: StorageBackend):
        """
        Initialize the event store.
        
        Args:
            storage_backend: Storage backend implementation
        """
        self._storage = storage_backend
        self._event_registry: Dict[str, Type[Event]] = {}
    
    def register_event_type(self, event_class: Type[Event]) -> None:
        """
        Register an event type for deserialization.
        
        Args:
            event_class: Event class to register
        """
        self._event_registry[event_class.__name__] = event_class
        logger.debug(f"Registered event type: {event_class.__name__}")
    
    def save_event(self, event: Event) -> None:
        """
        Save an event to the store.
        
        Args:
            event: The event to save
            
        Raises:
            EventStoreError: If saving fails
        """
        try:
            event_data = event.to_dict()
            self._storage.save_event(event_data)
            logger.debug(f"Saved event: {event}")
        except Exception as e:
            raise EventStoreError(f"Failed to save event: {e}")
    
    def save_events(self, events: List[Event]) -> None:
        """
        Save multiple events to the store.
        
        Args:
            events: List of events to save
            
        Raises:
            EventStoreError: If saving fails
        """
        for event in events:
            self.save_event(event)
        logger.info(f"Saved {len(events)} events")
    
    def load_events(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[Type[Event]]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Event]:
        """
        Load events from the store.
        
        Args:
            aggregate_id: Filter by aggregate ID
            event_types: Filter by event types
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return
            
        Returns:
            List of events matching the criteria
            
        Raises:
            EventStoreError: If loading fails
        """
        try:
            # Convert event types to names
            event_type_names = None
            if event_types is not None:
                event_type_names = [et.__name__ for et in event_types]
            
            # Load raw event data
            event_data_list = self._storage.load_events(
                aggregate_id=aggregate_id,
                event_types=event_type_names,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            # Deserialize events
            events = []
            for event_data in event_data_list:
                try:
                    event = self._deserialize_event(event_data)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to deserialize event: {e}")
            
            logger.debug(f"Loaded {len(events)} events")
            return events
            
        except Exception as e:
            raise EventStoreError(f"Failed to load events: {e}")
    
    def load_aggregate_events(self, aggregate_id: str) -> List[Event]:
        """
        Load all events for a specific aggregate.
        
        Args:
            aggregate_id: The aggregate identifier
            
        Returns:
            List of events for the aggregate, ordered by timestamp
        """
        return self.load_events(aggregate_id=aggregate_id)
    
    def delete_events(
        self,
        aggregate_id: Optional[str] = None,
        before_time: Optional[datetime] = None
    ) -> int:
        """
        Delete events from the store.
        
        Args:
            aggregate_id: Delete events for specific aggregate
            before_time: Delete events before this time
            
        Returns:
            Number of deleted events
            
        Raises:
            EventStoreError: If deletion fails
        """
        try:
            deleted_count = self._storage.delete_events(aggregate_id, before_time)
            logger.info(f"Deleted {deleted_count} events")
            return deleted_count
        except Exception as e:
            raise EventStoreError(f"Failed to delete events: {e}")
    
    def get_event_count(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[Type[Event]]] = None
    ) -> int:
        """
        Get count of events matching criteria.
        
        Args:
            aggregate_id: Filter by aggregate ID
            event_types: Filter by event types
            
        Returns:
            Number of matching events
        """
        events = self.load_events(aggregate_id=aggregate_id, event_types=event_types)
        return len(events)
    
    def _deserialize_event(self, event_data: Dict[str, Any]) -> Optional[Event]:
        """
        Deserialize event data into an Event instance.
        
        Args:
            event_data: Raw event data
            
        Returns:
            Event instance or None if deserialization fails
        """
        event_name = event_data.get("event_name")
        if not event_name or event_name not in self._event_registry:
            logger.warning(f"Unknown event type: {event_name}")
            return None
        
        event_class = self._event_registry[event_name]
        return event_class.from_dict(event_data)
    
    def replay_events(
        self,
        aggregate_id: str,
        from_version: int = 1,
        to_version: Optional[int] = None
    ) -> List[Event]:
        """
        Replay events for an aggregate within version range.
        
        Args:
            aggregate_id: The aggregate identifier
            from_version: Starting version (inclusive)
            to_version: Ending version (inclusive, None for latest)
            
        Returns:
            List of events in version order
        """
        events = self.load_aggregate_events(aggregate_id)
        
        # Filter by version if specified
        if from_version > 1 or to_version is not None:
            filtered_events = []
            for event in events:
                version = event.metadata.aggregate_version
                if version >= from_version:
                    if to_version is None or version <= to_version:
                        filtered_events.append(event)
            events = filtered_events
        
        return events
    
    def get_aggregate_version(self, aggregate_id: str) -> int:
        """
        Get the current version of an aggregate.
        
        Args:
            aggregate_id: The aggregate identifier
            
        Returns:
            Current version number
        """
        events = self.load_aggregate_events(aggregate_id)
        if not events:
            return 0
        
        return max(event.metadata.aggregate_version for event in events)


# Default event store instance
_default_event_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    """Get the default event store (uses in-memory backend)."""
    global _default_event_store
    if _default_event_store is None:
        _default_event_store = EventStore(InMemoryStorageBackend())
    return _default_event_store


def set_default_event_store(event_store: EventStore) -> None:
    """Set the default event store."""
    global _default_event_store
    _default_event_store = event_store


def reset_event_store() -> None:
    """Reset the default event store (mainly for testing)."""
    global _default_event_store
    _default_event_store = None
