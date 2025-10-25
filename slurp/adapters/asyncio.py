import asyncio
from asyncio import Semaphore
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any
from typing import AsyncContextManager
from typing import TypeVar


T = TypeVar("T")


@asynccontextmanager
async def noop_ctx(*args, **kwargs):
    yield


async def run_limited[T](
    *coros: Awaitable[T],
    limit: int = 10,
    sem_class: Callable[[int], AsyncContextManager[None]] = lambda limit: Semaphore(limit),
    return_exceptions: bool = True,
) -> list[T]:
    """
    Run a batch of coroutines with a concurrency limit.

    Args:
        coros: An iterable of awaitable objects (coroutines).
        limit: Maximum number of coroutines to run concurrently.
        sem_class: A factory function returning an async context manager for concurrency control.
                   Defaults to a simple Semaphore.
        return_exceptions: Return exceptions as results instead of raising them.

    Returns:
        A list of results, in the same order as the input coroutines.
    """
    semaphore = sem_class(limit)

    async def sem_task(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    return await asyncio.gather(*(sem_task(c) for c in coros), return_exceptions=return_exceptions)


async def aenumerate(aiterable, start=0):
    index = start
    async for value in aiterable:
        yield index, value
        index += 1


AsyncIteratorT = TypeVar("AsyncIteratorT")


async def consume_async_gen(
    agen: AsyncIterator[AsyncIteratorT], handler: Callable[[AsyncIteratorT], Any]
) -> None:
    """
    Consume an async generator and apply `handler` to each yielded item.

    Args:
        agen:      An async generator producing items of type T.
        handler:   A sync function or coroutine callback that processes each item.
    """
    async for item in agen:
        # If handler is async, await it; otherwise call directly
        result = handler(item)
        if asyncio.iscoroutine(result):
            await result


def flatten_lazy(iterable):
    """
    Flatten a nested iterable (list of lists) into a single iterable.

    Args:
        iterable: A nested iterable to flatten

    Yields:
        Individual items from the nested structure
    """
    for item in iterable:
        if isinstance(item, list | tuple):
            yield from item
        else:
            yield item
