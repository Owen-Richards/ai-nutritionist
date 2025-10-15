# Event-Driven Architecture System

A comprehensive event-driven architecture implementation for the AI Nutritionist application, providing domain events, event sourcing, async processing, and failure handling capabilities.

## Overview

This event system enables loose coupling between application components through domain events. It supports:

- **Domain Events**: Business-meaningful events that represent state changes
- **Event Bus**: Synchronous and asynchronous event routing
- **Event Handlers**: Pluggable business logic processors
- **Event Store**: Persistence and retrieval of events
- **Event Sourcing**: Aggregate reconstruction from event history
- **Dead Letter Queue**: Failed event handling and retry mechanisms

## Quick Start

### 1. Basic Event Publishing

```python
from packages.core.src.events import (
    UserRegistered,
    get_dispatcher,
    publish,
    publish_async
)

# Create an event
event = UserRegistered(
    user_id="user-123",
    email="john@example.com",
    profile_data={"name": "John Doe"}
)

# Publish synchronously
publish(event)

# Publish asynchronously
await publish_async(event)
```

### 2. Creating Event Handlers

```python
from packages.core.src.events import EventHandler, AsyncEventHandler, event_handler

# Synchronous handler
@event_handler(UserRegistered)
class WelcomeEmailHandler(EventHandler):
    def handle(self, event: Event) -> None:
        if isinstance(event, UserRegistered):
            print(f"Sending welcome email to {event.email}")

# Asynchronous handler
class UserProfileHandler(AsyncEventHandler):
    @property
    def event_types(self):
        return [UserRegistered, NutritionGoalSet]

    async def handle(self, event: Event) -> None:
        if isinstance(event, UserRegistered):
            await self.create_user_profile(event.user_id)
        elif isinstance(event, NutritionGoalSet):
            await self.update_goals(event.user_id, event.goal_type)
```

### 3. Event Subscription

```python
from packages.core.src.events import get_dispatcher

dispatcher = get_dispatcher()

# Subscribe handlers
welcome_handler = WelcomeEmailHandler()
profile_handler = UserProfileHandler()

dispatcher.subscribe(UserRegistered, welcome_handler)
dispatcher.subscribe(UserRegistered, profile_handler)
dispatcher.subscribe(NutritionGoalSet, profile_handler)
```

## Domain Events

The system includes pre-built domain events for the nutrition domain:

### User Events

- **UserRegistered**: New user registration
- **NutritionGoalSet**: User sets nutrition goals

### Meal Events

- **MealPlanCreated**: Meal plan generation
- **MealLogged**: User logs a meal

### Health Events

- **HealthDataSynced**: External health data sync
- **CoachingSessionCompleted**: AI coaching session

### Business Events

- **PaymentProcessed**: Subscription payment
- **WeeklyReportGenerated**: Automated reporting

### Example Usage

```python
from datetime import datetime
from packages.core.src.events import *

# User registration flow
user_event = UserRegistered(
    user_id="user-123",
    email="john@example.com",
    profile_data={
        "name": "John Doe",
        "age": 30,
        "dietary_preferences": ["vegetarian"]
    }
)

# Meal planning
meal_plan_event = MealPlanCreated(
    user_id="user-123",
    plan_id="plan-456",
    week_start=datetime.now(),
    nutritional_targets={
        "calories": 2000,
        "protein": 150,
        "carbs": 250,
        "fat": 67
    },
    meal_count=21
)

# Nutrition tracking
goal_event = NutritionGoalSet(
    user_id="user-123",
    goal_type="weight_loss",
    target_value=2.0,
    unit="kg",
    timeline="monthly"
)
```

## Event Sourcing

Implement event-sourced aggregates to maintain state through events:

```python
from packages.core.src.events import EventSourcedAggregate, EventSourcing

class UserAggregate(EventSourcedAggregate):
    def __init__(self, user_id: str):
        super().__init__(user_id)
        self.email = ""
        self.goals = {}
        self.meal_count = 0

    def _when(self, event: Event) -> None:
        if isinstance(event, UserRegistered):
            self.email = event.email
        elif isinstance(event, NutritionGoalSet):
            self.goals[event.goal_type] = event.target_value
        elif isinstance(event, MealLogged):
            self.meal_count += 1

# Usage
sourcing = EventSourcing()
sourcing.register_aggregate(UserAggregate)

# Create new aggregate
user = UserAggregate("user-123")
user.apply_event(UserRegistered(user_id="user-123", email="john@example.com"))
user.apply_event(NutritionGoalSet(user_id="user-123", goal_type="calories", target_value=2000, unit="kcal"))

# Save aggregate
sourcing.save_aggregate(user)

# Load aggregate later
loaded_user = sourcing.load_aggregate(UserAggregate, "user-123")
print(f"User email: {loaded_user.email}")
print(f"Goals: {loaded_user.goals}")
```

## Event Store

Persist and query events for audit trails and analytics:

