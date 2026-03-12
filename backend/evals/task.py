from fincen_chat.agent import get_agent_with_neo4j_mcp_toolset
from fincen_chat.config import get_agent_config, get_neo4j_config
from fincen_chat.models import AgentOutput


async def run_agent(question: str) -> AgentOutput:
    """Task function for pydantic evals.

    Each eval Case passes a question `str` as `inputs`.
    This function runs the real agent and returns its output.
    """
    agent_config = get_agent_config()
    neo4j_config = get_neo4j_config()

    agent = get_agent_with_neo4j_mcp_toolset(
        agent_config=agent_config,
        neo4j_config=neo4j_config,
    )

    async with agent:
        result = await agent.run(question)

    return result.output
