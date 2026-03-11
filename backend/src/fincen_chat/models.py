import uuid
from typing import Any, Literal
from enum import StrEnum, auto

from pydantic import BaseModel, Field, UUID4

# Structured output models


class FinCENEntity(BaseModel):
    """A named entity from the FinCEN dataset."""

    name: str
    entity_type: str | None = Field(
        default=None,
        description="E.g. 'Bank', 'Individual', 'Shell Company'",
    )
    country: str | None = None


class FinCENResponse(BaseModel):
    """Successful response grounded in FinCEN graph data."""

    answer: str = Field(
        description="A clear, human-readable answer to the user's question."
    )
    entities_mentioned: list[FinCENEntity] = Field(
        default_factory=list,
        description="FinCEN entities referenced in the answer.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "How confident the model is in ths answer, baserd on the data found."
            "Use 'low' if the graph data was sparse or ambiguous."
        ),
    )
    # `data_found` is a self-reporting integrity check
    data_found: bool = Field(
        description="True if the Neo4j graph returned relevant data for this query",
    )


class ErrorResponse(BaseModel):
    """Used when the question cannot be answered from FinCEN data."""

    reason: str = Field(
        description="A brief explanation of why the question cannot be answered."
    )


AgentOutput = FinCENResponse | ErrorResponse

# Chat models


class Role(StrEnum):
    ASSISTANT = auto()
    RETRY = auto()
    SYSTEM = auto()
    TOOL_CALL = auto()
    TOOL_RETURN = auto()
    USER = auto()


class Message(BaseModel):
    id: UUID4 = Field(
        default_factory=uuid.uuid4, description="Unique identifier for the message"
    )
    content: str = Field(
        description=(
            "The text content of the message."
            "Empty string default since tool calls don't have any content."
        ),
        default="",
    )
    role: Role = Field(description="The role of the message sender")
    tool_name: str | None = Field(
        default=None, description="Name of the tool invoked, if any"
    )
    tool_call_id: str | None = Field(
        default=None, description="Identifier of the tool invoked, if any"
    )
    tool_args: dict[str, Any] | None = Field(
        default=None, description="Arguments passed to the tool, if any"
    )


class Chat(BaseModel):
    id: UUID4 = Field(description="Unique identifier for the chat session")
    messages: list[Message] = Field(
        default_factory=list, description="Ordered list of messages in the chat"
    )
    position: int | None = Field(
        description="Current position index within the chat", default=None
    )

    @property
    def num_messages(self) -> int:
        return len(self.messages)


class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID4 | None = None
