import asyncio
import logging
import sys
from dataclasses import dataclass
from dataclasses import field

from slurp.adapters.asyncio import aenumerate
from slurp.adapters.kafka import KafkaQueueSubmitter
from slurp.adapters.producers.confluence import ConfluenceProducer
from slurp.adapters.producers.local import LocalProducer
from slurp.domain.config import AppConfig
from slurp.domain.ports import ProducerProtocol
from slurp.domain.ports import QueueSubmitterProtocol
from slurp.domain.validation import validate_app_config


logger = logging.getLogger(__name__)


@dataclass
class ScrapeUsecase:
    app_config: AppConfig = field(init=False)
    producer: ProducerProtocol = field(init=False)
    submitter: QueueSubmitterProtocol = field(init=False)

    def __post_init__(self):
        self.app_config = AppConfig.from_default(sys.argv)
        validate_app_config(self.app_config)
        if self.app_config.instrumentation:
            self.app_config.instrumentation.setup()

        match self.app_config.connector:
            case "local":
                self.producer = LocalProducer(self.app_config.local, self.app_config.generator)
            case "confluence":
                self.producer = ConfluenceProducer(
                    self.app_config.confluence, self.app_config.generator
                )
            case other:
                raise ValueError(f"Unknown connector: {other}")

        self.submitter = KafkaQueueSubmitter(self.app_config.kafka)

    async def run(self):
        """Discover tasks from the producer and submit them to the queue."""
        async with self.submitter:
            logger.info("Starting scraper with producer: %s", self.producer.name())
            logger.info("Kafka config: %s", self.app_config.kafka)
            count = 0
            async for count, task in aenumerate(self.producer(), start=1):
                logger.info(
                    "Submitting task %d: %s (key: %s)", count, task.title, task.idempotency_key
                )
                await self.submitter.submit(task)
            logger.info("Scraper completed. Total tasks submitted: %d", count)


if __name__ == "__main__":
    import asyncio

    async def main():
        usecase = ScrapeUsecase()
        await usecase.run()

    asyncio.run(main())
