import asyncio
import uuid
from fincen_agent.chat_repo import *


async def create_conn(config: PostgresConfig) -> asyncpg.Connection:
    """Create and return an asyncpg.Connection"""
    conn = await asyncpg.connect(
        dsn=config.dsn, server_settings={"search_path": config.postgres_schema}
    )
    return conn


async def test():
    config = PostgresConfig()
    conn = await create_conn(config)
    chat_id = await create_chat(conn)
    print(f"Created chat: {chat_id}")

    msgs = [Message(id=uuid.uuid4(), content="Hello", role=Role.USER)]
    await save_messages(chat_id, msgs, conn)

    chat = await get_chat(chat_id, conn)
    print(f"Chat has {chat.num_messages} messages")

    await conn.close()


asyncio.run(test())
