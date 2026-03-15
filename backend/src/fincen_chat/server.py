import asyncio
import asyncpg
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import UUID4
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from temporalio.client import Client
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from .agent import get_agent_with_neo4j_mcp_toolset, init_langfuse
from .chat_repo import (
    MessageGrouper,
    create_chat,
    get_chat,
    save_messages,
    from_pydantic_ai_messages,
    to_pydantic_ai_messages,
)
from .config import (
    get_agent_config,
    get_neo4j_config,
    get_langfuse_config,
    get_postgres_config,
    get_temporal_config,
)
from .investigation.router import router as investigation_router
from .log_config import setup_logging
from .models import AgentOutput, ChatRequest, FinCENResponse

logger = logging.Logger(__file__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage the asyncpg.Pool over the life of the app.

    FastAPI's `lifespan` context manager runs setup code (before the `yield`)
    before the server starts accepting requests and runs the teardown code
    (after the `yield`) when the server shuts down.
    """
    setup_logging()

    agent_config = get_agent_config()
    neo4j_config = get_neo4j_config()
    langfuse_config = get_langfuse_config()
    postgres_config = get_postgres_config()
    temporal_config = get_temporal_config()

    init_langfuse(langfuse_config)
    logger.info("Initialising database pool")
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

    app.state.temporal_client = await Client.connect(
        temporal_config.temporal_address, plugins=[PydanticAIPlugin()]
    )

    yield

    logger.info("Closing database pool")
    if app.state.pool is not None:
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)
router = APIRouter(prefix="/v1")


async def get_db_connection(request: Request) -> AsyncGenerator[asyncpg.Pool, None]:
    """Dependency that yields a database connection."""
    async with request.app.state.pool.acquire() as conn:
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
        result = await agent.run(
            request.message,
            message_history=history if history else None,
        )

        output: AgentOutput = result.output
        all_messages = result.all_messages()

        if isinstance(output, FinCENResponse):
            async for chunk in stream_structured_response(output):
                yield chunk
        else:
            # Error response
            yield sse_event(
                "structured_response",
                {
                    "answer": output.reason,
                    "entities": [],
                    "confidence": "low",
                    "data_found": False,
                },
            )

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
        if isinstance(e, ExceptionGroup):
            messages = "; ".join(str(exc) for exc in e.exceptions)
            yield sse_event("error", {"message": messages})
        else:
            yield sse_event("error", {"message": str(e)})


async def stream_structured_response(
    output: FinCENResponse,
) -> AsyncGenerator[str, None]:
    """Simulate streaming by emitting answer tokens, then a metadata event."""
    words = output.answer.split()
    for ind, word in enumerate(words):
        token = word if ind == 0 else f" {word}"
        yield sse_event("token", {"content": token})
        await asyncio.sleep(0.01)  # small delay for visual effect

    yield sse_event(
        "response_meta",
        {
            "entities": [e.model_dump() for e in output.entities_mentioned],
            "confidence": output.confidence,
            "data_found": output.data_found,
        },
    )


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
        start_position = 0 if chat.position is None else chat.position + 1
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
app.include_router(router=investigation_router, prefix="/api/v1")


# Health check
@app.get("/")
async def root():
    return {"status": "ok"}
