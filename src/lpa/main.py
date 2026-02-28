import asyncio
import base64
import os
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

MODEL = os.getenv("MODEL", "google-gla:gemini-3-flash-preview")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


async def main() -> None:
    credentials = base64.b64encode(
        f"{NEO4J_USERNAME}:{NEO4J_PASSWORD}".encode()
    ).decode()
    server = MCPServerStreamableHTTP(
        "http://localhost:8000/mcp",
        headers={"Authorization": f"Basic {credentials}"},
    )

    agent = Agent(
        MODEL,
        system_prompt="You are a helpful assistant",
        toolsets=[server],
    )

    response = await agent.run("What banks are listed in the database?")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
