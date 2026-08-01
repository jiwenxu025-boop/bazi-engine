"""Performance-contract tests for chart streaming and annual AI review."""

import asyncio
import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime


class _FakeChart:
    def __init__(self):
        self.birth_dt = datetime(2000, 1, 1, 12, 0)
        self._pending_llm_tasks = [(0, {"liunian": {"year": 2026}})]
        self.annual_scans = [object()]
        self.personality_result = {"evidence_view": {"status": {}}}
        self.family_result = None
        self.dayun_modulations = [{"period_index": 0}]
        self.dayun_interpretations = None

    def to_dict(self):
        return {
            "personality": {"evidence_view": {"status": {}}},
            "day_master": {"stem": "甲", "wuxing": "木", "yinyang": "阳"},
            "life_stage": "职场",
        }


def _stream(api_module):
    return api_module.stream_chart(
        name="test",
        gender="男",
        year=2000,
        month=1,
        day=1,
        hour=12,
        minute=0,
        city_id=None,
        longitude=None,
        timezone_offset_minutes=None,
        requested_time_mode="auto",
        time_accuracy="minute",
        ln_range=(2026, 2026),
        fav_set=None,
        life_stage="auto",
        hour_confirmed=True,
        practical=False,
    )


def _event_from_chunk(chunk: str):
    line = next((line for line in chunk.splitlines() if line.startswith("data: ")), "")
    payload = line[6:]
    return None if not payload or payload == "[DONE]" else json.loads(payload)


