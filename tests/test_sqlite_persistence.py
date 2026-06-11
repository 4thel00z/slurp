"""Async persistence must actually write rows (regression for missing greenlet)."""

import pytest
from sqlalchemy import text

from slurp.adapters.mutators.sqlite_persistence import SqlitePersistence
from slurp.domain.config import SQLiteConfig
from slurp.domain.models import TaskResult


def make_result() -> TaskResult:
    return TaskResult(
        title="doc",
        status_code=200,
        headers={},
        content="hello world",
        hash="h1",
        url="/tmp/doc.md",
    )


async def test_persists_task_result(tmp_path):
    """A TaskResult is committed and readable back from the database."""
    db = tmp_path / "p.db"
    persistence = SqlitePersistence(sqlite_config=SQLiteConfig(database=str(db), timeout=5.0))

    returned = await persistence(make_result())

    assert returned is not None
    async with persistence.async_engine.connect() as conn:
        count = (await conn.execute(text("SELECT count(*) FROM task_results"))).scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_aclose_disposes_engine(tmp_path):
    cfg = SQLiteConfig(database=str(tmp_path / "x.db"))
    p = SqlitePersistence(sqlite_config=cfg)
    await p.aclose()  # must not raise
