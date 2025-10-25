from dataclasses import dataclass

from atlassian import Confluence

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
        """
        Process the Confluence task.
        This method should be implemented to handle the specific logic for consuming a Confluence task.
        """
        # Placeholder for actual implementation
        print(f"Consuming task: {task}")
        if task.downloader != "confluence":
            print("⚠️  This task is not for Confluence consumer.")
            return None

        res = self.client.get_page_by_id(task.url, expand="body.storage,body.view")

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

        page = res.json()

        if not page:
            print(f"⚠️  Failed to get content for page {task.url}")
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
