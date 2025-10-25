import asyncio
from asyncio import get_running_loop
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from typing import Callable, AsyncGenerator
from uuid import uuid4

from atlassian import Confluence

from slurp.adapters.asyncio import flatten_lazy
from slurp.domain.config import ConfluenceConfig, GeneratorConfig
from slurp.domain.models import ConfluencePage, Task
from slurp.domain.ports import ProducerProtocol


@dataclass
class ConfluenceProducer(ProducerProtocol):
    config: ConfluenceConfig
    generator_config: GeneratorConfig

    client: Confluence = None

    def __post_init__(self):
        self.client = Confluence(
            url=self.config.base_url,
            username=self.config.username,
            password=self.config.api_key,
            cloud=self.config.cloud,
        )

    def months_back_predicate(self, months_back: int) -> Callable[[dict], bool]:
        def predicate(
                page: dict,
        ):
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
                print(
                    f"    ⚠️  Could not determine last modified date for page {page.get('id')}"
                )
                print(f"        Available date fields: {list(page.keys())}")
                if "version" in page:
                    print(f"        Version fields: {list(page['version'].keys())}")
                if "history" in page:
                    print(f"        History fields: {list(page['history'].keys())}")
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
                print(
                    f"    ⚠️  Error parsing date '{last_modified}' for page {page.get('id')}: {e}"
                )
                return True

            cutoff = datetime.now(modified_date.tzinfo) - timedelta(
                days=months_back * 30
            )
            if modified_date < cutoff:
                print(
                    f"    ⏰ Skipping page '{page.get('title', 'Unknown')}' - "
                    f"last modified {modified_date:%Y-%m-%d} (older than {months_back} months)"
                )
                return False

            return True

        return predicate

    def name(self) -> str:
        return "confluence"

    def fetch_page(self, offset: int, limit: int, expand="version,history,lastModified") -> list[dict]:
        """
        Fetch a batch of pages from Confluence.
        This method is used to fetch pages in batches based on the offset and limit.
        """
        return (self.client.get_all_pages_from_space_raw(
            space=self.config.space,
            start=offset,
            limit=limit,
            expand=expand,
        ) or {}).get("results", [])

    async def __call__(self) -> AsyncGenerator[Task, None]:
        loop = get_running_loop()
        executor = ThreadPoolExecutor(max_workers=self.config.concurrency)
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
        ))
        flat_results = flatten_lazy(await asyncio.gather(*fetchers))

        predicate = self.months_back_predicate(self.config.months_back)
        filtered_results = filter(predicate, flat_results)

        for page in filtered_results:
            page: ConfluencePage
            task = Task(
                title=page.get("title"),
                url=page.get("id"),
                downloader="confluence",
                metadata={
                    "links": page.get("_links", {}),
                },
                # worst case download multiple times
                idempotency_key=page.get("version", {}).get("when", str(uuid4())),
                language=self.generator_config.language,
                difficulty=self.generator_config.difficulty_ratio,
                temperature=self.generator_config.temperature,
            )
            yield task