"""ConfluenceDownloader error handling."""

import pytest

from slurp.adapters.downloader.confluence import ConfluenceDownloader
from slurp.domain.config import ConfluenceConfig
from slurp.domain.models import Task


def _downloader():
    d = ConfluenceDownloader.__new__(ConfluenceDownloader)
    d.config = ConfluenceConfig(username="u", api_key="k", space="s")
    d.client = None
    return d


def _task():
    return Task(title="t", url="123", downloader="confluence", idempotency_key="k", metadata={})


@pytest.mark.asyncio
async def test_returns_none_on_client_error():
    d = _downloader()

    class Boom:
        def get_page_by_id(self, *_, **__):
            raise RuntimeError("boom")

    d.client = Boom()
    assert await d(_task()) is None


@pytest.mark.asyncio
async def test_wrong_downloader_returns_none():
    d = _downloader()
    task = _task()
    task.downloader = "local"
    assert await d(task) is None
