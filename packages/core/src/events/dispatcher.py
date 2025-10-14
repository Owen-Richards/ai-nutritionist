"""
Event dispatcher for managing event routing and processing.

Provides a high-level interface for event publication and subscription.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union
from .base import Event
from .bus import EventBus, AsyncEventBus, get_event_bus, get_async_event_bus
from .handlers import (
    EventHandler, 
    AsyncEventHandler, 
    FunctionalEventHandler, 
    FunctionalAsyncEventHandler,
    HandlerFunction,
    AsyncHandlerFunction
)

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    High-level event dispatcher for managing event flow.
    
    Provides a unified interface for event publication, subscription,
    and handler management across both sync and async event buses.
    """
    
    def __init__(
        self,
        sync_bus: Optional[EventBus] = None,
        async_bus: Optional[AsyncEventBus] = None
    ):
        """
        Initialize the event dispatcher.
        
        Args:
            sync_bus: Synchronous event bus (uses default if None)
            async_bus: Asynchronous event bus (uses default if None)
        """
        self._sync_bus = sync_bus or get_event_bus()
        self._async_bus = async_bus or get_async_event_bus()
        self._subscriptions: Dict[str, List[Any]] = {}
    
    def publish(self, event: Event) -> None:
        """
        Publish an event synchronously.
        
        Args:
            event: The event to publish
        """
        logger.debug(f"Dispatching event synchronously: {event}")
        self._sync_bus.publish(event)
    
    async def publish_async(self, event: Event) -> None:
        """
        Publish an event asynchronously.
        
        Args:
            event: The event to publish
        """
        logger.debug(f"Dispatching event asynchronously: {event}")
        await self._async_bus.publish(event)
    
    async def publish_batch(self, events: List[Event]) -> None:
        """
        Publish multiple events asynchronously.
        
        Args:
            events: List of events to publish
        """
        logger.debug(f"Dispatching batch of {len(events)} events")
        await self._async_bus.publish_batch(events)
    
    def subscribe(
        self,
        event_type: Type[Event],
        handler: Union[EventHandler, AsyncEventHandler, HandlerFunction, AsyncHandlerFunction],
        async_handler: bool = None
    ) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: The event type to subscribe to
            handler: The handler (class instance or function)
            async_handler: Whether to use async bus (auto-detected if None)
        """
        # Auto-detect async requirement
        if async_handler is None:
            async_handler = (
                isinstance(handler, AsyncEventHandler) or
                asyncio.iscoroutinefunction(handler)
            )
        
        # Convert functions to handler instances
        if callable(handler) and not isinstance(handler, (EventHandler, AsyncEventHandler)):
            if async_handler:
                handler = FunctionalAsyncEventHandler(handler, [event_type])
            else:
                handler = FunctionalEventHandler(handler, [event_type])
        
        # Register with appropriate bus
        if async_handler:
            self._async_bus.register_handler(handler, [event_type])
        else:
            self._sync_bus.register_handler(handler, [event_type])
        
        # Track subscription
        event_name = event_type.__name__
        if event_name not in self._subscriptions:
            self._subscriptions[event_name] = []
        self._subscriptions[event_name].append(handler)
        
        logger.info(f"Subscribed {handler.__class__.__name__} to {event_name}")
    
    def unsubscribe(
        self,
        event_type: Type[Event],
        handler: Union[EventHandler, AsyncEventHandler]
    ) -> None:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to unsubscribe
        """
        # Remove from appropriate bus
        if isinstance(handler, AsyncEventHandler):
            self._async_bus.unregister_handler(handler)
        else:
            self._sync_bus.unregister_handler(handler)
        
        # Remove from tracking
        event_name = event_type.__name__
        if event_name in self._subscriptions and handler in self._subscriptions[event_name]:
            self._subscriptions[event_name].remove(handler)
        
        logger.info(f"Unsubscribed {handler.__class__.__name__} from {event_name}")
    
    def get_subscriptions(self, event_type: Type[Event]) -> List[Any]:
        """
        Get all subscriptions for an event type.
        
        Args:
            event_type: The event type to check
            
        Returns:
            List of subscribed handlers
        """
        event_name = event_type.__name__
        return self._subscriptions.get(event_name, []).copy()
    
    def clear_subscriptions(self, event_type: Optional[Type[Event]] = None) -> None:
        """
        Clear subscriptions for a specific event type or all types.
        
        Args:
            event_type: Specific event type to clear (clears all if None)
        """
        if event_type is None:
            self._subscriptions.clear()
            logger.info("Cleared all event subscriptions")
        else:
            event_name = event_type.__name__
            if event_name in self._subscriptions:
                del self._subscriptions[event_name]
            logger.info(f"Cleared subscriptions for {event_name}")
    
    def add_middleware(self, middleware: Callable) -> None:
        """
        Add middleware to both event buses.
        
        Args:
            middleware: Middleware function
        """
        self._sync_bus.add_middleware(middleware)
        self._async_bus.add_middleware(middleware)
        logger.info(f"Added middleware: {middleware.__name__}")


# Decorator-based subscription
def subscribe_to(*event_types: Type[Event], async_handler: bool = False):
    """
    Decorator for subscribing handler classes to events.
    
    Usage:
        @subscribe_to(UserRegistered, MealPlanCreated)
        class MyHandler(EventHandler):
            def handle(self, event: Event) -> None:
                # Handle the event
                pass
    
    Args:
        event_types: Event types to subscribe to
        async_handler: Whether to use async event bus
    """
    def decorator(handler_class):
        # Store subscription info on the class
        if not hasattr(handler_class, '_event_subscriptions'):
            handler_class._event_subscriptions = []
        
        for event_type in event_types:
            handler_class._event_subscriptions.append((event_type, async_handler))
        
        return handler_class
    
    return decorator


def auto_register_handlers(
    dispatcher: EventDispatcher,
    handler_instances: List[Union[EventHandler, AsyncEventHandler]]
) -> None:
    """
    Auto-register handlers that have subscription decorators.
    
    Args:
        dispatcher: The event dispatcher
        handler_instances: List of handler instances to register
    """
    for handler in handler_instances:
        if hasattr(handler.__class__, '_event_subscriptions'):
            for event_type, async_handler in handler.__class__._event_subscriptions:
                dispatcher.subscribe(event_type, handler, async_handler)
                logger.info(f"Auto-registered {handler.__class__.__name__} for {event_type.__name__}")


# Global event dispatcher
_default_dispatcher: Optional[EventDispatcher] = None


def get_dispatcher() -> EventDispatcher:
    """Get the default event dispatcher."""
    global _default_dispatcher
    if _default_dispatcher is None:
        _default_dispatcher = EventDispatcher()
    return _default_dispatcher


def reset_dispatcher() -> None:
    """Reset the global event dispatcher (mainly for testing)."""
    global _default_dispatcher
    _default_dispatcher = None


# Convenience functions for common operations
def publish(event: Event) -> None:
    """Publish an event using the default dispatcher."""
    get_dispatcher().publish(event)


async def publish_async(event: Event) -> None:
    """Publish an event asynchronously using the default dispatcher."""
    await get_dispatcher().publish_async(event)


def subscribe(
    event_type: Type[Event],
    handler: Union[EventHandler, AsyncEventHandler, HandlerFunction, AsyncHandlerFunction]
) -> None:
    """Subscribe to an event using the default dispatcher."""
    get_dispatcher().subscribe(event_type, handler)
