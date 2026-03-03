import asyncio

import logging

from .log_config import setup_logging

logger = logging.Logger(__file__)


async def main() -> None:

    setup_logging()

    logging.info("Hello")


if __name__ == "__main__":
    asyncio.run(main())
