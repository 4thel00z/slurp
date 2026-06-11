"""Scraper must not raise when the producer yields nothing."""

import pytest

from slurp.usecases.scraper import ScrapeUsecase


@pytest.mark.asyncio
async def test_run_with_no_tasks_does_not_raise(monkeypatch):
    uc = ScrapeUsecase.__new__(ScrapeUsecase)

    class EmptyProducer:
        def name(self):
            return "empty"

        async def __call__(self):
            return
            yield  # make it an async generator

    class NullSubmitter:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def submit(self, task): ...

    uc.producer = EmptyProducer()
    uc.submitter = NullSubmitter()

    class _Cfg:
        kafka = None

    uc.app_config = _Cfg()
    await uc.run()  # must not raise UnboundLocalError
