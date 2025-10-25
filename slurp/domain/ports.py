from collections.abc import AsyncGenerator
from collections.abc import AsyncIterable
from typing import Protocol
from typing import runtime_checkable

from slurp.domain.models import Generation
from slurp.domain.models import Task
from slurp.domain.models import TaskResult


@runtime_checkable
class ProducerProtocol(Protocol):
    async def __call__(self) -> AsyncGenerator[Task, None]:
        """Async-yield Task items to be fetched."""
        ...

    def name(self) -> str: ...


@runtime_checkable
class QueueSubmitterProtocol(Protocol):
    async def submit(self, task: Task) -> None:
        """Submit a Task to the queue."""
        ...


@runtime_checkable
class ConsumerProtocol(Protocol):
    async def __call__(self) -> AsyncGenerator[Task, None]:
        """Async-yield Task items to be fetched."""
        ...

    async def acknowledge(self, task_result: TaskResult) -> None:
        """Acknowledge that a Task has been processed."""
        ...


@runtime_checkable
class DownloaderProtocol(Protocol):
    async def __call__(self, task: Task) -> TaskResult | None:
        """
        Download the content of the task and return a TaskResult.
        Return None if the task cannot be processed.
        """
        ...


class TaskResultMutatorProtocol(Protocol):
    async def __call__(self, response: TaskResult) -> TaskResult | None:
        """
        Mutate the TaskResult.
        Return it back after the mutation.
        """
        ...


@runtime_checkable
class GeneratorProtocol(Protocol):
    async def generate(self, task_result: TaskResult) -> Generation:
        """Normalize or clean bytes and return text."""
        ...

    async def generate_from_batch(self, *task_results: TaskResult) -> AsyncIterable[Generation]:
        """Normalize or clean bytes and return a list of texts."""
        ...


class GenerationMutatorProtocol(Protocol):
    async def __call__(self, response: TaskResult) -> TaskResult | None:
        """
        Mutate the TaskResult.
        Return it back after the mutation.
        """
        ...
