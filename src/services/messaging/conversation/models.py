"""
Conversation Domain Models

Defines core data structures for conversation state management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages in a conversation."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    QUICK_REPLY = "quick_reply"
    LOCATION = "location"


class QuickReplyType(str, Enum):
    """Types of quick reply buttons."""

    TEXT = "text"
    POSTBACK = "postback"
    URL = "url"


@dataclass
class Message:
    """Represents a user or system message."""

    text: str
    type: MessageType = MessageType.TEXT
    media_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QuickReply:
    """Represents a quick reply button for user convenience."""

    text: str
    payload: str
    type: QuickReplyType = QuickReplyType.TEXT
    image_url: Optional[str] = None


class Conversation(BaseModel):
    """
    Represents a conversation with persistent state.

    This is the core domain model for conversation management, tracking
    the current state, context, and history of user interactions.
    """

    user_id: str = Field(..., description="Unique user identifier")
    channel: str = Field(..., description="Communication channel (whatsapp, sms, etc)")
    state: str = Field(..., description="Current conversation state")
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context data")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Message history")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage."""
        return {
            "user_id": self.user_id,
            "channel": self.channel,
            "state": self.state,
            "context": self.context,
            "history": self.history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create from dictionary (DynamoDB item)."""
        return cls(
            user_id=data["user_id"],
            channel=data["channel"],
            state=data["state"],
            context=data.get("context", {}),
            history=data.get("history", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )

    def add_message(self, role: str, text: str, message_type: str = "text") -> None:
        """Add a message to conversation history."""
        self.history.append(
            {
                "role": role,
                "text": text,
                "type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self.updated_at = datetime.utcnow()

    def update_context(self, **kwargs) -> None:
        """Update conversation context."""
        self.context.update(kwargs)
        self.updated_at = datetime.utcnow()

    def get_recent_history(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent message history."""
        return self.history[-count:] if self.history else []
