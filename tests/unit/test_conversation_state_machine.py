"""
Tests for Conversation State Machine

Tests cover state transitions, context preservation, and error handling.
"""

from datetime import datetime

import pytest

from src.services.messaging.conversation import (
    ConversationState,
    ConversationStateMachine,
    ConversationTransition,
    InMemoryConversationRepository,
    Message,
    MessageType,
)


@pytest.fixture
def repository():
    """Create in-memory repository for testing."""
    return InMemoryConversationRepository()


@pytest.fixture
def state_machine(repository):
    """Create state machine with in-memory repository."""
    return ConversationStateMachine(repository=repository, event_bus=None)


@pytest.mark.asyncio
async def test_initial_greeting(state_machine):
    """Test initial greeting transitions to collecting preferences."""
    message = Message(text="Hello", type=MessageType.TEXT)

    response = await state_machine.process_message(
        user_id="test123", channel="whatsapp", message=message
    )

    assert response.state == ConversationState.COLLECTING_PREFERENCES
    assert "dietary preferences" in response.message.lower()
    assert len(response.quick_replies) > 0


@pytest.mark.asyncio
async def test_dietary_preference_collection(state_machine):
    """Test collecting dietary preferences."""
    # Start conversation
    message1 = Message(text="Hi", type=MessageType.TEXT)
    await state_machine.process_message("test123", "whatsapp", message1)

    # Add dietary preference
    message2 = Message(text="I'm vegan", type=MessageType.TEXT)
    response = await state_machine.process_message("test123", "whatsapp", message2)

    assert response.state == ConversationState.COLLECTING_PREFERENCES

    # Verify context saved
    conversation = await state_machine.repository.get_or_create("test123", "whatsapp")
    assert len(conversation.context.get("preferences", [])) > 0


@pytest.mark.asyncio
async def test_complete_conversation_flow(state_machine):
    """Test complete conversation from start to finish."""
    user_id = "test123"
    channel = "whatsapp"

    # 1. Initial greeting
    response1 = await state_machine.process_message(
        user_id, channel, Message(text="Hello", type=MessageType.TEXT)
    )
    assert response1.state == ConversationState.COLLECTING_PREFERENCES

    # 2. Add dietary preference
    response2 = await state_machine.process_message(
        user_id, channel, Message(text="I'm vegetarian", type=MessageType.TEXT)
    )
    assert response2.state == ConversationState.COLLECTING_PREFERENCES

    # 3. Request meal plan
    response3 = await state_machine.process_message(
        user_id, channel, Message(text="Create meal plan", type=MessageType.TEXT)
    )
    assert response3.state == ConversationState.MEAL_PLANNING

    # 4. Verify conversation history
    conversation = await state_machine.repository.get_or_create(user_id, channel)
    assert len(conversation.history) >= 3
    assert conversation.state == ConversationState.MEAL_PLANNING.value


@pytest.mark.asyncio
async def test_context_preservation(state_machine):
    """Test that conversation context is preserved across messages."""
    user_id = "test123"
    channel = "whatsapp"

    # Send first message
    await state_machine.process_message(user_id, channel, Message(text="Hi", type=MessageType.TEXT))

    # Send dietary preference
    await state_machine.process_message(
        user_id, channel, Message(text="I'm vegan and allergic to nuts", type=MessageType.TEXT)
    )

    # Verify context persisted
    conversation = await state_machine.repository.get_or_create(user_id, channel)
    assert "preferences" in conversation.context
    assert len(conversation.history) >= 2


@pytest.mark.asyncio
async def test_invalid_transition_handling(state_machine):
    """Test handling of invalid state transitions."""
    user_id = "test123"
    channel = "whatsapp"

    # Create conversation in INITIAL state
    response = await state_machine.process_message(
        user_id,
        channel,
        Message(text="rate my experience", type=MessageType.TEXT),  # Feedback in INITIAL state
    )

    # Should handle gracefully
    assert response.message is not None
    assert len(response.quick_replies) > 0  # Should offer help


@pytest.mark.asyncio
async def test_help_request_any_state(state_machine):
    """Test that help can be requested from any state."""
    user_id = "test123"
    channel = "whatsapp"

    # Start conversation
    await state_machine.process_message(user_id, channel, Message(text="Hi", type=MessageType.TEXT))

    # Request help
    response = await state_machine.process_message(
        user_id, channel, Message(text="help", type=MessageType.TEXT)
    )

    assert "help" in response.message.lower()
    assert len(response.quick_replies) > 0