```python
from packages.core.src.events import get_event_store

store = get_event_store()

# Register event types
store.register_event_type(UserRegistered)
store.register_event_type(MealLogged)

# Save events
events = [
    UserRegistered(user_id="user-123", email="john@example.com"),
    MealLogged(user_id="user-123", meal_id="meal-1", calories=500)
]
store.save_events(events)

# Query events
user_events = store.load_events(aggregate_id="user-123")
recent_events = store.load_events(
    start_time=datetime.now() - timedelta(days=7),
    limit=100
)

# Get event timeline
timeline = store.load_events(
    event_types=[MealLogged],
    start_time=datetime.now() - timedelta(days=30)
)
```

## Error Handling & Dead Letter Queue

Handle failed events with automatic retry and dead letter queue:

```python
from packages.core.src.events import get_dead_letter_queue

dlq = get_dead_letter_queue()

# Check failed events
failed_events = dlq.get_failed_events()
print(f"Failed events: {len(failed_events)}")

# Get retry-ready events
retry_events = dlq.get_retry_ready_events()
for failed_event in retry_events:
    try:
        # Retry processing
        await process_event(failed_event.event)
        dlq.mark_retry_successful(failed_event)
    except Exception:
        dlq.mark_retry_attempted(failed_event)

# Get statistics
stats = dlq.get_stats()
print(f"Total failed: {stats['total_events']}")
print(f"By reason: {stats['by_reason']}")
```

## Advanced Features

### Middleware

Add cross-cutting concerns with middleware:

```python
def logging_middleware(event: Event) -> Event:
    print(f"Processing event: {event.event_name}")
    return event

def user_context_middleware(event: Event) -> Event:
    if hasattr(event, 'user_id'):
        # Add user context
        return event.with_metadata(user_id=event.user_id)
    return event

dispatcher = get_dispatcher()
dispatcher.add_middleware(logging_middleware)
dispatcher.add_middleware(user_context_middleware)
```

### Batch Processing

Process multiple events efficiently:

```python
events = [
    UserRegistered(user_id="user-1", email="user1@example.com"),
    UserRegistered(user_id="user-2", email="user2@example.com"),
    UserRegistered(user_id="user-3", email="user3@example.com"),
]

# Batch publish
await dispatcher.publish_batch(events)
```

### Event Filtering

Filter events by type, user, or custom criteria:

```python
# Filter by event type
user_events = store.load_events(event_types=[UserRegistered, NutritionGoalSet])

# Filter by time range
recent_meals = store.load_events(
    event_types=[MealLogged],
    start_time=datetime.now() - timedelta(days=7)
)

# Filter by aggregate
user_timeline = store.load_events(aggregate_id="user-123")
```

## Configuration

### Event Bus Configuration

```python
from packages.core.src.events import AsyncEventBus, DeadLetterQueue

# Configure dead letter queue
dlq = DeadLetterQueue(
    max_queue_size=1000,
    retention_days=30,
    max_retries=3
)

# Configure async event bus
bus = AsyncEventBus(dead_letter_queue=dlq)
bus.set_concurrent_limit(50)  # Max concurrent handlers
```

### Custom Storage Backend

Implement custom storage for production use:

```python
from packages.core.src.events import StorageBackend, EventStore

class DatabaseStorageBackend(StorageBackend):
    def save_event(self, event_data: Dict[str, Any]) -> None:
        # Save to database
        pass

    def load_events(self, **kwargs) -> List[Dict[str, Any]]:
        # Load from database
        pass

# Use custom backend
store = EventStore(DatabaseStorageBackend())
```

## Best Practices

### 1. Event Design

- Make events immutable and self-contained
- Include all necessary data in the event
- Use meaningful event names that describe business outcomes
- Version events when schema changes

### 2. Handler Design

- Keep handlers focused on single responsibilities
- Make handlers idempotent (safe to retry)
- Use async handlers for I/O operations
- Handle errors gracefully

### 3. Performance

- Use batch processing for multiple events
- Configure appropriate concurrency limits
- Implement event filtering to reduce processing
- Consider snapshots for aggregates with many events

### 4. Monitoring

- Monitor dead letter queue size and trends
- Track event processing times and failures
- Log important business events for audit trails
- Set up alerts for critical event failures

## Testing

The system includes comprehensive tests:

```bash
# Run event system tests
python -m pytest packages/core/tests/events/ -v

# Run specific test categories
python -m pytest packages/core/tests/events/test_events.py::TestEventBus -v
```

### Test Utilities

```python
from packages.core.src.events import reset_event_buses, reset_event_store

# Reset for clean test state
def setup_test():
    reset_event_buses()
    reset_event_store()
    reset_dead_letter_queue()
```

## Architecture Benefits

### Loose Coupling

- Components communicate through events, not direct calls
- Easy to add new features without modifying existing code
- Better separation of concerns

### Scalability

- Async processing supports high throughput
- Event sourcing enables horizontal scaling
- Failed events don't block the entire system

### Observability

- Complete audit trail of all business events
- Easy to trace user journeys and system interactions
- Rich analytics and reporting capabilities

### Reliability

- Dead letter queue prevents event loss
- Retry mechanisms handle transient failures
- Event sourcing provides data recovery capabilities

This event-driven architecture provides a solid foundation for building scalable, maintainable, and observable applications in the nutrition domain.
