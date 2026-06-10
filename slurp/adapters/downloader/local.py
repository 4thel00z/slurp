import logging
from dataclasses import dataclass
from pathlib import Path

from slurp.domain.config import LocalConfig
from slurp.domain.models import Task
from slurp.domain.models import TaskResult
from slurp.domain.ports import DownloaderProtocol
from slurp.hash import strhash


logger = logging.getLogger(__name__)


@dataclass
class LocalDownloader(DownloaderProtocol):
    """Reads task content from a local file path (``task.url``)."""

    config: LocalConfig | None = None

    async def __call__(self, task: Task) -> TaskResult | None:
        if task.downloader != "local":
            logger.warning("Task %s is not for the local downloader.", task.idempotency_key)
            return None

        path = Path(task.url)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as err:
            logger.warning("Could not read local file %s: %s", task.url, err)
            return None

        return TaskResult(
            title=task.title,
            url=task.url,
            status_code=200,
            content=content,
            hash=strhash(content),
            headers={},
            temperature=task.temperature,
            difficulty=task.difficulty,
            language=task.language,
        )
