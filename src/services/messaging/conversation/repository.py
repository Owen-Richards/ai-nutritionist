"""
Conversation Repository

Persistence layer for conversation state management using DynamoDB.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol

import boto3
from botocore.exceptions import ClientError

from .models import Conversation, ConversationState

logger = logging.getLogger(__name__)


class ConversationRepository(Protocol):
    """
    Repository protocol for conversation persistence.

    Defines the contract for conversation storage implementations.
    """

    async def get_or_create(self, user_id: str, channel: str) -> Conversation:
        """
        Get existing conversation or create new one.

        Args:
            user_id: User identifier
            channel: Communication channel

        Returns:
            Conversation object
        """
        ...

    async def save(self, conversation: Conversation) -> None:
        """
        Save conversation state.

        Args:
            conversation: Conversation to save
        """
        ...

    async def delete(self, user_id: str, channel: str) -> None:
        """
        Delete conversation (GDPR compliance).

        Args:
            user_id: User identifier
            channel: Communication channel
        """
        ...


class DynamoDBConversationRepository:
    """
    DynamoDB-backed conversation state persistence.

    Table Schema:
        PK: user_id#channel
        SK: conversation
        Attributes: state, context, history, timestamps
    """

    def __init__(self, table_name: str = "ai-nutritionist-conversations-dev"):
        """
        Initialize repository.

        Args:
            table_name: DynamoDB table name
        """
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    async def get_or_create(self, user_id: str, channel: str) -> Conversation:
        """
        Get existing conversation or create new one.

        Args:
            user_id: User identifier
            channel: Communication channel

        Returns:
            Conversation object
        """
        key = f"{user_id}#{channel}"

        try:
            response = self.table.get_item(Key={"pk": key, "sk": "conversation"})

            if "Item" in response:
                item = response["Item"]
                return Conversation.from_dict(
                    {
                        "user_id": user_id,
                        "channel": channel,
                        "state": item.get("state", ConversationState.INITIAL.value),
                        "context": item.get("context", {}),
                        "history": item.get("history", []),
                        "created_at": item.get("created_at", datetime.utcnow().isoformat()),
                        "updated_at": item.get("updated_at", datetime.utcnow().isoformat()),
                        "metadata": item.get("metadata", {}),
                    }
                )

        except ClientError as e:
            logger.error(f"Error loading conversation: {e}")

        # Create new conversation
        return Conversation(
            user_id=user_id,
            channel=channel,
            state=ConversationState.INITIAL.value,
            context={},
            history=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata={},
        )

    async def save(self, conversation: Conversation) -> None:
        """
        Save conversation state.

        Args:
            conversation: Conversation to save
        """
        key = f"{conversation.user_id}#{conversation.channel}"

        try:
            item = {
                "pk": key,
                "sk": "conversation",
                "user_id": conversation.user_id,
                "channel": conversation.channel,
                "state": conversation.state,
                "context": conversation.context,
                "history": conversation.history[-20:],  # Keep last 20 messages
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "metadata": conversation.metadata,
                "ttl": int((datetime.utcnow().timestamp() + (30 * 24 * 60 * 60))),  # 30 days TTL
            }

            self.table.put_item(Item=item)
            logger.info(f"Saved conversation for {key} in state {conversation.state}")

        except ClientError as e:
            logger.error(f"Error saving conversation: {e}")
            raise

    async def delete(self, user_id: str, channel: str) -> None:
        """
        Delete conversation (GDPR compliance).

        Args:
            user_id: User identifier
            channel: Communication channel
        """
        key = f"{user_id}#{channel}"

        try:
            self.table.delete_item(Key={"pk": key, "sk": "conversation"})
            logger.info(f"Deleted conversation for {key}")

        except ClientError as e:
            logger.error(f"Error deleting conversation: {e}")
            raise

    async def get_by_state(self, state: ConversationState, limit: int = 100):
        """
        Get conversations by state (for monitoring).

        Args:
            state: Conversation state to filter by
            limit: Maximum number of results

        Returns:
            List of conversations
        """
        try:
            response = self.table.scan(
                FilterExpression="#state = :state",
                ExpressionAttributeNames={"#state": "state"},
                ExpressionAttributeValues={":state": state.value},
                Limit=limit,
            )

            conversations = []
            for item in response.get("Items", []):
                conv = Conversation.from_dict(
                    {
                        "user_id": item["user_id"],
                        "channel": item["channel"],
                        "state": item["state"],
                        "context": item.get("context", {}),
                        "history": item.get("history", []),
                        "created_at": item["created_at"],
                        "updated_at": item["updated_at"],
                        "metadata": item.get("metadata", {}),
                    }
                )
                conversations.append(conv)

            return conversations

        except ClientError as e:
            logger.error(f"Error querying by state: {e}")
            return []


class InMemoryConversationRepository:
    """
    In-memory conversation repository for testing.
    """

    def __init__(self):
        self.conversations = {}

    async def get_or_create(self, user_id: str, channel: str) -> Conversation:
        """Get or create conversation."""
        key = f"{user_id}#{channel}"

        if key not in self.conversations:
            self.conversations[key] = Conversation(
                user_id=user_id,
                channel=channel,
                state=ConversationState.INITIAL.value,
                context={},
                history=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={},
            )

        return self.conversations[key]

    async def save(self, conversation: Conversation) -> None:
        """Save conversation."""
        key = f"{conversation.user_id}#{conversation.channel}"
        self.conversations[key] = conversation

    async def delete(self, user_id: str, channel: str) -> None:
        """Delete conversation."""
        key = f"{user_id}#{channel}"
        if key in self.conversations:
            del self.conversations[key]
