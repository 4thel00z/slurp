"""KafkaQueueSubmitter.submit does not flush per message."""

import pytest

from slurp.adapters.kafka import KafkaQueueSubmitter
from slurp.domain.config import KafkaConfig
from slurp.domain.models import Task


@pytest.mark.asyncio
async def test_submit_does_not_flush_each_message():
    sub = KafkaQueueSubmitter(KafkaConfig())

    class FakeProducer:
        def __init__(self):
            self.sent = 0
            self.flushed = 0

        async def send(self, *_, **__):
            self.sent += 1

        async def flush(self):
            self.flushed += 1

    sub.producer = FakeProducer()
    task = Task(title="t", url="u", downloader="local", idempotency_key="k", metadata={})
    await sub.submit(task)
    assert sub.producer.sent == 1
    assert sub.producer.flushed == 0
