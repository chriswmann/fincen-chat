import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from ..config import get_temporal_config
from .workflows import InvestigationWorkflow


async def main() -> None:
    config = get_temporal_config()
    client = await Client.connect(config.temporal_address, plugins=[PydanticAIPlugin()])

    async with Worker(
        client=client,
        task_queue=config.temporal_task_queue,
        workflows=[InvestigationWorkflow],
    ):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
