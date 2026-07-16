"""Application-scoped worker resources for blocking engine and LLM tasks."""
import asyncio
import concurrent.futures
import os
import threading
from collections.abc import Callable

_executor: concurrent.futures.ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _max_workers() -> int:
    return max(1, int(os.getenv("BAZI_MAX_BLOCKING_WORKERS", "4")))


def get_blocking_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Return the shared bounded executor, recreating it after application shutdown."""
    global _executor
    with _executor_lock:
        if _executor is None or getattr(_executor, "_shutdown", False):
            _executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=_max_workers(),
                thread_name_prefix="bazi-worker",
            )
        return _executor


def submit_blocking(loop: asyncio.AbstractEventLoop, function: Callable, *args):
    """Run blocking work in the application-scoped executor."""
    return loop.run_in_executor(get_blocking_executor(), function, *args)


def close_blocking_executor() -> None:
    """Stop accepting queued work during application shutdown."""
    global _executor
    with _executor_lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)
