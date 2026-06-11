import logging
from dataclasses import dataclass

from atlassian import Confluence


logger = logging.getLogger(__name__)

from slurp.domain.config import ConfluenceConfig
from slurp.domain.models import Task
from slurp.domain.models import TaskResult
from slurp.domain.ports import DownloaderProtocol
from slurp.hash import strhash


@dataclass
class ConfluenceDownloader(DownloaderProtocol):
    """
    A consumer for Confluence tasks.
    This class is responsible for processing Confluence tasks and returning the results.
    """

    config: ConfluenceConfig
    client: Confluence | None = None

    def __post_init__(self):
        self.client = Confluence(
            url=self.config.base_url,
            username=self.config.username,
            password=self.config.api_key,
            cloud=self.config.cloud,
            advanced_mode=True,
        )

    async def __call__(self, task: Task) -> TaskResult | None:
        if task.downloader != "confluence":
            logger.warning("Task %s is not for the Confluence downloader.", task.idempotency_key)
            return None

        try:
            res = self.client.get_page_by_id(task.url, expand="body.storage,body.view")
        except Exception:
            logger.warning("Confluence download failed for %s", task.url, exc_info=True)
            return None

        if not res.ok:
            return TaskResult(
                title=task.title,
                url=task.url,
                status_code=res.status_code,
                content=res.text,
                hash=strhash(res.text),
                headers=res.headers,
                temperature=task.temperature,
                difficulty=task.difficulty,
                language=task.language,
            )

        try:
            page = res.json()
        except ValueError:
            logger.warning("Confluence returned non-JSON body for %s", task.url)
            return None

        if not page:
            logger.warning("Empty Confluence content for page %s", task.url)
            return None

        body_html = page.get("body", {}).get("view", {}).get("value", "")
        return TaskResult(
            title=task.title,
            url=task.url,
            status_code=res.status_code,
            content=body_html,
            hash=strhash(body_html),
            headers=res.headers,
            temperature=task.temperature,
            difficulty=task.difficulty,
            language=task.language,
        )
