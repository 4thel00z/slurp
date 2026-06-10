"""Tests for the local file downloader."""

from slurp.adapters.downloader.local import LocalDownloader
from slurp.domain.models import Task


def make_task(url: str, downloader: str = "local") -> Task:
    return Task(title="doc", url=url, downloader=downloader, idempotency_key="key", metadata={})


async def test_reads_file_content_into_task_result(tmp_path):
    """Downloader reads the file at task.url into a TaskResult."""
    f = tmp_path / "note.md"
    f.write_text("# Hello\n\nworld", encoding="utf-8")

    result = await LocalDownloader()(make_task(str(f)))

    assert result is not None
    assert result.content == "# Hello\n\nworld"
    assert result.status_code == 200
    assert result.url == str(f)
    assert result.hash


async def test_rejects_non_local_task(tmp_path):
    """A task addressed to another downloader is ignored."""
    f = tmp_path / "note.md"
    f.write_text("data", encoding="utf-8")

    result = await LocalDownloader()(make_task(str(f), downloader="confluence"))

    assert result is None


async def test_missing_file_returns_none(tmp_path):
    """A task pointing at a nonexistent file yields no result."""
    result = await LocalDownloader()(make_task(str(tmp_path / "nope.md")))

    assert result is None
