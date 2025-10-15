"""
Event bus implementations for routing and processing events.

Provides both synchronous and asynchronous event buses with
support for handler registration and event dispatch.
"""

import asyncio
import logging
from typing import List, Optional, Type, Union
from .base import Event
from .handlers import EventHandler, AsyncEventHandler, HandlerRegistry
from .dead_letter import DeadLetterQueue

logger = logging.getLogger(__name__)


class EventBusError(Exception):
    """Base exception for event bus operations."""
    pass


class EventBus:
    """
    Synchronous event bus for handling events.
    
    Manages event handlers and provides synchronous event processing.
    Suitable for lightweight operations that don't require async I/O.
    """
    
    def __init__(self, dead_letter_queue: Optional[DeadLetterQueue] = None):
        """
        Initialize the event bus.
        
        Args:
            dead_letter_queue: Queue for failed events (optional)
        """
        self._registry = HandlerRegistry()
        self._dead_letter_queue = dead_letter_queue
        self._middleware: List[callable] = []
    
    def register_handler(
        self,
        handler: EventHandler,
        event_types: Optional[List[Type[Event]]] = None
    ) -> None:
        """
        Register an event handler.
        
        Args:
            handler: The handler to register
            event_types: Specific event types to handle (optional)
        """
        if not isinstance(handler, EventHandler):
            raise EventBusError("Handler must be an instance of EventHandler")
        
        self._registry.register_handler(handler, event_types)
    
    def unregister_handler(self, handler: EventHandler) -> None:
        """
        Unregister an event handler.
        
        Args:
            handler: The handler to unregister
        """
        self._registry.unregister_handler(handler)
    
    def add_middleware(self, middleware: callable) -> None:
        """
        Add middleware to process events before handlers.
        
        Args:
            middleware: Function that takes an event and returns modified event or None
        """
        self._middleware.append(middleware)
    
    def publish(self, event: Event) -> None:
        """
        Publish an event to all registered handlers.
        
        Args:
            event: The event to publish
            
        Raises:
            EventBusError: If event processing fails critically
        """
        logger.debug(f"Publishing event: {event}")
        
        try:
            # Apply middleware
            processed_event = event
            for middleware in self._middleware:
                processed_event = middleware(processed_event)
                if processed_event is None:
                    logger.debug(f"Event filtered out by middleware: {event}")
                    return
            
            # Get handlers for this event
            sync_handlers, _ = self._registry.get_handlers(processed_event)
            
            if not sync_handlers:
                logger.debug(f"No handlers found for event: {processed_event}")
                return
            
            # Process with sync handlers
            failed_handlers = []
            for handler in sync_handlers:
                try:
                    handler.handle(processed_event)
                    logger.debug(f"Event handled by {handler.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Handler {handler.__class__.__name__} failed: {e}")
                    failed_handlers.append((handler, e))
            
            # Handle failures
            if failed_handlers:
                if self._dead_letter_queue:
                    self._dead_letter_queue.add(processed_event, failed_handlers)
                else:
                    logger.warning(f"Event processing had {len(failed_handlers)} failures but no dead letter queue configured")
        
        except Exception as e:
            logger.error(f"Critical error in event bus: {e}")
            if self._dead_letter_queue:
                self._dead_letter_queue.add(event, [("EventBus", e)])
            raise EventBusError(f"Failed to process event: {e}")


