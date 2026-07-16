"""共享 HTTP 客户端和调用级超时控制。"""
import threading
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager

import httpx

_client: httpx.Client | None = None
_async_client: httpx.AsyncClient | None = None
_client_lock = threading.Lock()


class _TimeoutBoundClient:
    """Apply a timeout to one call without mutating the shared connection pool."""

    def __init__(self, client: httpx.Client, timeout: float):
        self._client = client
        self._timeout = timeout

    def post(self, url: str, **kwargs) -> httpx.Response:
        kwargs.setdefault("timeout", self._timeout)
        return self._client.post(url, **kwargs)

    def stream(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return self._client.stream(method, url, **kwargs)


class _AsyncTimeoutBoundClient:
    """Async counterpart that shares one connection pool across chat streams."""

    def __init__(self, client: httpx.AsyncClient, timeout: float):
        self._client = client
        self._timeout = timeout

    async def post(self, url: str, **kwargs) -> httpx.Response:
        kwargs.setdefault("timeout", self._timeout)
        return await self._client.post(url, **kwargs)

    def stream(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return self._client.stream(method, url, **kwargs)


def _get_client() -> httpx.Client:
    global _client
    with _client_lock:
        if _client is None or _client.is_closed:
            _client = httpx.Client(
                limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
            )
        return _client


def _get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=12, max_keepalive_connections=6),
        )
    return _async_client


def close_shared_client() -> None:
    """Close the connection pool during application shutdown."""
    global _client
    with _client_lock:
        client, _client = _client, None
    if client is not None and not client.is_closed:
        client.close()


async def close_shared_clients() -> None:
    """Close both pools during application shutdown."""
    global _async_client
    close_shared_client()
    async_client, _async_client = _async_client, None
    if async_client is not None and not async_client.is_closed:
        await async_client.aclose()


@contextmanager
def shared_client(timeout: float = 60.0) -> Iterator[_TimeoutBoundClient]:
    """Yield a shared pool with a timeout scoped to this individual request."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    yield _TimeoutBoundClient(_get_client(), timeout)


@asynccontextmanager
async def shared_async_client(timeout: float = 60.0):
    """Yield the async connection pool with a timeout scoped to this request."""
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    yield _AsyncTimeoutBoundClient(_get_async_client(), timeout)
