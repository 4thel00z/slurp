import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dataclasses import field

from slurp.adapters.downloader.confluence import ConfluenceDownloader
from slurp.adapters.downloader.local import LocalDownloader
from slurp.adapters.downloader.registry import DownloaderRegistry
from slurp.adapters.generators.llm import LLMGenerator
from slurp.adapters.instrumentation import setup_instrumentation
from slurp.adapters.kafka import KafkaConsumer
from slurp.adapters.mutators.html_parser import HTMLParser
from slurp.adapters.mutators.sqlite_persistence import SqlitePersistence
from slurp.domain.config import AppSettings
from slurp.domain.config import load_settings
from slurp.domain.models import Generation
from slurp.domain.models import TaskResult


logger = logging.getLogger(__name__)


@dataclass
class WorkerUsecase:
    app_config: AppSettings = field(init=False)

    def __post_init__(self):
        # load all configuration from environment/args
        self.app_config = load_settings(sys.argv)
        setup_instrumentation(self.app_config.instrumentation.logfire_token)
        logger.info("WorkerUsecase initialized.")

        # initialize protocols
        self.consumer = KafkaConsumer(self.app_config.kafka)
        # downloaders are dispatched by task.downloader and built lazily, so
        # local-only runs never construct the Confluence client.
        self.downloaders = DownloaderRegistry(
            {
                "confluence": lambda: ConfluenceDownloader(self.app_config.confluence),
                "local": lambda: LocalDownloader(self.app_config.local),
            }
        )
        self.persistence = SqlitePersistence(sqlite_config=self.app_config.sqlite)
        # mutators: HTML parsing then persistence
        self.html_parser = HTMLParser()
        self.mutators = [self.consumer.acknowledge, self.html_parser, self.persistence]
        # formatter for question/answer generation; only built when enabled so the
        # worker can run the download/parse/persist path without an LLM token.
        self.generator = None
        if self.app_config.generator.enabled:
            self.generator = LLMGenerator(
                token_config=self.app_config.token, config=self.app_config.generator
            )
        else:
            logger.warning("Generator disabled, skipping QA generation step.")
        self.generation_mutators = [self.persistence]

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
        logger.info(
            f"Generated 1‐item batch → {len(gen.question_answers)} QAs from '{result.title}'."
        )
        yield gen

    async def process_batch(self, results: list[TaskResult]) -> AsyncIterator[Generation]:
        if not self.app_config.generator.enabled:
            return

        async for gen in self.generator.generate_from_batch(*results):
            for m in self.generation_mutators:
                gen = await m(gen)  # noqa: PLW2901 - intentional mutation chain
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
        try:
            async with self.consumer:
                async for task in self.consumer():
                    logger.info(
                        f"Processing task: {task.idempotency_key} with downloader: {task.downloader}"
                    )
                    downloader = self.downloaders.get(task.downloader)
                    if downloader is None:
                        logger.warning(
                            f"No downloader registered for '{task.downloader}', skipping task."
                        )
                        continue
                    result = await downloader(task)
                    if not result:
                        continue
                    logger.info(
                        f"Finished downloading task: {task.idempotency_key}. Result: {result.content[:100]}..."
                    )

                    # apply mutators
                    for mut in self.mutators:
                        logger.info(
                            f"Applying mutator: {mut.__class__.__name__} to task: {task.idempotency_key}"
                        )
                        result = await mut(result)
                        if not result:
                            break

                    if not result:
                        logger.info(f"No result for task: {task.idempotency_key}")
                        continue

                    logger.info(
                        f"Finished mutating task: {task.idempotency_key}. Result: {result.content[:100]}..."
                    )
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
                if not results:
                    return

                if batch_size <= 1:
                    current = results.pop(0)
                    async for g in self.process(current):
                        yield g
                else:
                    async for g in self.process_batch(results):
                        yield g
                    logger.info(f"Flushed final batch of {len(results)} results.")
                    results.clear()
        finally:
            self.html_parser.shutdown()
            await self.persistence.aclose()


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
