"""Tests for the local file producer."""

from slurp.adapters.producers.local import LocalProducer
from slurp.domain.config import GeneratorConfig
from slurp.domain.config import LocalConfig


def make_producer(local: LocalConfig) -> LocalProducer:
    generator = GeneratorConfig(language="en", model="test-model")
    return LocalProducer(config=local, generator_config=generator)


async def collect(producer: LocalProducer) -> list:
    return [task async for task in producer()]


def test_name():
    producer = make_producer(LocalConfig(path="."))
    assert producer.name() == "local"


async def test_yields_one_task_per_matching_file(tmp_path):
    """Every file with an allowed extension becomes a task."""
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")

    tasks = await collect(make_producer(LocalConfig(path=str(tmp_path))))

    assert len(tasks) == 2
    assert {t.downloader for t in tasks} == {"local"}
    assert all(t.url == str((tmp_path / t.title).resolve()) for t in tasks)


async def test_filters_by_extension(tmp_path):
    """Files outside the extension allowlist are skipped."""
    (tmp_path / "keep.md").write_text("keep", encoding="utf-8")
    (tmp_path / "skip.pdf").write_text("skip", encoding="utf-8")

    tasks = await collect(make_producer(LocalConfig(path=str(tmp_path), extensions=".md")))

    assert [t.title for t in tasks] == ["keep.md"]


async def test_single_file_path(tmp_path):
    """A path pointing at one file yields exactly that file."""
    f = tmp_path / "only.md"
    f.write_text("x", encoding="utf-8")

    tasks = await collect(make_producer(LocalConfig(path=str(f))))

    assert len(tasks) == 1
    assert tasks[0].url == str(f.resolve())


async def test_carries_generator_settings(tmp_path):
    """Tasks inherit language/difficulty/temperature from the generator config."""
    (tmp_path / "a.md").write_text("a", encoding="utf-8")

    tasks = await collect(make_producer(LocalConfig(path=str(tmp_path))))

    assert tasks[0].language == "en"
