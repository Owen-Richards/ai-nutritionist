"""
Tests for the event-driven architecture system.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from packages.core.src.events import (
    Event, DomainEvent, EventMetadata, EventType,
    EventBus, AsyncEventBus,
    EventHandler, AsyncEventHandler,
    EventDispatcher,
    EventStore, InMemoryStorageBackend,
    EventSourcing, EventSourcedAggregate,
    DeadLetterQueue, FailedEvent, FailureReason,
    UserRegistered, MealPlanCreated, NutritionGoalSet,
    MealLogged, PaymentProcessed, HealthDataSynced,
    CoachingSessionCompleted, WeeklyReportGenerated,
)


class TestEventBase:
    """Test base event classes."""
    
    def test_event_metadata_creation(self):
        """Test event metadata creation."""
        metadata = EventMetadata(
            event_type=EventType.DOMAIN,
            aggregate_id="test-123",
            user_id="user-456"
        )
        
        assert metadata.event_type == EventType.DOMAIN
        assert metadata.aggregate_id == "test-123"
        assert metadata.user_id == "user-456"
        assert metadata.aggregate_version == 1
        assert metadata.source == "ai-nutritionist"
    
    def test_domain_event_creation(self):
        """Test domain event creation."""
        event = DomainEvent(
            aggregate_id="test-123",
            user_id="user-456",
            test_data="value"
        )
        
        assert event.aggregate_id == "test-123"
        assert event.metadata.user_id == "user-456"
        assert event.data["test_data"] == "value"
        assert event.metadata.event_type == EventType.DOMAIN
    
    def test_event_serialization(self):
        """Test event serialization/deserialization."""
        event = DomainEvent(
            aggregate_id="test-123",
            test_data="value",
            number=42
        )
        
        # Serialize
        event_dict = event.to_dict()
        assert "event_name" in event_dict
        assert "metadata" in event_dict
        assert "data" in event_dict
        
        # Deserialize
        restored_event = DomainEvent.from_dict(event_dict)
        assert restored_event.aggregate_id == event.aggregate_id
        assert restored_event.data["test_data"] == "value"
        assert restored_event.data["number"] == 42


class TestDomainEvents:
    """Test domain event implementations."""
    
    def test_user_registered_event(self):
        """Test UserRegistered event."""
        event = UserRegistered(
            user_id="user-123",
            email="test@example.com",
            profile_data={"name": "Test User"}
        )
        
        assert event.user_id == "user-123"
        assert event.email == "test@example.com"
        assert event.profile_data["name"] == "Test User"
        assert event.aggregate_id == "user-123"
    
    def test_meal_plan_created_event(self):
        """Test MealPlanCreated event."""
        week_start = datetime.now()
        event = MealPlanCreated(
            user_id="user-123",
            plan_id="plan-456",
            week_start=week_start,
            nutritional_targets={"calories": 2000}
        )
        
        assert event.user_id == "user-123"
        assert event.plan_id == "plan-456"
        assert event.week_start == week_start
        assert event.nutritional_targets["calories"] == 2000
    
    def test_meal_logged_event(self):
        """Test MealLogged event."""
        event = MealLogged(
            user_id="user-123",
            meal_id="meal-789",
            calories=450.5,
            nutritional_info={"protein": 25, "carbs": 30}
        )
        
        assert event.user_id == "user-123"
        assert event.meal_id == "meal-789"
        assert event.calories == 450.5
        assert event.nutritional_info["protein"] == 25


class TestEventHandlers:
    """Test event handler system."""
    
    def test_sync_event_handler(self):
        """Test synchronous event handler."""
        handled_events = []
        
        class TestHandler(EventHandler):
            def handle(self, event: Event) -> None:
                handled_events.append(event)
        
        handler = TestHandler()
        event = UserRegistered(user_id="test", email="test@example.com")
        
        handler.handle(event)
        assert len(handled_events) == 1
        assert handled_events[0] == event
    
    @pytest.mark.asyncio
    async def test_async_event_handler(self):
        """Test asynchronous event handler."""
        handled_events = []
        
        class TestAsyncHandler(AsyncEventHandler):
            async def handle(self, event: Event) -> None:
                handled_events.append(event)
        
        handler = TestAsyncHandler()
        event = UserRegistered(user_id="test", email="test@example.com")
        
        await handler.handle(event)
        assert len(handled_events) == 1
        assert handled_events[0] == event


class TestEventBus:
    """Test event bus implementations."""
    
    def test_sync_event_bus(self):
        """Test synchronous event bus."""
        handled_events = []
        
        class TestHandler(EventHandler):
            def handle(self, event: Event) -> None:
                handled_events.append(event)
        
        bus = EventBus()
        handler = TestHandler()
        bus.register_handler(handler)
        
        event = UserRegistered(user_id="test", email="test@example.com")
        bus.publish(event)
        
        assert len(handled_events) == 1
        assert handled_events[0] == event
    
    @pytest.mark.asyncio
    async def test_async_event_bus(self):
        """Test asynchronous event bus."""
        handled_events = []
        
        class TestAsyncHandler(AsyncEventHandler):
            async def handle(self, event: Event) -> None:
                handled_events.append(event)
        
        bus = AsyncEventBus()
        handler = TestAsyncHandler()
        bus.register_handler(handler)
        
        event = UserRegistered(user_id="test", email="test@example.com")
        await bus.publish(event)
        
        assert len(handled_events) == 1
        assert handled_events[0] == event
    
    @pytest.mark.asyncio
    async def test_async_event_bus_batch(self):
        """Test async event bus batch processing."""
        handled_events = []
        
        class TestAsyncHandler(AsyncEventHandler):
            async def handle(self, event: Event) -> None:
                handled_events.append(event)
        
        bus = AsyncEventBus()
        handler = TestAsyncHandler()
        bus.register_handler(handler)
        
        events = [
            UserRegistered(user_id="test1", email="test1@example.com"),
            UserRegistered(user_id="test2", email="test2@example.com"),
            UserRegistered(user_id="test3", email="test3@example.com"),
        ]
        
        await bus.publish_batch(events)
        
        assert len(handled_events) == 3


class TestEventStore:
    """Test event store and persistence."""
    
    def test_in_memory_storage_backend(self):
        """Test in-memory storage backend."""
        backend = InMemoryStorageBackend()
        
        event_data = {
            "event_name": "TestEvent",
            "metadata": {"event_id": "123", "timestamp": datetime.now().isoformat()},
            "data": {"test": "value"}
        }
        
        # Save event
        backend.save_event(event_data)
        
        # Load events
        events = backend.load_events()
        assert len(events) == 1
        assert events[0]["event_name"] == "TestEvent"
    
    def test_event_store_save_and_load(self):
        """Test event store save and load operations."""
        store = EventStore(InMemoryStorageBackend())
        store.register_event_type(UserRegistered)
        
        event = UserRegistered(user_id="test", email="test@example.com")
        
        # Save event
        store.save_event(event)
        
        # Load events
        loaded_events = store.load_events()
        assert len(loaded_events) == 1
        assert isinstance(loaded_events[0], UserRegistered)
        assert loaded_events[0].user_id == "test"
    
    def test_event_store_filtering(self):
        """Test event store filtering capabilities."""
        store = EventStore(InMemoryStorageBackend())
        store.register_event_type(UserRegistered)
        store.register_event_type(MealLogged)
        
        # Save different events
        user_event = UserRegistered(user_id="user1", email="test@example.com")
        meal_event = MealLogged(user_id="user1", meal_id="meal1", calories=500)
        
        store.save_event(user_event)
        store.save_event(meal_event)
        
        # Filter by event type
        user_events = store.load_events(event_types=[UserRegistered])
        assert len(user_events) == 1
        assert isinstance(user_events[0], UserRegistered)
        
        # Filter by aggregate ID
        user1_events = store.load_events(aggregate_id="user1")
        assert len(user1_events) == 1  # UserRegistered has aggregate_id = user_id


class TestEventSourcing:
    """Test event sourcing capabilities."""
    
    def test_event_sourced_aggregate(self):
        """Test event sourced aggregate base class."""
        
        class TestAggregate(EventSourcedAggregate):
            def __init__(self, aggregate_id: str):
                super().__init__(aggregate_id)
                self.name = ""
                self.email = ""
            
            def _when(self, event: Event) -> None:
                if isinstance(event, UserRegistered):
                    self.email = event.email
        
        aggregate = TestAggregate("test-123")
        event = UserRegistered(user_id="test-123", email="test@example.com")
        
        # Apply event
        aggregate.apply_event(event)
        
        assert aggregate.email == "test@example.com"
        assert aggregate.version == 1
        assert len(aggregate.uncommitted_events) == 1
    
    def test_aggregate_reconstruction(self):
        """Test aggregate reconstruction from events."""
        
        class TestAggregate(EventSourcedAggregate):
            def __init__(self, aggregate_id: str):
                super().__init__(aggregate_id)
                self.email = ""
                self.goals = []
            
            def _when(self, event: Event) -> None:
                if isinstance(event, UserRegistered):
                    self.email = event.email
                elif isinstance(event, NutritionGoalSet):
                    self.goals.append(event.goal_type)
        
        # Create events
        events = [
            UserRegistered(user_id="test", email="test@example.com"),
            NutritionGoalSet(user_id="test", goal_type="calories", target_value=2000, unit="kcal"),
        ]
        
        # Set proper metadata
        for i, event in enumerate(events):
            events[i] = event.with_metadata(aggregate_version=i + 1)
        
        # Reconstruct aggregate
        aggregate = TestAggregate("test")
        aggregate.load_from_history(events)
        
        assert aggregate.email == "test@example.com"
        assert "calories" in aggregate.goals
        assert aggregate.version == 2


class TestDeadLetterQueue:
    """Test dead letter queue functionality."""
    
    def test_dead_letter_queue_creation(self):
        """Test dead letter queue creation."""
        dlq = DeadLetterQueue(max_queue_size=100, retention_days=7)
        assert dlq._max_queue_size == 100
        assert dlq._retention_days == 7
    
    def test_add_failed_event(self):
        """Test adding failed events to queue."""
        dlq = DeadLetterQueue()
        event = UserRegistered(user_id="test", email="test@example.com")
        
        # Simulate handler failure
        failures = [("TestHandler", Exception("Test error"))]
        dlq.add(event, failures)
        
        failed_events = dlq.get_failed_events()
        assert len(failed_events) == 1
        assert failed_events[0].event == event
        assert failed_events[0].error_message == "Test error"
    
    def test_retry_logic(self):
        """Test retry logic for failed events."""
        dlq = DeadLetterQueue()
        event = UserRegistered(user_id="test", email="test@example.com")
        
        failures = [("TestHandler", Exception("Test error"))]
        dlq.add(event, failures, max_retries=2)
        
        failed_events = dlq.get_failed_events()
        failed_event = failed_events[0]
        
        # Initially not ready for retry (due to delay)
        assert not failed_event.is_retry_due()
        
        # Simulate time passing
        failed_event.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
        assert failed_event.is_retry_due()
        
        # Mark retry attempted
        dlq.mark_retry_attempted(failed_event)
        assert failed_event.retry_count == 1
    
    def test_queue_statistics(self):
        """Test dead letter queue statistics."""
        dlq = DeadLetterQueue()
        event = UserRegistered(user_id="test", email="test@example.com")
        
        failures = [
            ("Handler1", Exception("Error 1")),
            ("Handler2", TimeoutError("Timeout")),
        ]
        dlq.add(event, failures)
        
        stats = dlq.get_stats()
        assert stats["total_events"] == 2
        assert "handler_error" in stats["by_reason"]
        assert "timeout" in stats["by_reason"]


class TestEventDispatcher:
    """Test event dispatcher functionality."""
    
    def test_event_dispatcher_creation(self):
        """Test event dispatcher creation."""
        dispatcher = EventDispatcher()
        assert dispatcher._sync_bus is not None
        assert dispatcher._async_bus is not None
    
    def test_sync_subscription(self):
        """Test synchronous event subscription."""
        dispatcher = EventDispatcher()
        handled_events = []
        
        def handler(event: Event):
            handled_events.append(event)
        
        dispatcher.subscribe(UserRegistered, handler)
        
        event = UserRegistered(user_id="test", email="test@example.com")
        dispatcher.publish(event)
        
        assert len(handled_events) == 1
        assert handled_events[0] == event
    
    @pytest.mark.asyncio
    async def test_async_subscription(self):
        """Test asynchronous event subscription."""
        dispatcher = EventDispatcher()
        handled_events = []
        
        async def async_handler(event: Event):
            handled_events.append(event)
        
        dispatcher.subscribe(UserRegistered, async_handler)
        
        event = UserRegistered(user_id="test", email="test@example.com")
        await dispatcher.publish_async(event)
        
        assert len(handled_events) == 1
        assert handled_events[0] == event


class TestIntegration:
    """Integration tests for the complete event system."""
    
    @pytest.mark.asyncio
    async def test_complete_event_flow(self):
        """Test complete event-driven flow."""
        # Setup components
        dispatcher = EventDispatcher()
        handled_events = []
        
        class TestHandler(AsyncEventHandler):
            @property
            def event_types(self):
                return [UserRegistered, MealLogged]
            
            async def handle(self, event: Event):
                handled_events.append(event)
        
        # Register handler
        handler = TestHandler()
        dispatcher.subscribe(UserRegistered, handler)
        dispatcher.subscribe(MealLogged, handler)
        
        # Create and publish events
        events = [
            UserRegistered(user_id="user1", email="user1@example.com"),
            MealLogged(user_id="user1", meal_id="meal1", calories=500),
        ]
        
        await dispatcher.publish_batch(events)
        
        # Verify handling
        assert len(handled_events) == 2
        assert isinstance(handled_events[0], UserRegistered)
        assert isinstance(handled_events[1], MealLogged)
    
    def test_event_store_integration(self):
        """Test integration with event store."""
        store = EventStore(InMemoryStorageBackend())
        
        # Register event types
        event_types = [
            UserRegistered, MealPlanCreated, NutritionGoalSet,
            MealLogged, PaymentProcessed, HealthDataSynced,
            CoachingSessionCompleted, WeeklyReportGenerated
        ]
        
        for event_type in event_types:
            store.register_event_type(event_type)
        
        # Create and save events
        events = [
            UserRegistered(user_id="user1", email="user1@example.com"),
            NutritionGoalSet(user_id="user1", goal_type="calories", target_value=2000, unit="kcal"),
            MealLogged(user_id="user1", meal_id="meal1", calories=500),
        ]
        
        store.save_events(events)
        
        # Load and verify
        loaded_events = store.load_events(aggregate_id="user1")
        assert len(loaded_events) == 2  # UserRegistered and NutritionGoalSet have aggregate_id = user_id
        
        all_events = store.load_events()
        assert len(all_events) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
