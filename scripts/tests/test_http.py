"""Shared HTTP client lifecycle and timeout tests."""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient


def test_shared_client_keeps_timeouts_scoped_to_each_request(monkeypatch):
    import bazi_engine._http as http_module

    seen_timeouts = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_timeouts.append(request.extensions["timeout"])
        return httpx.Response(200, json={"ok": True})

    raw_client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(http_module, "_client", raw_client)

    with http_module.shared_client(5.0) as client:
        assert client.post("https://example.test/first").status_code == 200
    with http_module.shared_client(12.0) as client:
        assert client.post("https://example.test/second").status_code == 200

    assert seen_timeouts[0]["read"] == 5.0
    assert seen_timeouts[1]["read"] == 12.0
    http_module.close_shared_client()


def test_shared_client_rejects_non_positive_timeout():
    import bazi_engine._http as http_module

    with pytest.raises(ValueError, match="timeout must be positive"), http_module.shared_client(0):
        pass


def test_api_lifespan_closes_shared_http_client(monkeypatch):
    import bazi_engine._http as http_module
    from bazi_engine.api import app

    raw_client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(200)))
    raw_async_client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: httpx.Response(200)))
    monkeypatch.setattr(http_module, "_client", raw_client)
    monkeypatch.setattr(http_module, "_async_client", raw_async_client)

    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200

    assert raw_client.is_closed
    assert raw_async_client.is_closed


def test_shared_async_client_keeps_timeouts_scoped_to_each_request(monkeypatch):
    import bazi_engine._http as http_module

    seen_timeouts = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_timeouts.append(request.extensions["timeout"])
        return httpx.Response(200, json={"ok": True})

    raw_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(http_module, "_async_client", raw_client)

    async def make_calls():
        async with http_module.shared_async_client(7.0) as client:
            assert (await client.post("https://example.test/first")).status_code == 200
        async with http_module.shared_async_client(13.0) as client:
            assert (await client.post("https://example.test/second")).status_code == 200

    asyncio.run(make_calls())

    assert seen_timeouts[0]["read"] == 7.0
    assert seen_timeouts[1]["read"] == 13.0
    asyncio.run(http_module.close_shared_clients())
