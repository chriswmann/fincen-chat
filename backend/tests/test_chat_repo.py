import asyncio
from fincen_agent.chat_repo import *


async def test():
    config = PostgresConfig()
    pool = await create_pool(config)
    chat_id = await create_chat(pool)
    print(f"Created chat: {chat_id}")

    msgs = [Message(id=..., content="Hello", role=Role.USER)]
    await save_messages(chat_id, msgs, pool)

    chat = await get_chat(chat_id, pool)
    print(f"Chat has {chat.num_messages} messages")

    await pool.close()


asyncio.run(test())
