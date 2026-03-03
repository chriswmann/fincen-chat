import json
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator
import asyncpg
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import UUID4
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from fincen_agent.agent import get_agent_with_neo4j_mcp_toolset
from fincen_agent.chat_repo import (
    MessageGrouper,
    create_chat,
    get_chat,
    save_messages,
    from_pydantic_ai_messages,
    to_pydantic_ai_messages,
)
from fincen_agent.config import AgentConfig, Neo4jConfig, PostgresConfig
from fincen_agent.models import ChatRequest


@lru_cache()
def get_agent_config() -> AgentConfig:
    """Provide the config via an easier-to-monkeypatch function."""
    return AgentConfig()  # type: ignore - ignore errors about missing required fields


@lru_cache()
def get_neo4j_config() -> Neo4jConfig:
    """Provide the config via an easier-to-monkeypatch function."""
    return Neo4jConfig()  # type: ignore - ignore errors about missing required fields


@lru_cache()
def get_postgres_config() -> PostgresConfig:
    """Provide the config via an easier-to-monkeypatch function."""
    return PostgresConfig()  # type: ignore - ignore errors about missing required fields


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Manage the asyncpg.Pool over the life of the app.

    FastAPI's `lifespan` context manager runs setup code (before the `yield`)
    before the server starts accepting requests and runs the teardown code
    (after the `yield`) when the server shuts down.
    """

    agent_config = get_agent_config()
    neo4j_config = get_neo4j_config()
    postgres_config = get_postgres_config()
    print("Initialising database pool")
    app.state.pool = await asyncpg.create_pool(
        dsn=postgres_config.dsn,
        server_settings={
            "search_path": postgres_config.postgres_schema,
        },
    )

    app.state.agent = get_agent_with_neo4j_mcp_toolset(
        agent_config=agent_config,
        neo4j_config=neo4j_config,
    )

    yield

    print("Closing database pool")
    if app.state.pool is not None:
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/v1")


async def get_db_connection(request: Request) -> AsyncGenerator:
    """Dependency that yields a database connection.

    Use `with` to guarantee the connection returned cleanly
    """
    async with request.app.state.pool.acquire() as conn:
        # Yield the connection to the end point
        yield conn


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def event_stream(
    request: ChatRequest,
    agent: Agent,
    chat_id: UUID4,
    history: list[ModelMessage] | None,
    conn: asyncpg.Connection,
    start_position: int,
) -> AsyncGenerator[str, None]:
    yield sse_event("meta", {"conversation_id": str(chat_id)})

    try:
        async with agent.run_stream(
            request.message,
            message_history=history if history else None,
        ) as stream:
            async for token in stream.stream_text(delta=True):
                yield sse_event("token", {"content": token})
            all_messages = stream.all_messages()

        offset = len(history) if history is not None else 0
        new_messages = all_messages[offset:]
        db_messages = from_pydantic_ai_messages(new_messages)
        await save_messages(
            chat_id=chat_id,
            messages=db_messages,
            start_position=start_position,
            conn=conn,
        )
        yield sse_event("done", {})

    except Exception as e:
        yield sse_event("error", {"message": str(e)})


@router.post("/chat")
async def chat_request(
    raw_request: Request, request: ChatRequest, conn=Depends(get_db_connection)
) -> StreamingResponse:
    agent = raw_request.app.state.agent
    if request.conversation_id is not None:
        chat = await get_chat(request.conversation_id, conn)
        chat_id = chat.id
        history = to_pydantic_ai_messages(
            messages=chat.messages, grouper=MessageGrouper()
        )
        start_position = chat.position + 1
    else:
        chat_id = await create_chat(conn)
        history = []
        start_position = 0

    return StreamingResponse(
        event_stream(
            request=request,
            agent=agent,
            chat_id=chat_id,
            history=history,
            conn=conn,
            start_position=start_position,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


app.include_router(router=router, prefix="/api")


# Health check
@app.get("/")
async def root():
    return {"status": "ok"}
