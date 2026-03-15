from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from .models import InvestigationReport, SubQueryResult, ResearchPlan
from ..config import get_agent_config, get_neo4j_config

_config = get_agent_config()

planning_agent = Agent(
    _config.model,
    output_type=ResearchPlan,
    instructions="""You are a research planner for FinCEN financial crime investigations.
    Given a user's investigation query, decompose it into 3-6 focused sub-queries
    that can each be answered by querying a Neo4j graph of FinCEN filing data.
    """,
    name="planner",
)
planning_agent.instrument_all()

temporal_planner = TemporalAgent(planning_agent)


_neo4j = get_neo4j_config()
_credentials = _neo4j.get_encoded_credentials()

def _get_neo4j_mcp() -> MCPServerStreamableHTTP:
    return MCPServerStreamableHTTP(
        _neo4j.neo4j_mcp_url,
        headers={"Authorization": f"Basic {_credentials}"},
        tool_prefix="neo4j",  # Sets the toolset ID for Temporal activity naming
    )

research_agent = Agent(
    _config.model,
    output_type=SubQueryResult,
    instructions="""You are a research agent investigating FinCEN data.
    Given a specific sub-query, use the Neo4j graph tools to find relevant data.
    Report your findings thoroughly, listing all entities discovered.""",
    toolsets=[_get_neo4j_mcp()],
    name="researcher",
    retries=3,
)
research_agent.instrument_all()

temporal_researcher = TemporalAgent(research_agent)

synthesis_agent = Agent(
    _config.model,
    output_type=InvestigationReport,
    instructions="""You are an analyst synthesising findings from a FinCEN investigation.
    Given the original query and research findings from multiple sub-queries,
    produce a comprehensive investigation report with an executive summary,
    detailed findings, risk indicators, and recommendations...""",
    name="synthesiser",
)
synthesis_agent.instrument_all()

temporal_synthesiser = TemporalAgent(synthesis_agent)
