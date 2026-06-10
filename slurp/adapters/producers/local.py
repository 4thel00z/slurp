import logging
from collections.abc import AsyncGenerator
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from slurp.domain.config import GeneratorConfig
from slurp.domain.config import LocalConfig
from slurp.domain.models import Task
from slurp.hash import strhash


logger = logging.getLogger(__name__)


@dataclass
class LocalProducer:
    """Discovers local files and emits one Task per file."""

    config: LocalConfig
    generator_config: GeneratorConfig

    def name(self) -> str:
        return "local"

    def _iter_files(self) -> Iterator[Path]:
        root = Path(self.config.path).expanduser()
        if root.is_file():
            # An explicitly named file is honored regardless of extension.
            yield root.resolve()
            return

        if not root.is_dir():
            logger.warning("Local path %s does not exist.", self.config.path)
            return

        allowed = self.config.extension_list()
        for candidate in sorted(root.glob(self.config.glob)):
            if not candidate.is_file():
                continue
            if allowed and candidate.suffix.lower() not in allowed:
                continue
            yield candidate.resolve()

    async def __call__(self) -> AsyncGenerator[Task, None]:
        for path in self._iter_files():
            abs_path = str(path)
            yield Task(
                title=path.name,
                url=abs_path,
                downloader="local",
                metadata={"path": abs_path},
                idempotency_key=strhash(abs_path),
                language=self.generator_config.language,
                difficulty=self.generator_config.difficulty_ratio,
                temperature=self.generator_config.temperature,
            )
