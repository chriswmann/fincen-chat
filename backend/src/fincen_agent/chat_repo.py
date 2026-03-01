"""Handles chat CRUD"""

import json
from functools import singledispatch

import asyncpg
from pydantic import UUID4
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelRequestPart,
    ModelResponse,
    ModelResponsePart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from .models import Chat, Message, Role


async def create_chat(conn: asyncpg.Connection) -> UUID4:
    """Insert a new chat into the DB and return the ID"""
    row = await conn.fetchval(query="insert into chats default values returning id;")

    if row is None:
        raise ValueError("Could not create chat")

    return row


async def get_chat(chat_id: UUID4, conn: asyncpg.Connection) -> Chat:
    """Fetch a chat and all of its messages, ordered by position"""
    rows = await conn.fetch(
        """select
                 id, role, content, tool_name, tool_call_id, tool_args, position
                 from messages
                 where chat_id = $1
                 order by position;
        """,
        chat_id,
    )

    messages = [
        Message(
            id=r["id"],
            role=Role(r["role"]),
            content=r["content"],
            tool_name=r["tool_name"],
            tool_call_id=r["tool_call_id"],
            tool_args=json.loads(r["tool_args"]) if r["tool_args"] else None,
        )
        for r in rows
    ]

    position = rows[-1]["position"] if rows else 0

    chat = Chat(
        id=chat_id,
        messages=messages,
        position=position,
    )

    return chat


async def save_messages(
    chat_id: UUID4,
    messages: list[Message],
    start_position: int,
    conn: asyncpg.Connection,
) -> None:
    """Save a batch of messages to an existing chat"""
    await conn.executemany(
        """insert into messages (chat_id, role, content, tool_name, tool_call_id, tool_args, position)
        values ($1, $2, $3, $4, $5, $6::jsonb, $7);
        """,
        [
            (
                chat_id,
                msg.role.value,
                msg.content,
                msg.tool_name,
                msg.tool_call_id,
                json.dumps(msg.tool_args) if msg.tool_args else None,
                start_position + idx,
            )
            for idx, msg in enumerate(messages)
        ],
    )


async def get_messages(chat_id: UUID4, conn: asyncpg.Connection) -> list[Message]:
    """Load the messages for a chat, ordered by position"""
    chat = await get_chat(chat_id, conn)
    return chat.messages


class MessageGrouper:
    def __init__(self) -> None:

        self._result: list[ModelMessage] = []
        self._request_parts: list[ModelRequestPart] = []
        self._response_parts: list[ModelResponsePart] = []

    def _flush_request(self) -> None:
        if self._request_parts:
            self._result.append(ModelRequest(parts=self._request_parts))
            self._request_parts = []

    def _flush_response(self) -> None:
        if self._response_parts:
            self._result.append(ModelResponse(parts=self._response_parts))
            self._response_parts = []

    def add(self, msg: Message) -> None:
        match msg.role:
            case Role.ASSISTANT:
                self._flush_request()
                self._response_parts.append(TextPart(content=msg.content))
            case Role.USER:
                self._flush_response()
                self._request_parts.append(UserPromptPart(content=msg.content))
            case Role.TOOL_CALL:
                errors = []
                if not msg.tool_name:
                    errors.append("Tool call missing tool name")
                if not msg.tool_call_id:
                    errors.append("Tool call missing tool call ID")
                if errors:
                    raise ValueError("\n".join(errors))
                self._flush_request()
                self._response_parts.append(
                    ToolCallPart(
                        tool_name=str(msg.tool_name),
                        tool_call_id=str(msg.tool_call_id),
                        args=msg.tool_args or {},
                    )
                )
            case Role.TOOL_RETURN:
                errors = []
                if not msg.tool_name:
                    errors.append("Tool return missing tool name")
                if not msg.tool_call_id:
                    errors.append("Tool return missing tool call ID")
                if errors:
                    raise ValueError("\n".join(errors))
                self._flush_response()
                self._request_parts.append(
                    ToolReturnPart(
                        tool_name=str(msg.tool_name),
                        tool_call_id=str(msg.tool_call_id),
                        content=msg.content,
                    )
                )

    def build(self) -> list[ModelMessage]:
        self._flush_request()
        self._flush_response()

        return self._result


def to_pydantic_ai_messages(
    messages: list[Message],
    grouper: MessageGrouper,
) -> list[ModelMessage]:
    """Convert flat DB rows to PydanticAI's grouped message format.

    PydanticAI groups messages into a `ModelRequest` (user/tool-return) and
    `ModelResponse` (assistant/tool-call). We reconstruct this by iterating through
    our flat rows and building up the request/response structure as the role changes."""
    for message in messages:
        grouper.add(message)

    return grouper.build()


@singledispatch
def _part_to_message(part: ModelRequestPart | ModelResponsePart) -> Message:
    raise ValueError(f"Unexpected part type: {type(part).__name__}")


@_part_to_message.register
def _(part: TextPart) -> Message:
    return Message(
        content=part.content,
        role=Role.ASSISTANT,
    )


@_part_to_message.register
def _(part: ToolCallPart) -> Message:
    return Message(
        tool_name=part.tool_name,
        tool_call_id=part.tool_call_id,
        tool_args=part.args if isinstance(part.args, dict) else {},
        content="",
        role=Role.TOOL_CALL,
    )


@_part_to_message.register
def _(part: ToolReturnPart) -> Message:
    return Message(
        tool_name=part.tool_name,
        tool_call_id=part.tool_call_id,
        content=str(part.content),
        role=Role.TOOL_RETURN,
    )


@_part_to_message.register
def _(part: UserPromptPart) -> Message:
    return Message(content=str(part.content), role=Role.USER)


def from_pydantic_ai_messages(
    history: list[ModelMessage],
) -> list[Message]:
    """Convert from PydanticAI's grouped message format to flat DB rows.

    This is the inverse of `to_pydantic_ai_messages`. We iterate over
    each message's parts and create one `Message` row per part.
    """

    return [_part_to_message(part) for model_msg in history for part in model_msg.parts]
