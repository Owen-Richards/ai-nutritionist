"""
Conversation State Management Package

AI_CONTEXT
Purpose: Stateful conversation management with context preservation across channels
Public API: ConversationStateMachine, ConversationState, ConversationRepository
Internal: State transitions, quick replies, context persistence
Contracts: Async state operations, DynamoDB persistence, event emission
Side Effects: DynamoDB writes, event bus publications
Stability: public - New core conversation management system
Usage Example:
    from src.services.messaging.conversation import ConversationStateMachine

    state_machine = ConversationStateMachine(repository, event_bus)
    response = await state_machine.process_message(
        user_id="user123",
        channel="whatsapp",
        message=Message(text="I want to eat healthier", type="text")
    )
"""

from .models import Conversation, Message, QuickReply
from .repository import ConversationRepository, DynamoDBConversationRepository
from .state_machine import (
    ConversationResponse,
    ConversationState,
    ConversationStateMachine,
    ConversationTransition,
)

__all__ = [
    "ConversationState",
    "ConversationStateMachine",
    "ConversationTransition",
    "ConversationResponse",
    "ConversationRepository",
    "DynamoDBConversationRepository",
    "Conversation",
    "Message",
    "QuickReply",
]
