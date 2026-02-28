import asyncio
import os
from pydantic_ai import Agent

MODEL = os.getenv("MODEL", "google-gla:gemini-3-flash-preview")


async def main():

    agent = Agent(
        MODEL,
        system_prompt="You are a helpful assistant",
    )

    response = await agent.run("Hi, what is your name?")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
