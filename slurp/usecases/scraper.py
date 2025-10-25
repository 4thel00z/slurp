import asyncio
import sys
from dataclasses import dataclass
from dataclasses import field

from slurp.adapters.asyncio import aenumerate
from slurp.adapters.kafka import KafkaQueueSubmitter
from slurp.adapters.producers.confluence import ConfluenceProducer
from slurp.domain.config import AppConfig
from slurp.domain.ports import ProducerProtocol
from slurp.domain.ports import QueueSubmitterProtocol


@dataclass
class ScrapeUsecase:
    app_config: AppConfig = field(init=False)
    producer: ProducerProtocol = field(init=False)
    submitter: QueueSubmitterProtocol = field(init=False)

    def __post_init__(self):
        self.app_config = AppConfig.from_default(sys.argv)
        if self.app_config.instrumentation:
            self.app_config.instrumentation.setup()
        if self.app_config.confluence:
            self.producer = ConfluenceProducer(
                self.app_config.confluence, self.app_config.generator
            )

        self.submitter = KafkaQueueSubmitter(self.app_config.kafka)

    async def run(self):
        """
        Main scraper function that orchestrates the scraping process.
        """
        async with self.submitter:
            print(f"Starting scraper with producer: {self.producer.name()}")
            print(f"Kafka config: {self.app_config.kafka}")
            async for i, task in aenumerate(self.producer(), start=1):
                if not task:
                    print("Received empty task, breaking")
                    break
                print(f"Submitting task {i}: {task.title} (key: {task.idempotency_key})")
                await self.submitter.submit(task)
                print(f"Task {i} submitted successfully")

            print(f"Scraper completed. Total tasks submitted: {i}")


if __name__ == "__main__":
    import asyncio

    async def main():
        usecase = ScrapeUsecase()
        await usecase.run()

    asyncio.run(main())
