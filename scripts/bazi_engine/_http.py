"""共享 HTTP 客户端 — 复用连接池，避免每个模块各自创建"""
from contextlib import contextmanager

import httpx

_client: httpx.Client | None = None


@contextmanager
def shared_client(timeout: float = 60.0):
    """获取共享的 httpx.Client（懒加载，单例，contextmanager 兼容 with 语句）"""
    global _client
    if _client is None:
        _client = httpx.Client(timeout=timeout)
    yield _client
