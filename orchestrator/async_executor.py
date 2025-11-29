"""Async execution utilities for concurrent agent operations."""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, TypeVar

from .logging_config import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


class AsyncExecutor:
    """Execute tasks asynchronously with configurable concurrency."""

    def __init__(self, max_workers: int = 3) -> None:
        """
        Initialize async executor.

        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def execute_parallel(
        self,
        tasks: List[Callable[[], T]],
        timeout: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute tasks in parallel.

        Args:
            tasks: List of callable tasks
            timeout: Timeout for each task in seconds

        Returns:
            List of results with status
        """
        futures = []
        results = []

        for i, task in enumerate(tasks):
            future = self.executor.submit(task)
            futures.append((i, task, future))

        for i, task, future in futures:
            try:
                result = future.result(timeout=timeout)
                results.append(
                    {
                        "index": i,
                        "success": True,
                        "result": result,
                        "error": None,
                    }
                )
            except Exception as e:
                logger.error(f"Task {i} failed: {e}", exc_info=True)
                results.append(
                    {
                        "index": i,
                        "success": False,
                        "result": None,
                        "error": str(e),
                    }
                )

        return results

    def execute_sequential(
        self,
        tasks: List[Callable[[], T]],
        stop_on_error: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Execute tasks sequentially.

        Args:
            tasks: List of callable tasks
            stop_on_error: Stop execution on first error

        Returns:
            List of results with status
        """
        results = []

        for i, task in enumerate(tasks):
            try:
                result = task()
                results.append(
                    {
                        "index": i,
                        "success": True,
                        "result": result,
                        "error": None,
                    }
                )
            except Exception as e:
                logger.error(f"Task {i} failed: {e}", exc_info=True)
                results.append(
                    {
                        "index": i,
                        "success": False,
                        "result": None,
                        "error": str(e),
                    }
                )

                if stop_on_error:
                    break

        return results

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown executor."""
        self.executor.shutdown(wait=wait)

    def __enter__(self) -> "AsyncExecutor":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.shutdown()


class TaskQueue:
    """Simple task queue for managing agent tasks."""

    def __init__(self, max_size: int = 100) -> None:
        """
        Initialize task queue.

        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self.queue: List[Dict[str, Any]] = []

    def enqueue(self, task: Dict[str, Any]) -> bool:
        """
        Add task to queue.

        Args:
            task: Task dictionary

        Returns:
            True if enqueued, False if queue full
        """
        if len(self.queue) >= self.max_size:
            return False

        self.queue.append(task)
        return True

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        Remove and return next task from queue.

        Returns:
            Task dictionary or None if queue empty
        """
        if not self.queue:
            return None

        return self.queue.pop(0)

    def peek(self) -> Optional[Dict[str, Any]]:
        """
        View next task without removing it.

        Returns:
            Task dictionary or None if queue empty
        """
        if not self.queue:
            return None

        return self.queue[0]

    def size(self) -> int:
        """Get queue size."""
        return len(self.queue)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.queue) == 0

    def is_full(self) -> bool:
        """Check if queue is full."""
        return len(self.queue) >= self.max_size

    def clear(self) -> None:
        """Clear all tasks from queue."""
        self.queue.clear()


async def run_async_task(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a synchronous function asynchronously.

    Args:
        func: Function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


async def gather_with_concurrency(
    n: int,
    *tasks: Callable[[], T],
) -> List[T]:
    """
    Gather tasks with limited concurrency.

    Args:
        n: Maximum concurrent tasks
        *tasks: Tasks to execute

    Returns:
        List of results
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task: Callable[[], T]) -> T:
        async with semaphore:
            return await run_async_task(task)

    return await asyncio.gather(*(sem_task(task) for task in tasks))
