import asyncio
import os

from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from db import DBConfig, setup_db

MODEL = os.getenv("MODEL", "google-gla:gemini-3-flash-preview")


async def main():
    db_config = DBConfig()
    setup_db(db_config)
    agent = Agent(
        MODEL,
        system_prompt="You are a helpful assistant",
    )

    response = await agent.run("Hi, what is your name?")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
