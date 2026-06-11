import asyncio
import logging
from asyncio import get_running_loop
from collections.abc import AsyncGenerator
from collections.abc import Callable
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from functools import partial
from uuid import uuid4

from atlassian import Confluence


logger = logging.getLogger(__name__)

from slurp.adapters.asyncio import flatten_lazy
from slurp.domain.config import ConfluenceConfig
from slurp.domain.config import GeneratorConfig
from slurp.domain.models import ConfluencePage
from slurp.domain.models import Task
from slurp.domain.ports import ProducerProtocol


@dataclass
class ConfluenceProducer(ProducerProtocol):
    config: ConfluenceConfig
    generator_config: GeneratorConfig

    client: Confluence | None = None

    def __post_init__(self):
        self.client = Confluence(
            url=self.config.base_url,
            username=self.config.username,
            password=self.config.api_key,
            cloud=self.config.cloud,
        )

    def months_back_predicate(self, months_back: int) -> Callable[[dict], bool]:
        def predicate(page: dict):
            if months_back is None or months_back <= 0:
                return True
            last_modified = (
                page.get("version", {}).get("when")
                or page.get("lastModified", {}).get("when")
                or page.get("history", {}).get("lastUpdated", {}).get("when")
                or page.get("_expandable", {}).get("lastModified")
                or page.get("created", {}).get("when")
            )

            if not last_modified:
                logger.debug("Could not determine last modified date for page %s", page.get("id"))
                logger.debug("Available date fields: %s", list(page.keys()))
                if "version" in page:
                    logger.debug("Version fields: %s", list(page["version"].keys()))
                if "history" in page:
                    logger.debug("History fields: %s", list(page["history"].keys()))
                return True

            try:
                if isinstance(last_modified, str) and last_modified.endswith("Z"):
                    last_modified = last_modified[:-1] + "+00:00"
                modified_date = (
                    datetime.fromisoformat(last_modified)
                    if isinstance(last_modified, str)
                    else last_modified
                )
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Error parsing date %r for page %s: %s", last_modified, page.get("id"), e
                )
                return True

            cutoff = datetime.now(modified_date.tzinfo) - timedelta(days=months_back * 30)
            if modified_date < cutoff:
                logger.debug(
                    "Skipping page %r - last modified %s (older than %s months)",
                    page.get("title", "Unknown"),
                    modified_date.strftime("%Y-%m-%d"),
                    months_back,
                )
                return False

            return True

        return predicate

    def name(self) -> str:
        return "confluence"

    def fetch_page(
        self, offset: int, limit: int, expand="version,history,lastModified"
    ) -> list[dict]:
        """Fetch a batch of pages from Confluence; return [] on API error."""
        try:
            raw = self.client.get_all_pages_from_space_raw(
                space=self.config.space, start=offset, limit=limit, expand=expand
            )
        except Exception:
            logger.warning(
                "Confluence fetch failed (space=%s offset=%s)",
                self.config.space,
                offset,
                exc_info=True,
            )
            return []
        return (raw or {}).get("results", [])

    async def __call__(self) -> AsyncGenerator[Task, None]:
        loop = get_running_loop()
        with ThreadPoolExecutor(max_workers=self.config.concurrency) as executor:
            fetchers = (
                loop.run_in_executor(
                    executor,
                    partial(
                        self.fetch_page,
                        offset=offset,
                        limit=min(self.config.page_batch_size, self.config.max_pages - offset),
                        expand="version,history,lastModified",
                    ),
                )
                for offset in range(
                    self.config.skip,
                    self.config.max_pages + self.config.skip,
                    self.config.page_batch_size,
                )
            )
            flat_results = list(flatten_lazy(await asyncio.gather(*fetchers)))

        predicate = self.months_back_predicate(self.config.months_back)
        for page in filter(predicate, flat_results):
            page: ConfluencePage
            task = Task(
                title=page.get("title"),
                url=page.get("id"),
                downloader="confluence",
                metadata={"links": page.get("_links", {})},
                # worst case download multiple times
                idempotency_key=page.get("version", {}).get("when", str(uuid4())),
                language=self.generator_config.language,
                difficulty=self.generator_config.difficulty_ratio,
                temperature=self.generator_config.temperature,
            )
            yield task