def _install_fake_chart_dependencies(monkeypatch):
    import bazi_engine.api as api_module
    import bazi_engine.liunian.llm_bridge as bridge
    import bazi_engine.llm_review as llm_review
    import bazi_engine.personality_fusion as fusion

    monkeypatch.setenv("BAZI_FUSION_ENGINE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(api_module, "build_chart", lambda **_kwargs: _FakeChart())
    monkeypatch.setattr(api_module, "_record_fusion_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fusion, "build_fusion_data_package", lambda *_args, **_kwargs: {})
    return api_module, bridge, llm_review, fusion


def test_rules_are_emitted_before_three_ai_workers_run_in_parallel(monkeypatch):
    api_module, bridge, llm_review, fusion = _install_fake_chart_dependencies(monkeypatch)
    barrier = threading.Barrier(3)
    starts = {}
    starts_lock = threading.Lock()

    def mark_started(component):
        with starts_lock:
            starts[component] = time.monotonic()
        barrier.wait(timeout=2)

    def fake_annual(_results, _tasks, on_result, _on_token, cancel_event=None):
        assert cancel_event is not None
        mark_started("annual")
        on_result(2026, [])

    def fake_fusion(_package, on_chunk=None, result_metadata=None, cancel_event=None):
        assert cancel_event is not None
        mark_started("fusion")
        if on_chunk:
            on_chunk("画像")
        if result_metadata is not None:
            result_metadata["model"] = "fake"
        return "完整画像"

    def fake_dayun(_chart):
        mark_started("dayun")
        return [{"index": 0, "interpretation": "大运解读"}]

    monkeypatch.setattr(bridge, "_execute_llm_reviews_streaming", fake_annual)
    monkeypatch.setattr(fusion, "generate_fusion_report", fake_fusion)
    monkeypatch.setattr(llm_review, "enrich_dayun_interpretations", fake_dayun)

    async def collect():
        events = []
        async for chunk in _stream(api_module):
            event = _event_from_chunk(chunk)
            if event:
                events.append(event)
        return events

    started_at = time.monotonic()
    events = asyncio.run(collect())
    elapsed = time.monotonic() - started_at
    phases = [event["phase"] for event in events]
    rules_index = phases.index("rules_done")

    assert phases[0] == "started"
    assert rules_index < phases.index("llm_result")
    assert rules_index < phases.index("personality_token")
    assert rules_index < phases.index("dayun_done")
    assert set(starts) == {"annual", "fusion", "dayun"}
    assert max(starts.values()) - min(starts.values()) < 0.5
    assert elapsed < 2


def test_stream_close_signals_running_ai_workers_to_cancel(monkeypatch):
    api_module, bridge, llm_review, fusion = _install_fake_chart_dependencies(monkeypatch)
    annual_started = threading.Event()
    annual_cancelled = threading.Event()
    fusion_started = threading.Event()
    fusion_cancelled = threading.Event()

    def fake_annual(_results, _tasks, _on_result, _on_token, cancel_event=None):
        annual_started.set()
        assert cancel_event is not None
        cancel_event.wait(timeout=2)
        if cancel_event.is_set():
            annual_cancelled.set()

    def fake_fusion(_package, on_chunk=None, result_metadata=None, cancel_event=None):
        fusion_started.set()
        if on_chunk:
            on_chunk("首段")
        assert cancel_event is not None
        cancel_event.wait(timeout=2)
        if cancel_event.is_set():
            fusion_cancelled.set()
        return None

    monkeypatch.setattr(bridge, "_execute_llm_reviews_streaming", fake_annual)
    monkeypatch.setattr(fusion, "generate_fusion_report", fake_fusion)
    monkeypatch.setattr(llm_review, "enrich_dayun_interpretations", lambda _chart: [])

    async def close_after_ai_starts():
        stream = _stream(api_module)
        assert _event_from_chunk(await anext(stream))["phase"] == "started"
        assert _event_from_chunk(await anext(stream))["phase"] == "rules_done"
        await asyncio.wait_for(anext(stream), timeout=1)
        deadline = time.monotonic() + 1
        while not (annual_started.is_set() and fusion_started.is_set()):
            assert time.monotonic() < deadline
            await asyncio.sleep(0.01)
        await stream.aclose()

    asyncio.run(close_after_ai_starts())

    assert annual_cancelled.wait(timeout=1)
    assert fusion_cancelled.wait(timeout=1)


def test_annual_review_uses_dedicated_model_and_bounded_output(monkeypatch):
    import bazi_engine.llm_review as llm_review

    payloads = []

    class FakeResponse:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def iter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"{}"},"finish_reason":"stop"}]}'
            yield "data: [DONE]"

    class FakeClient:
        def stream(self, _method, _url, json=None, headers=None):
            del headers
            payloads.append(json)
            return FakeResponse()

    @contextmanager
    def fake_shared_client(_timeout):
        yield FakeClient()

    monkeypatch.setattr(llm_review, "DEEPSEEK_KEY", "test-key")
    monkeypatch.setattr(llm_review, "DEEPSEEK_REVIEW_MODEL", "review-fast")
    monkeypatch.setattr(llm_review, "_ANNUAL_REVIEW_MAX_OUTPUT_TOKENS", 2048)
    monkeypatch.setattr(llm_review, "_ANNUAL_BATCH_MAX_OUTPUT_TOKENS", 3072)
    monkeypatch.setattr(llm_review, "is_available", lambda: True)
    monkeypatch.setattr(llm_review, "shared_client", fake_shared_client)
    monkeypatch.setattr(llm_review, "build_review_prompt", lambda _ctx: "prompt")

    llm_review.call_llm_review({"liunian": {"year": 2026}})
    natal = {
        "pillars": "甲子 乙丑 丙寅 丁卯",
        "day_master": "丙",
        "pattern": "测试格",
        "strength": "中和",
        "favorable_wuxing": [],
        "harmful_wuxing": [],
        "favorable": [],
        "harmful": [],
        "tiaohou": {},
    }
    contexts = [
        {
            "natal": natal,
            "liunian": {"year": year, "stem": "甲", "branch": "子", "age": 30},
            "dayun": {},
            "rule_signals": [],
            "year_features": {},
        }
        for year in (2026, 2027)
    ]
    llm_review.call_llm_batch_review(contexts)

    assert [payload["model"] for payload in payloads] == ["review-fast", "review-fast"]
    assert [payload["max_tokens"] for payload in payloads] == [2048, 3072]