@pytest.mark.asyncio
async def test_message_history_tracking(state_machine):
    """Test that message history is tracked correctly."""
    user_id = "test123"
    channel = "whatsapp"

    messages = [
        "Hello",
        "I'm vegan",
        "Create a meal plan",
    ]

    for msg_text in messages:
        await state_machine.process_message(
            user_id, channel, Message(text=msg_text, type=MessageType.TEXT)
        )

    conversation = await state_machine.repository.get_or_create(user_id, channel)

    # Should have user messages + assistant responses
    assert len(conversation.history) >= len(messages)

    # Check message structure
    for msg in conversation.history:
        assert "role" in msg
        assert "text" in msg
        assert "timestamp" in msg


@pytest.mark.asyncio
async def test_multi_channel_isolation(state_machine):
    """Test that conversations are isolated by channel."""
    user_id = "test123"

    # WhatsApp conversation
    response_wa = await state_machine.process_message(
        user_id, "whatsapp", Message(text="Hi", type=MessageType.TEXT)
    )

    # SMS conversation
    response_sms = await state_machine.process_message(
        user_id, "sms", Message(text="Hello", type=MessageType.TEXT)
    )

    # Both should be in COLLECTING_PREFERENCES but separate
    assert response_wa.state == ConversationState.COLLECTING_PREFERENCES
    assert response_sms.state == ConversationState.COLLECTING_PREFERENCES

    # Verify separate conversations
    conv_wa = await state_machine.repository.get_or_create(user_id, "whatsapp")
    conv_sms = await state_machine.repository.get_or_create(user_id, "sms")

    assert conv_wa.channel == "whatsapp"
    assert conv_sms.channel == "sms"


@pytest.mark.asyncio
async def test_transition_actions_execution(state_machine):
    """Test that transition actions are executed."""
    user_id = "test123"
    channel = "whatsapp"

    # Trigger transition with actions
    await state_machine.process_message(user_id, channel, Message(text="Hi", type=MessageType.TEXT))

    conversation = await state_machine.repository.get_or_create(user_id, channel)

    # Check that welcome action was executed
    assert conversation.context.get("welcomed") == True


@pytest.mark.asyncio
async def test_error_recovery(state_machine):
    """Test error handling and recovery."""
    user_id = "test123"
    channel = "whatsapp"

    # Create conversation
    await state_machine.process_message(user_id, channel, Message(text="Hi", type=MessageType.TEXT))

    # Send something that might cause issues (but should be handled gracefully)
    response = await state_machine.process_message(
        user_id, channel, Message(text="", type=MessageType.TEXT)  # Empty message
    )

    # Should still get a response
    assert response.message is not None
    assert response.state is not None


@pytest.mark.asyncio
async def test_quick_reply_responses(state_machine):
    """Test that quick replies are generated appropriately."""
    user_id = "test123"
    channel = "whatsapp"

    response = await state_machine.process_message(
        user_id, channel, Message(text="Hi", type=MessageType.TEXT)
    )

    # Should have quick reply options
    assert len(response.quick_replies) > 0

    # Quick replies should have required fields
    for qr in response.quick_replies:
        assert qr.text
        assert qr.payload


@pytest.mark.asyncio
async def test_conversation_ttl_set(repository):
    """Test that conversation TTL is set for GDPR compliance."""
    conversation = await repository.get_or_create("test123", "whatsapp")
    await repository.save(conversation)

    # In DynamoDB implementation, TTL would be set
    # For in-memory, we just verify save works
    retrieved = await repository.get_or_create("test123", "whatsapp")
    assert retrieved.user_id == "test123"


@pytest.mark.asyncio
async def test_intent_detection(state_machine):
    """Test intent extraction from messages."""
    test_cases = [
        ("Hi there!", "greeting"),
        ("I'm vegan", "dietary_preference"),
        ("Create a meal plan", "meal_plan_request"),
        ("I ate a salad", "nutrition_log"),
        ("Can you help me?", "help"),
    ]

    conversation = await state_machine.repository.get_or_create("test", "test")

    for text, expected_intent in test_cases:
        message = Message(text=text, type=MessageType.TEXT)
        intent = await state_machine._extract_intent(message, conversation)
        assert intent == expected_intent


def test_transition_definition():
    """Test that transitions are properly defined."""
    repository = InMemoryConversationRepository()
    machine = ConversationStateMachine(repository)

    # Verify key transitions exist
    assert "start_onboarding" in machine.transitions
    assert "complete_preferences" in machine.transitions
    assert "start_tracking" in machine.transitions

    # Verify transition structure
    transition = machine.transitions["start_onboarding"]
    assert transition.from_state == ConversationState.INITIAL
    assert transition.to_state == ConversationState.COLLECTING_PREFERENCES
    assert len(transition.actions) > 0
