import base64
from langfuse import Langfuse
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from .config import AgentConfig, LangfuseConfig, Neo4jConfig
from .tracing import instrument


def init_langfuse(config: LangfuseConfig) -> Langfuse:
    langfuse = Langfuse(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key.get_secret_value(),
        host=config.langfuse_host,
    )
    langfuse.auth_check()
    return langfuse


@instrument
def get_agent_with_neo4j_mcp_toolset(
    agent_config: AgentConfig,
    neo4j_config: Neo4jConfig,
) -> Agent:
    credentials = base64.b64encode(
        f"{neo4j_config.neo4j_username}:{neo4j_config.neo4j_password}".encode()
    ).decode()
    server = MCPServerStreamableHTTP(
        "http://localhost:8000/mcp",
        headers={"Authorization": f"Basic {credentials}"},
    )

    agent = Agent(
        agent_config.model,
        system_prompt="You are a helpful assistant",
        toolsets=[server],
        retries=3,
    )

    agent.instrument_all()

    return agent