class AsyncEventBus:
    """
    Asynchronous event bus for handling events.
    
    Manages event handlers and provides asynchronous event processing.
    Preferred for I/O intensive operations and high-throughput scenarios.
    """
    
    def __init__(self, dead_letter_queue: Optional[DeadLetterQueue] = None):
        """
        Initialize the async event bus.
        
        Args:
            dead_letter_queue: Queue for failed events (optional)
        """
        self._registry = HandlerRegistry()
        self._dead_letter_queue = dead_letter_queue
        self._middleware: List[callable] = []
        self._concurrent_limit = 100  # Max concurrent handler executions
    
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
        if not isinstance(handler, (EventHandler, AsyncEventHandler)):
            raise EventBusError("Handler must be an instance of EventHandler or AsyncEventHandler")
        
        self._registry.register_handler(handler, event_types)
    
    def unregister_handler(self, handler: Union[EventHandler, AsyncEventHandler]) -> None:
        """
        Unregister an event handler.
        
        Args:
            handler: The handler to unregister
        """
        self._registry.unregister_handler(handler)
    
    def add_middleware(self, middleware: callable) -> None:
        """
        Add middleware to process events before handlers.
        
        Args:
            middleware: Function that takes an event and returns modified event or None
        """
        self._middleware.append(middleware)
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event to all registered handlers asynchronously.
        
        Args:
            event: The event to publish
            
        Raises:
            EventBusError: If event processing fails critically
        """
        logger.debug(f"Publishing event: {event}")
        
        try:
            # Apply middleware
            processed_event = event
            for middleware in self._middleware:
                if asyncio.iscoroutinefunction(middleware):
                    processed_event = await middleware(processed_event)
                else:
                    processed_event = middleware(processed_event)
                
                if processed_event is None:
                    logger.debug(f"Event filtered out by middleware: {event}")
                    return
            
            # Get handlers for this event
            sync_handlers, async_handlers = self._registry.get_handlers(processed_event)
            
            if not sync_handlers and not async_handlers:
                logger.debug(f"No handlers found for event: {processed_event}")
                return
            
            # Create tasks for all handlers
            tasks = []
            handler_info = []
            
            # Add sync handlers (wrapped in async)
            for handler in sync_handlers:
                async def sync_wrapper(h, e):
                    try:
                        h.handle(e)
                        return h, None
                    except Exception as ex:
                        return h, ex
                
                task = asyncio.create_task(sync_wrapper(handler, processed_event))
                tasks.append(task)
                handler_info.append(handler)
            
            # Add async handlers
            for handler in async_handlers:
                async def async_wrapper(h, e):
                    try:
                        await h.handle(e)
                        return h, None
                    except Exception as ex:
                        return h, ex
                
                task = asyncio.create_task(async_wrapper(handler, processed_event))
                tasks.append(task)
                handler_info.append(handler)
            
            # Execute all handlers with concurrency limit
            semaphore = asyncio.Semaphore(self._concurrent_limit)
            
            async def limited_execution(task):
                async with semaphore:
                    return await task
            
            limited_tasks = [limited_execution(task) for task in tasks]
            results = await asyncio.gather(*limited_tasks, return_exceptions=True)
            
            # Process results
            failed_handlers = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Handler {handler_info[i].__class__.__name__} failed: {result}")
                    failed_handlers.append((handler_info[i], result))
                elif result[1] is not None:  # Handler returned error
                    logger.error(f"Handler {result[0].__class__.__name__} failed: {result[1]}")
                    failed_handlers.append((result[0], result[1]))
                else:
                    logger.debug(f"Event handled by {result[0].__class__.__name__}")
            
            # Handle failures
            if failed_handlers:
                if self._dead_letter_queue:
                    await self._dead_letter_queue.add_async(processed_event, failed_handlers)
                else:
                    logger.warning(f"Event processing had {len(failed_handlers)} failures but no dead letter queue configured")
        
        except Exception as e:
            logger.error(f"Critical error in async event bus: {e}")
            if self._dead_letter_queue:
                await self._dead_letter_queue.add_async(event, [("AsyncEventBus", e)])
            raise EventBusError(f"Failed to process event: {e}")
    
    async def publish_batch(self, events: List[Event]) -> None:
        """
        Publish multiple events concurrently.
        
        Args:
            events: List of events to publish
        """
        if not events:
            return
        
        logger.debug(f"Publishing batch of {len(events)} events")
        
        # Create tasks for all events
        tasks = [self.publish(event) for event in events]
        
        # Execute with concurrency control
        semaphore = asyncio.Semaphore(self._concurrent_limit)
        
        async def limited_publish(task):
            async with semaphore:
                return await task
        
        limited_tasks = [limited_publish(task) for task in tasks]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        # Log any failures
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            logger.error(f"Batch processing had {len(failures)} event failures")
    
    def set_concurrent_limit(self, limit: int) -> None:
        """
        Set the maximum number of concurrent handler executions.
        
        Args:
            limit: Maximum concurrent executions
        """
        self._concurrent_limit = max(1, limit)
        logger.info(f"Set concurrent limit to {self._concurrent_limit}")


# Global event bus instances
_default_event_bus: Optional[EventBus] = None
_default_async_event_bus: Optional[AsyncEventBus] = None


def get_event_bus() -> EventBus:
    """Get the default synchronous event bus."""
    global _default_event_bus
    if _default_event_bus is None:
        _default_event_bus = EventBus()
    return _default_event_bus


def get_async_event_bus() -> AsyncEventBus:
    """Get the default asynchronous event bus."""
    global _default_async_event_bus
    if _default_async_event_bus is None:
        _default_async_event_bus = AsyncEventBus()
    return _default_async_event_bus


def reset_event_buses() -> None:
    """Reset the global event bus instances (mainly for testing)."""
    global _default_event_bus, _default_async_event_bus
    _default_event_bus = None
    _default_async_event_bus = None
