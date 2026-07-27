import asyncio
import itertools

_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
_counter = itertools.count()

PRIORITY_PREMIUM = 0
PRIORITY_FREE = 1


async def submit(priority: int, coro) -> asyncio.Future:
    """Кладёт корутину в очередь и возвращает Future с результатом её выполнения."""
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    seq = next(_counter)
    await _queue.put((priority, seq, coro, fut))
    return fut


async def _worker():
    while True:
        priority, seq, coro, fut = await _queue.get()
        try:
            result = await coro
            if not fut.done():
                fut.set_result(result)
        except Exception as e:
            if not fut.done():
                fut.set_exception(e)
        finally:
            _queue.task_done()


def start_workers(count: int):
    for _ in range(count):
        asyncio.create_task(_worker())


def queue_size() -> int:
    return _queue.qsize()
