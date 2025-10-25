import sys
import asyncio
import logging
from dataclasses import dataclass
from typing import AsyncGenerator, AsyncIterator

logger = logging.getLogger(__name__)

from slurp.domain.config import AppConfig, SQLiteConfig
from slurp.adapters.kafka import KafkaConsumer
from slurp.adapters.downloader.confluence import ConfluenceDownloader
from slurp.adapters.mutators.html_parser import HTMLParser
from slurp.adapters.mutators.sqlite_persistence import SqlitePersistence
from slurp.adapters.generators.llm import LLMGenerator
from slurp.domain.models import Generation, TaskResult


@dataclass
class WorkerUsecase:
    app_config: AppConfig = None

    def __post_init__(self):
        # load all configuration from environment/args
        self.app_config = AppConfig.from_default(sys.argv)
        if self.app_config.instrumentation:
            self.app_config.instrumentation.setup()
        logger.info("WorkerUsecase initialized.")

        # initialize protocols
        self.consumer = KafkaConsumer(self.app_config.kafka)
        self.downloader = ConfluenceDownloader(self.app_config.confluence)
        self.persistence = SqlitePersistence(sqlite_config=self.app_config.sqlite)
        # mutators: HTML parsing then persistence
        self.mutators = [
            self.consumer.acknowledge,
            HTMLParser(),
            self.persistence
        ]
        # formatter for question/answer generation
        self.generator = LLMGenerator(
            token_config=self.app_config.token,
            config=self.app_config.generator,
        )
        if not self.generator:
            logger.warning("No generator configured, skipping generation step.")
        self.generation_mutators = [
            self.persistence
        ]

    async def process(self, result: TaskResult) -> AsyncIterator[Generation]:
        if not self.app_config.generator.enabled:
            return

        gen = await self.generator.generate(result)
        if not gen:
            return
        for m in self.generation_mutators:
            gen = await m(gen)
            if not gen:
                return
        logger.info(f"Generated 1‐item batch → {len(gen.question_answers)} QAs from '{result.title}'.")
        yield gen

    async def process_batch(self, results: list[TaskResult]) -> AsyncIterator[Generation]:
        if not self.app_config.generator.enabled:
            return

        async for gen in self.generator.generate_from_batch(*results):
            for m in self.generation_mutators:
                gen = await m(gen)
                if not gen:
                    break

            logger.info(f"Generated {len(results)}‐item batch → {len(gen.question_answers)} QAs.")
            yield gen

    async def run(self) -> AsyncIterator[Generation]:
        """
        Main worker function that orchestrates the worker process.
        """
        batch_size = self.app_config.generator.batch_size
        results: list[TaskResult] = []

        logger.info("Starting worker run loop.")
        async with self.consumer:
            async for task in self.consumer():
                logger.info(f"Processing task: {task.idempotency_key} with downloader: {task.downloader}")
                result = await self.downloader(task)
                if not result:
                    continue
                logger.info(f"Finished downloading task: {task.idempotency_key}. Result: {result.content[:100]}...")

                # apply mutators
                for mut in self.mutators:
                    logger.info(f"Applying mutator: {mut.__class__.__name__} to task: {task.idempotency_key}")
                    result = await mut(result)
                    if not result:
                        break

                if not result:
                    logger.info(f"No result for task: {task.idempotency_key}")
                    continue

                logger.info(f"Finished mutating task: {task.idempotency_key}. Result: {result.content[:100]}...")
                results.append(result)
                # single-item mode
                if batch_size <= 1:
                    # flush single immediately
                    current = results.pop(0)
                    async for g in self.process(current):
                        yield g
                    continue

                # batch mode flush when full
                if len(results) >= batch_size:
                    async for g in self.process_batch(results):
                        yield g
                    results.clear()

            # final flush of leftovers
            if not results: return

            if batch_size <= 1:
                current = results.pop(0)
                async for g in self.process(current):
                    yield g
            else:
                async for g in self.process_batch(results):
                    yield g
                logger.info(f"Flushed final batch of {len(results)} results.")
                results.clear()



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from slurp.adapters.asyncio import consume_async_gen


    def handle(generation):
        for qa in generation.question_answers:
            logger.info(f"""Q: {qa.question}
                    A: {qa.answer}
                       ---""")

    async def main():
        usecase = WorkerUsecase()

        await consume_async_gen(usecase.run(), handle)


    asyncio.run(main())
