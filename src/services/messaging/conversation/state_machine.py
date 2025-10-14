"""
Conversation State Machine

Implements finite state machine for managing conversation flows with
state transitions, context preservation, and event emission.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from packages.core.src.events import DomainEvent, EventBus

from .models import Conversation, Message, MessageType, QuickReply
from .repository import ConversationRepository

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """
    Conversation states representing the user's journey.

    State Flow:
    INITIAL → COLLECTING_PREFERENCES → MEAL_PLANNING → NUTRITION_TRACKING
                                      ↓
                                   FEEDBACK → COMPLETED
    """

    INITIAL = "initial"
    COLLECTING_PREFERENCES = "collecting_preferences"
    MEAL_PLANNING = "meal_planning"
    NUTRITION_TRACKING = "nutrition_tracking"
    FEEDBACK = "feedback"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ConversationTransition:
    """
    Defines a valid state transition with associated logic.

    Attributes:
        from_state: Source state
        to_state: Destination state
        trigger: Event that triggers this transition
        conditions: Optional conditions that must be met
        actions: Actions to execute during transition
    """

    from_state: ConversationState
    to_state: ConversationState
    trigger: str
    conditions: Optional[Dict[str, Any]] = None
    actions: List[str] = None

    def __post_init__(self):
        if self.actions is None:
            self.actions = []


@dataclass
class ConversationResponse:
    """
    Response from state machine after processing a message.

    Contains the response message, suggested quick replies,
    and updated conversation state.
    """

    message: str
    quick_replies: List[QuickReply]
    state: ConversationState
    context: Dict[str, Any]
    metadata: Dict[str, Any]


class ConversationStateMachine:
    """
    Channel-agnostic conversation state management.

    Manages conversation states, transitions, and context preservation
    across different messaging channels (WhatsApp, SMS, etc).
    """

    def __init__(self, repository: ConversationRepository, event_bus: Optional[EventBus] = None):
        """
        Initialize state machine.

        Args:
            repository: Conversation persistence layer
            event_bus: Event bus for publishing state changes
        """
        self.repository = repository
        self.event_bus = event_bus
        self.transitions = self._build_transitions()
        self.intent_handlers = self._register_intent_handlers()

    def _build_transitions(self) -> Dict[str, ConversationTransition]:
        """
        Build the transition map defining valid state changes.

        Returns:
            Dictionary mapping transition names to ConversationTransition objects
        """
        return {
            # Initial onboarding
            "start_onboarding": ConversationTransition(
                from_state=ConversationState.INITIAL,
                to_state=ConversationState.COLLECTING_PREFERENCES,
                trigger="start",
                actions=["send_welcome", "ask_dietary_preferences"],
            ),
            # Complete preferences collection
            "complete_preferences": ConversationTransition(
                from_state=ConversationState.COLLECTING_PREFERENCES,
                to_state=ConversationState.MEAL_PLANNING,
                trigger="preferences_complete",
                conditions={"all_required_fields": True},
                actions=["save_preferences", "generate_initial_plan"],
            ),
            # Additional preferences
            "add_preferences": ConversationTransition(
                from_state=ConversationState.COLLECTING_PREFERENCES,
                to_state=ConversationState.COLLECTING_PREFERENCES,
                trigger="add_preference",
                actions=["save_preference", "ask_next_preference"],
            ),
            # Start meal planning
            "begin_meal_planning": ConversationTransition(
                from_state=ConversationState.MEAL_PLANNING,
                to_state=ConversationState.MEAL_PLANNING,
                trigger="generate_plan",
                actions=["create_meal_plan", "show_plan_options"],
            ),
            # Move to tracking
            "start_tracking": ConversationTransition(
                from_state=ConversationState.MEAL_PLANNING,
                to_state=ConversationState.NUTRITION_TRACKING,
                trigger="accept_plan",
                actions=["save_meal_plan", "enable_tracking", "send_tracking_tips"],
            ),
            # Log nutrition
            "log_meal": ConversationTransition(
                from_state=ConversationState.NUTRITION_TRACKING,
                to_state=ConversationState.NUTRITION_TRACKING,
                trigger="log_nutrition",
                actions=["record_meal", "provide_feedback"],
            ),
            # Request feedback
            "request_feedback": ConversationTransition(
                from_state=ConversationState.NUTRITION_TRACKING,
                to_state=ConversationState.FEEDBACK,
                trigger="feedback_prompt",
                actions=["ask_satisfaction", "show_rating_options"],
            ),
            # Complete conversation
            "finish_conversation": ConversationTransition(
                from_state=ConversationState.FEEDBACK,
                to_state=ConversationState.COMPLETED,
                trigger="feedback_received",
                actions=["save_feedback", "send_thank_you"],
            ),
            # Error handling
            "handle_error": ConversationTransition(
                from_state=ConversationState.ERROR,
                to_state=ConversationState.INITIAL,
                trigger="reset",
                actions=["clear_context", "send_apology"],
            ),
        }

    def _register_intent_handlers(self) -> Dict[str, Callable]:
        """
        Register handlers for different user intents.

        Returns:
            Dictionary mapping intent names to handler functions
        """
        return {
            "greeting": self._handle_greeting,
            "dietary_preference": self._handle_dietary_preference,
            "meal_plan_request": self._handle_meal_plan_request,
            "nutrition_log": self._handle_nutrition_log,
            "feedback": self._handle_feedback,
            "help": self._handle_help,
            "unknown": self._handle_unknown,
        }

    async def process_message(
        self, user_id: str, channel: str, message: Message
    ) -> ConversationResponse:
        """
        Process an incoming message and advance conversation state.

        Args:
            user_id: Unique user identifier
            channel: Communication channel (whatsapp, sms, etc)
            message: User's message

        Returns:
            ConversationResponse with reply and updated state
        """
        try:
            # Load or create conversation
            conversation = await self.repository.get_or_create(user_id, channel)

            # Add message to history
            conversation.add_message("user", message.text, message.type.value)

            # Determine intent
            intent = await self._extract_intent(message, conversation)
            logger.info(
                f"Processing message for user {user_id} in state {conversation.state}, "
                f"detected intent: {intent}"
            )

            # Find valid transition
            transition = self._find_transition(ConversationState(conversation.state), intent)

            if not transition:
                logger.warning(
                    f"No valid transition found for state {conversation.state} "
                    f"with intent {intent}"
                )
                return await self._handle_invalid_transition(conversation, message)

            # Execute transition
            conversation = await self._execute_transition(conversation, transition, message)

            # Persist state
            await self.repository.save(conversation)

            # Emit event
            if self.event_bus:
                await self._emit_state_change_event(
                    user_id, channel, transition.from_state, transition.to_state
                )

            # Build response
            response = await self._build_response(conversation, transition)

            # Add response to history
            conversation.add_message("assistant", response.message, "text")
            await self.repository.save(conversation)

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return await self._handle_error(user_id, channel, e)

    async def _extract_intent(self, message: Message, conversation: Conversation) -> str:
        """
        Extract user intent from message.

        Uses keyword matching and context. In production, this could
        be enhanced with NLU/LLM-based intent classification.

        Args:
            message: User's message
            conversation: Current conversation state

        Returns:
            Intent name
        """
        text = message.text.lower()

        # Greeting patterns
        if any(word in text for word in ["hi", "hello", "hey", "start"]):
            return "greeting"

        # Dietary preferences
        if any(word in text for word in ["vegan", "vegetarian", "gluten", "dairy", "allergy"]):
            return "dietary_preference"

        # Meal planning
        if any(word in text for word in ["meal plan", "recipes", "cook", "eat"]):
            return "meal_plan_request"

        # Nutrition logging
        if any(word in text for word in ["ate", "had", "consumed", "calories", "log"]):
            return "nutrition_log"

        # Feedback
        if any(word in text for word in ["rate", "feedback", "review", "satisfied"]):
            return "feedback"

        # Help request
        if any(word in text for word in ["help", "support", "how"]):
            return "help"

        return "unknown"

    def _find_transition(
        self, current_state: ConversationState, intent: str
    ) -> Optional[ConversationTransition]:
        """
        Find a valid transition for current state and intent.

        Args:
            current_state: Current conversation state
            intent: Detected user intent

        Returns:
            ConversationTransition if found, None otherwise
        """
        # Map intents to triggers
        intent_to_trigger = {
            "greeting": "start",
            "dietary_preference": "add_preference",
            "meal_plan_request": "generate_plan",
            "nutrition_log": "log_nutrition",
            "feedback": "feedback_received",
        }

        trigger = intent_to_trigger.get(intent)
        if not trigger:
            return None

        # Find matching transition
        for transition in self.transitions.values():
            if transition.from_state == current_state and transition.trigger == trigger:
                return transition

        return None

    async def _execute_transition(
        self, conversation: Conversation, transition: ConversationTransition, message: Message
    ) -> Conversation:
        """
        Execute state transition and associated actions.

        Args:
            conversation: Current conversation
            transition: Transition to execute
            message: Triggering message

        Returns:
            Updated conversation
        """
        logger.info(f"Executing transition from {transition.from_state} to {transition.to_state}")

        # Update state
        conversation.state = transition.to_state.value
        conversation.updated_at = datetime.utcnow()

        # Execute actions
        for action in transition.actions:
            await self._execute_action(action, conversation, message)

        return conversation

    async def _execute_action(
        self, action: str, conversation: Conversation, message: Message
    ) -> None:
        """
        Execute a specific action.

        Args:
            action: Action name
            conversation: Current conversation
            message: Triggering message
        """
        action_handlers = {
            "send_welcome": self._action_send_welcome,
            "ask_dietary_preferences": self._action_ask_preferences,
            "save_preference": self._action_save_preference,
            "generate_initial_plan": self._action_generate_plan,
            "record_meal": self._action_record_meal,
            "provide_feedback": self._action_provide_feedback,
        }

        handler = action_handlers.get(action)
        if handler:
            await handler(conversation, message)
        else:
            logger.warning(f"No handler found for action: {action}")

    # Action handlers
    async def _action_send_welcome(self, conversation: Conversation, message: Message) -> None:
        """Send welcome message."""
        conversation.update_context(welcomed=True)

    async def _action_ask_preferences(self, conversation: Conversation, message: Message) -> None:
        """Ask for dietary preferences."""
        conversation.update_context(asking_preferences=True)

    async def _action_save_preference(self, conversation: Conversation, message: Message) -> None:
        """Save dietary preference."""
        preferences = conversation.context.get("preferences", [])
        preferences.append(message.text)
        conversation.update_context(preferences=preferences)

    async def _action_generate_plan(self, conversation: Conversation, message: Message) -> None:
        """Generate meal plan."""
        conversation.update_context(plan_generated=True)

    async def _action_record_meal(self, conversation: Conversation, message: Message) -> None:
        """Record meal log."""
        logs = conversation.context.get("meal_logs", [])
        logs.append({"text": message.text, "timestamp": datetime.utcnow().isoformat()})
        conversation.update_context(meal_logs=logs)

    async def _action_provide_feedback(self, conversation: Conversation, message: Message) -> None:
        """Provide feedback on logged meal."""
        conversation.update_context(feedback_provided=True)

    # Intent handlers
    async def _handle_greeting(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle greeting intent."""
        return ConversationResponse(
            message="Hello! 👋 I'm your AI nutritionist. Let's start by understanding your dietary preferences.",
            quick_replies=[
                QuickReply(text="🥗 I'm vegetarian", payload="vegetarian"),
                QuickReply(text="🥑 I'm vegan", payload="vegan"),
                QuickReply(text="🍖 No restrictions", payload="none"),
            ],
            state=ConversationState.COLLECTING_PREFERENCES,
            context=conversation.context,
            metadata={},
        )

    async def _handle_dietary_preference(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle dietary preference intent."""
        return ConversationResponse(
            message="Got it! Any allergies or foods you want to avoid?",
            quick_replies=[
                QuickReply(text="No allergies", payload="no_allergies"),
                QuickReply(text="Continue", payload="continue"),
            ],
            state=ConversationState.COLLECTING_PREFERENCES,
            context=conversation.context,
            metadata={},
        )

    async def _handle_meal_plan_request(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle meal plan request intent."""
        return ConversationResponse(
            message="I'll create a personalized meal plan for you! 📋",
            quick_replies=[
                QuickReply(text="7-day plan", payload="7day"),
                QuickReply(text="3-day plan", payload="3day"),
            ],
            state=ConversationState.MEAL_PLANNING,
            context=conversation.context,
            metadata={},
        )

    async def _handle_nutrition_log(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle nutrition logging intent."""
        return ConversationResponse(
            message="Meal logged! 📝 Great job tracking your nutrition.",
            quick_replies=[
                QuickReply(text="Log another", payload="log_more"),
                QuickReply(text="View summary", payload="summary"),
            ],
            state=ConversationState.NUTRITION_TRACKING,
            context=conversation.context,
            metadata={},
        )

    async def _handle_feedback(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle feedback intent."""
        return ConversationResponse(
            message="Thank you for your feedback! 🙏",
            quick_replies=[],
            state=ConversationState.COMPLETED,
            context=conversation.context,
            metadata={},
        )

    async def _handle_help(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle help request."""
        return ConversationResponse(
            message="I can help you with:\n• Meal planning\n• Nutrition tracking\n• Dietary advice",
            quick_replies=[
                QuickReply(text="Meal plan", payload="meal_plan"),
                QuickReply(text="Track meal", payload="track"),
            ],
            state=ConversationState(conversation.state),
            context=conversation.context,
            metadata={},
        )

    async def _handle_unknown(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle unknown intent."""
        return ConversationResponse(
            message="I'm not sure I understand. Can you rephrase that?",
            quick_replies=[
                QuickReply(text="Help", payload="help"),
                QuickReply(text="Start over", payload="reset"),
            ],
            state=ConversationState(conversation.state),
            context=conversation.context,
            metadata={},
        )

    async def _handle_invalid_transition(
        self, conversation: Conversation, message: Message
    ) -> ConversationResponse:
        """Handle invalid state transition."""
        logger.warning(
            f"Invalid transition for state {conversation.state} " f"with message: {message.text}"
        )

        return ConversationResponse(
            message="I'm having trouble understanding that in this context. Let me help you:",
            quick_replies=[
                QuickReply(text="Start over", payload="reset"),
                QuickReply(text="Get help", payload="help"),
            ],
            state=ConversationState(conversation.state),
            context=conversation.context,
            metadata={"error": "invalid_transition"},
        )

    async def _build_response(
        self, conversation: Conversation, transition: ConversationTransition
    ) -> ConversationResponse:
        """Build response based on new state."""
        state = ConversationState(conversation.state)

        # State-specific responses
        if state == ConversationState.COLLECTING_PREFERENCES:
            return ConversationResponse(
                message="Let me know your dietary preferences!",
                quick_replies=[
                    QuickReply(text="Vegetarian", payload="vegetarian"),
                    QuickReply(text="Vegan", payload="vegan"),
                ],
                state=state,
                context=conversation.context,
                metadata={},
            )
        elif state == ConversationState.MEAL_PLANNING:
            return ConversationResponse(
                message="Let's create your meal plan!",
                quick_replies=[
                    QuickReply(text="Generate plan", payload="generate"),
                ],
                state=state,
                context=conversation.context,
                metadata={},
            )
        else:
            return ConversationResponse(
                message="How can I help you today?",
                quick_replies=[],
                state=state,
                context=conversation.context,
                metadata={},
            )

    async def _emit_state_change_event(
        self, user_id: str, channel: str, old_state: ConversationState, new_state: ConversationState
    ) -> None:
        """Emit state change event to event bus."""
        if not self.event_bus:
            return

        event = DomainEvent(
            event_type="conversation.state_changed",
            aggregate_id=f"{user_id}#{channel}",
            data={
                "user_id": user_id,
                "channel": channel,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        await self.event_bus.publish(event)

    async def _handle_error(
        self, user_id: str, channel: str, error: Exception
    ) -> ConversationResponse:
        """Handle processing error."""
        logger.error(f"Error in conversation processing: {error}", exc_info=True)

        return ConversationResponse(
            message="I encountered an error. Let's start fresh!",
            quick_replies=[
                QuickReply(text="Restart", payload="reset"),
            ],
            state=ConversationState.ERROR,
            context={},
            metadata={"error": str(error)},
        )
