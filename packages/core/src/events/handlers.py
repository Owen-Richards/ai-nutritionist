"""
Event handlers for processing domain events.

Provides base classes and registration mechanisms for event handlers.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, Union
from .base import Event

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Base class for synchronous event handlers.
    
    Event handlers encapsulate the business logic that should
    be executed when specific events occur.
    """
    
    @abstractmethod
    def handle(self, event: Event) -> None:
        """
        Handle the given event.
        
        Args:
            event: The event to handle
            
        Raises:
            Exception: If handling fails
        """
        pass
    
    @property
    def event_types(self) -> List[Type[Event]]:
        """
        Get the event types this handler can process.
        
        Override this method to specify which events this handler supports.
        """
        return [Event]
    
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process the given event."""
        return any(isinstance(event, event_type) for event_type in self.event_types)


class AsyncEventHandler(ABC):
    """
    Base class for asynchronous event handlers.
    
    Async handlers are preferred for I/O intensive operations
    like external API calls, database operations, etc.
    """
    
    @abstractmethod
    async def handle(self, event: Event) -> None:
        """
        Handle the given event asynchronously.
        
        Args:
            event: The event to handle
            
        Raises:
            Exception: If handling fails
        """
        pass
    
    @property
    def event_types(self) -> List[Type[Event]]:
        """
        Get the event types this handler can process.
        
        Override this method to specify which events this handler supports.
        """
        return [Event]
    
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can process the given event."""
        return any(isinstance(event, event_type) for event_type in self.event_types)


class HandlerRegistry:
    """
    Registry for managing event handlers.
    
    Provides registration and lookup capabilities for both
    synchronous and asynchronous event handlers.
    """
    
    def __init__(self):
        """Initialize the handler registry."""
        self._sync_handlers: Dict[str, List[EventHandler]] = {}
        self._async_handlers: Dict[str, List[AsyncEventHandler]] = {}
        self._global_sync_handlers: List[EventHandler] = []
        self._global_async_handlers: List[AsyncEventHandler] = []
    
    def register_handler(
        self,
        handler: Union[EventHandler, AsyncEventHandler],
        event_types: Optional[List[Type[Event]]] = None
    ) -> None:
        """
        Register an event handler.
        
        Args:
            handler: The handler to register
            event_types: Specific event types to handle (optional)
        """
        if event_types is None:
            event_types = handler.event_types
            
        if isinstance(handler, AsyncEventHandler):
            if not event_types or event_types == [Event]:
                self._global_async_handlers.append(handler)
            else:
                for event_type in event_types:
                    event_name = event_type.__name__
                    if event_name not in self._async_handlers:
                        self._async_handlers[event_name] = []
                    self._async_handlers[event_name].append(handler)
        else:
            if not event_types or event_types == [Event]:
                self._global_sync_handlers.append(handler)
            else:
                for event_type in event_types:
                    event_name = event_type.__name__
                    if event_name not in self._sync_handlers:
                        self._sync_handlers[event_name] = []
                    self._sync_handlers[event_name].append(handler)
        
        logger.info(f"Registered handler {handler.__class__.__name__} for events: {[et.__name__ for et in event_types]}")
    
    def unregister_handler(self, handler: Union[EventHandler, AsyncEventHandler]) -> None:
        """
        Unregister an event handler.
        
        Args:
            handler: The handler to unregister
        """
        if isinstance(handler, AsyncEventHandler):
            # Remove from global handlers
            if handler in self._global_async_handlers:
                self._global_async_handlers.remove(handler)
            
            # Remove from specific event handlers
            for handlers_list in self._async_handlers.values():
                if handler in handlers_list:
                    handlers_list.remove(handler)
        else:
            # Remove from global handlers
            if handler in self._global_sync_handlers:
                self._global_sync_handlers.remove(handler)
            
            # Remove from specific event handlers
            for handlers_list in self._sync_handlers.values():
                if handler in handlers_list:
                    handlers_list.remove(handler)
        
        logger.info(f"Unregistered handler {handler.__class__.__name__}")
    
    def get_handlers(self, event: Event) -> tuple[List[EventHandler], List[AsyncEventHandler]]:
        """
        Get all handlers for a specific event.
        
        Args:
            event: The event to get handlers for
            
        Returns:
            Tuple of (sync_handlers, async_handlers)
        """
        event_name = event.event_name
        
        # Get specific handlers
        sync_handlers = self._sync_handlers.get(event_name, []).copy()
        async_handlers = self._async_handlers.get(event_name, []).copy()
        
        # Add global handlers that can handle this event
        for handler in self._global_sync_handlers:
            if handler.can_handle(event):
                sync_handlers.append(handler)
        
        for handler in self._global_async_handlers:
            if handler.can_handle(event):
                async_handlers.append(handler)
        
        return sync_handlers, async_handlers
    
    def clear(self) -> None:
        """Clear all registered handlers."""
        self._sync_handlers.clear()
        self._async_handlers.clear()
        self._global_sync_handlers.clear()
        self._global_async_handlers.clear()
        logger.info("Cleared all registered handlers")


# Decorator for registering event handlers
def event_handler(*event_types: Type[Event]):
    """
    Decorator for registering event handlers.
    
    Usage:
        @event_handler(UserRegistered, MealPlanCreated)
        class MyHandler(EventHandler):
            def handle(self, event: Event) -> None:
                # Handle the event
                pass
    """
    def decorator(handler_class):
        if hasattr(handler_class, '_event_types'):
            handler_class._event_types.extend(event_types)
        else:
            handler_class._event_types = list(event_types)
        
        # Override the event_types property
        def event_types_property(self):
            return self._event_types
        
        handler_class.event_types = property(event_types_property)
        return handler_class
    
    return decorator


# Functional handler support
HandlerFunction = Callable[[Event], None]
AsyncHandlerFunction = Callable[[Event], Awaitable[None]]


class FunctionalEventHandler(EventHandler):
    """Wrapper to use functions as event handlers."""
    
    def __init__(self, handler_func: HandlerFunction, event_types: List[Type[Event]]):
        """Initialize functional handler."""
        self._handler_func = handler_func
        self._event_types = event_types
    
    def handle(self, event: Event) -> None:
        """Handle event using the wrapped function."""
        self._handler_func(event)
    
    @property
    def event_types(self) -> List[Type[Event]]:
        """Get supported event types."""
        return self._event_types


class FunctionalAsyncEventHandler(AsyncEventHandler):
    """Wrapper to use async functions as event handlers."""
    
    def __init__(self, handler_func: AsyncHandlerFunction, event_types: List[Type[Event]]):
        """Initialize functional async handler."""
        self._handler_func = handler_func
        self._event_types = event_types
    
    async def handle(self, event: Event) -> None:
        """Handle event using the wrapped async function."""
        await self._handler_func(event)
    
    @property
    def event_types(self) -> List[Type[Event]]:
        """Get supported event types."""
        return self._event_types
