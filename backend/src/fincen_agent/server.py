from contextlib import asynccontextmanager
from functools import lru_cache
import asyncpg
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, UUID4

from backend.src.fincen_agent.chat_repo import (
    PostgresConfig,
    get_messages,
)

pool: asyncpg.Pool | None = None


@lru_cache()
def get_config() -> PostgresConfig:
    """Provide the config via an easier-to-monkeypatch function."""
    return PostgresConfig()


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Manage the asyncpg.Pool over the life of the app.

    Used with the `lifespan` argument of `FastAPI`.
    """
    global pool

    config = get_config()
    print("Initialising database pool")
    pool = asyncpg.create_pool(dsn=config.dsn)

    yield

    print("Closing database pool")
    if pool is not None:
        await pool.close()


app = FastAPI(lifespan=lifespan)


async def get_db_connection() -> None:
    """Dependency that yields a database connection."""
    if pool is None:
        raise RuntimeError("Database pool is not initialised")

    # Use `with` to guarantee the connection returned cleanly
    async with pool.connection() as conn:
        # Yield the connection to the end point
        yield conn


class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID4 | None


router = APIRouter(prefix="/v1")


@router.post("/chat")
async def chat_request(
    request: ChatRequest, db_conn=Depends(get_db_connection)
) -> StreamingResponse:
    if request.conversation_id is not None:
        messages = get_messages(request.conversation_id, db_conn)
    else:
        messages = [request.message]


app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    return {}
