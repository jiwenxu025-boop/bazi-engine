"""Small, bounded bridge for sending worker events to an async SSE generator."""

import asyncio
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)


class StreamEventQueue:
    """Bound worker-to-event-loop events and stop accepting them after cancellation."""

    def __init__(self, loop: asyncio.AbstractEventLoop, *, name: str) -> None:
        self._loop = loop
        self._name = name
        self._queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue(
            maxsize=max(1, int(os.getenv("BAZI_STREAM_EVENT_QUEUE_MAX", "128")))
        )
        self._closed = threading.Event()
        self._overflowed = threading.Event()

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    @property
    def overflowed(self) -> bool:
        return self._overflowed.is_set()

    def publish(self, event_type: str, payload: Any) -> None:
        """Schedule a non-blocking event offer from a synchronous worker callback."""
        if not self._closed.is_set():
            self._loop.call_soon_threadsafe(self._offer, event_type, payload)

    def _offer(self, event_type: str, payload: Any) -> None:
        if self._closed.is_set():
            return
        try:
            self._queue.put_nowait((event_type, payload))
        except asyncio.QueueFull:
            self._overflowed.set()
            self._closed.set()
            logger.warning("SSE event queue overflowed stream=%s", self._name)

    async def get(self, timeout: float) -> tuple[str, Any]:
        return await asyncio.wait_for(self._queue.get(), timeout=timeout)

    def close(self) -> None:
        self._closed.set()
