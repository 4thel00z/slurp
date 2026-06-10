from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field

from slurp.domain.ports import DownloaderProtocol


@dataclass
class DownloaderRegistry:
    """Lazily builds and caches downloaders keyed by connector name.

    Factories are only invoked on first use, so unused connectors (e.g. the
    Confluence client when running in local mode) are never constructed.
    """

    factories: dict[str, Callable[[], DownloaderProtocol]]
    _cache: dict[str, DownloaderProtocol] = field(default_factory=dict)

    def get(self, name: str) -> DownloaderProtocol | None:
        if name not in self.factories:
            return None
        if name not in self._cache:
            self._cache[name] = self.factories[name]()
        return self._cache[name]
