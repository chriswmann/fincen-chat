"""Handles chat CRUD"""

import json
import uuid
from enum import StrEnum, auto
from typing import Any

import asyncpg
from pydantic import BaseModel, Field, SecretStr, UUID4
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_schema: str = "fincen"
    postgres_port: int = 5432

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}"
            f":{self.postgres_password.get_secret_value()}"
            f"@localhost:{self.postgres_port}/{self.postgres_db}"
        )


class Role(StrEnum):
    USER = auto()
    ASSISTANT = auto()
    TOOL_CALL = auto()
    TOOL_RETURN = auto()


class Message(BaseModel):
    id: UUID4 = Field(
        default_factory=uuid.uuid4, description="Unique identifier for the message"
    )
    content: str = Field(description="The text content of the message")
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
    position: int = Field(description="Current position index within the chat")

    @property
    def num_messages(self) -> int:
        return len(self.messages)


async def create_chat(conn: asyncpg.Connection) -> UUID4:
    """Insert a new chat into the DB and return the ID"""
    row: UUID4 = await conn.fetchval(
        query="insert into chats default values returning id"
    )

    return row


async def get_chat(chat_id: UUID4, conn: asyncpg.Connection) -> Chat:
    """Fetch a chat and all of its messages, ordered by position"""
    rows = await conn.fetch(
        "select id, messages, position from messages where id = $1", chat_id
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
    chat_id: UUID4, messages: list[Message], conn: asyncpg.Connection
) -> None:
    """Save a batch of messages to an existing chat"""
    await conn.executemany(
        """insert into messages (chat_id, role, content, tool_name, tool_call_id, tool_args, position)
        values ($1, $2, $3, $4, $5, $6::jsonb, $7)
        """,
        [
            (
                chat_id,
                msg.role.value,
                msg.content,
                msg.tool_name,
                msg.tool_call_id,
                json.dumps(msg.tool_args) if msg.tool_args else None,
                idx,
            )
            for idx, msg in enumerate(messages)
        ],
    )


async def get_messages(chat_id: UUID4, conn: asyncpg.Connection) -> list[Message]:
    """Load the messages for a chat, ordered by position"""
    chat = await get_chat(chat_id, conn)
    return chat.messages
