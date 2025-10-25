import logging
from collections.abc import AsyncGenerator
from dataclasses import asdict
from dataclasses import dataclass

import orjson
from aiokafka import AIOKafkaConsumer
from aiokafka import AIOKafkaProducer

from slurp.domain.config import KafkaConfig
from slurp.domain.models import Task
from slurp.domain.models import TaskResult
from slurp.domain.ports import ConsumerProtocol
from slurp.domain.ports import QueueSubmitterProtocol


logger = logging.getLogger(__name__)


@dataclass
class KafkaQueueSubmitter(QueueSubmitterProtocol):
    """
    Submits Task instances to a Kafka topic (Redpanda-compatible).
    """

    config: KafkaConfig
    producer: AIOKafkaProducer = None

    def __post_init__(self):
        if not self.config.bootstrap_servers:
            raise ValueError("Kafka bootstrap servers must be provided in the configuration.")
        if not self.config.topic:
            raise ValueError("Kafka topic must be provided in the configuration.")
        if not self.config.client_id:
            raise ValueError("Kafka client ID must be provided in the configuration.")
        self.producer = None

    @staticmethod
    def serialize_task(task: Task):
        """Serialize a Task instance to JSON."""
        if not isinstance(task, Task):
            raise TypeError("Expected a Task instance.")

        return orjson.dumps(asdict(task))

    async def __aenter__(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers,
            client_id=self.config.client_id,
            value_serializer=self.serialize_task,
            key_serializer=lambda s: str(s).encode("utf-8"),
            enable_idempotence=True,
        )
        await self.producer.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.producer:
            await self.producer.flush()
            await self.producer.stop()

    async def submit(self, task: Task) -> None:
        """Serialize and send a Task to Kafka."""
        if not self.producer:
            raise RuntimeError("Kafka producer is not initialized. Use 'async with' context.")
        await self.producer.send(self.config.topic, task, key=task.idempotency_key)
        # Flush to ensure the message is sent immediately
        await self.producer.flush()


@dataclass
class KafkaConsumer(ConsumerProtocol):
    config: KafkaConfig
    consumer: AIOKafkaConsumer = None

    def __post_init__(self):
        if not self.config.bootstrap_servers:
            raise ValueError("Kafka bootstrap servers must be provided in the configuration.")
        if not self.config.topic:
            raise ValueError("Kafka topic must be provided in the configuration.")
        if not self.config.client_id:
            raise ValueError("Kafka client ID must be provided in the configuration.")
        self.consumer = None

    async def __aenter__(self):
        self.consumer = AIOKafkaConsumer(
            self.config.topic,
            bootstrap_servers=self.config.bootstrap_servers,
            client_id=self.config.client_id,
            group_id=f"{self.config.client_id}-group",
            value_deserializer=lambda val: Task(**orjson.loads(val)),
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        logger.info("KafkaConsumer initialized.")
        logger.info("KafkaConsumer starting.")
        await self.consumer.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.consumer:
            logger.info("KafkaConsumer stopping.")
            await self.consumer.stop()

    async def __call__(self) -> AsyncGenerator[Task, None]:
        """Async-yield Task items to be fetched."""
        async for msg in self.consumer:
            logger.info("KafkaConsumer yielding message.")
            yield msg.value

    async def acknowledge(self, task_result: TaskResult) -> None:
        """Acknowledge that a Task has been processed."""
        logger.info("KafkaConsumer committing offset.")
        await self.consumer.commit()
        return task_result
