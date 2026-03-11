import base64
from langfuse import Langfuse
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.mcp import MCPServerStreamableHTTP
from .config import AgentConfig, LangfuseConfig, Neo4jConfig, REFUSAL_MESSAGE
from .models import AgentOutput, FinCENResponse


def init_langfuse(config: LangfuseConfig) -> Langfuse:
    langfuse = Langfuse(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key.get_secret_value(),
        host=config.langfuse_host,
    )
    langfuse.auth_check()
    return langfuse


def get_agent_with_neo4j_mcp_toolset(
    agent_config: AgentConfig,
    neo4j_config: Neo4jConfig,
) -> Agent:
    credentials = base64.b64encode(
        f"{neo4j_config.neo4j_username}:{neo4j_config.neo4j_password.get_secret_value()}".encode()
    ).decode()
    server = MCPServerStreamableHTTP(
        neo4j_config.neo4j_mcp_url,
        headers={"Authorization": f"Basic {credentials}"},
    )

    agent = Agent(
        agent_config.model,
        output_type=AgentOutput,
        instructions=f"""
        You are a helpful assistant who answers queries about FinCEN 
        (Financial Crimes Enforcement Network) data. You can only answer 
        questions about the FinCEN data that you have access to via the fincen 
        graph database. If the user tries to ask about anything other than the 
        fincen data, you must respond with: '{REFUSAL_MESSAGE}.

        When you have searched the graph and found relevant data, respond with 
        a FinCENResponse. Set data_found=true and populate entities_mentioned
        with any named entities (banks, individuals, companies, countries) 
        referenced in your answer.

        If the user asks about something related to the FinCEN dataset but the 
        graph returns no relevant data, respond with an ErrorResponse explaining 
        why you cannot answer.
        """,
        toolsets=[server],
        retries=3,
    )

    agent.instrument_all()

    @agent.output_validator
    async def validate_fincen_response(output: AgentOutput) -> AgentOutput:
        """Domain-level validation.

        If the model says `data_found=True` but listed no entities, that seems odd,
        so ask it to try again with more detail.
        """
        if isinstance(output, FinCENResponse):
            if output.data_found and not output.answer.strip():
                raise ModelRetry(
                    "You indicated data was found but provided an empty answer."
                    "Please provide a complete answer based on the graph data."
                )
        return output

    return agent
