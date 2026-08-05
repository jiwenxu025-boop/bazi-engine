"""LLM review results must not alter rule-engine signals."""

import pytest

from bazi_engine.chart import build_chart
from bazi_engine.enums import Dizhi, Tiangan
from bazi_engine.liunian.llm_bridge import (
    _execute_llm_reviews_parallel,
    _execute_llm_reviews_streaming,
    _signals_to_dicts,
)
from bazi_engine.liunian.signal import AnnualScan, EventSignal
from bazi_engine.llm_review import LLMReviewResult


def test_llm_reviews_are_serialized_separately_from_rule_events(monkeypatch):
    import bazi_engine.llm_review as llm_review

    scan = AnnualScan(2026, Tiangan("甲"), Dizhi("子"))
    review = LLMReviewResult(
        year=2026,
        category="事业",
        direction="中性",
        strength=1,
        prediction="模型审阅结果",
        reasoning="测试理由",
    )
    monkeypatch.setattr(llm_review, "call_llm_review", lambda _context: [review])

    _execute_llm_reviews_parallel([scan], [(0, {})])

    data = scan.to_dict()
    assert data["events"] == []
    assert len(data["ai_reviews"]) == 1
    assert data["ai_reviews"][0]["source"] == "llm"


def test_report_traceability_keeps_ai_review_sources_separate(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    monkeypatch.setenv("BAZI_FUSION_ENGINE", "0")
    chart = build_chart("测试", "男", 2007, 8, 26, 20, liunian_range=(2026, 2026))
    chart.annual_scans[0].ai_reviews.append(EventSignal(
        category="事业", direction="中性", strength=1, source="llm",
    ))

    traceability = chart.to_dict()["report_meta"]["traceability"]

    assert traceability["annual_signal_sources"] == ["rule"]
    assert traceability["annual_ai_review_sources"] == ["llm"]


def test_no_signal_ai_review_serializes_status_without_rule_event(monkeypatch):
    import bazi_engine.llm_review as llm_review

    scan = AnnualScan(2026, Tiangan("甲"), Dizhi("子"))
    review = LLMReviewResult(
        year=2026,
        category="桃花",
        direction="中性",
        strength=0,
        prediction="未发现明显信号",
        reasoning="",
        confidence=0,
        review_status="无明显信号",
    )
    monkeypatch.setattr(llm_review, "call_llm_review", lambda _context: [review])

    _execute_llm_reviews_parallel([scan], [(0, {})])

    data = scan.to_dict()
    assert data["events"] == []
    assert data["ai_reviews"] == [
        {
            "category": "桃花",
            "direction": "中性",
            "strength": 0,
            "prediction": "未发现明显信号",
            "triggers": [],
            "notes": [],
            "calibration_refs": [],
            "personality_note": "",
            "source": "llm",
            "review_status": "无明显信号",
        }
    ]


def test_streamed_and_synchronous_ai_review_shapes_match():
    review = LLMReviewResult(
        year=2026,
        category="财运",
        direction="负面",
        strength=1,
        prediction="核对实际收支",
        reasoning="规则层已有财运弱信号",
    )
    scan = AnnualScan(2026, Tiangan("甲"), Dizhi("子"))

    from bazi_engine.liunian.llm_bridge import _review_to_signal

    scan.ai_reviews.append(_review_to_signal(review))

    assert _signals_to_dicts([review]) == scan.to_dict()["ai_reviews"]


def test_multi_year_batch_is_chunked_and_retries_every_missing_year(monkeypatch):
    import bazi_engine.llm_review as llm_review

    years = list(range(2023, 2027))
    scans = [AnnualScan(year, Tiangan("甲"), Dizhi("子")) for year in years]
    contexts = [{"year": year} for year in years]
    batch_sizes = []
    single_years = []
    streamed_tokens = []
    streamed_results = []

    def fake_batch(batch_contexts, on_token=None):
        batch_sizes.append(len(batch_contexts))
        return [[] for _ in batch_contexts]

    def fake_single(context, on_token=None):
        year = context["year"]
        single_years.append(year)
        if on_token:
            on_token("ok")
        return [LLMReviewResult(
            year=year,
            category="事业",
            direction="中性",
            strength=1,
            prediction="逐年回退结果",
            reasoning="批量结果不完整",
        )]

    monkeypatch.setattr(llm_review, "call_llm_batch_review", fake_batch)
    monkeypatch.setattr(llm_review, "call_llm_review", fake_single)

    _execute_llm_reviews_streaming(
        scans,
        list(enumerate(contexts)),
        lambda year, signals: streamed_results.append((year, signals)),
        lambda year, token: streamed_tokens.append((year, token)),
    )

    assert sorted(batch_sizes) == [2, 2]
    assert sorted(single_years) == years
    assert sum(len(scan.ai_reviews) for scan in scans) == len(years)
    assert sorted(year for year, _signals in streamed_results) == years
    assert sorted(streamed_tokens) == [(year, "ok") for year in years]


def test_missing_single_year_fallback_emits_explicit_incomplete_matrix(monkeypatch):
    import bazi_engine.llm_review as llm_review

    years = [2023, 2024, 2025]
    scans = [AnnualScan(year, Tiangan("甲"), Dizhi("子")) for year in years]
    streamed_results = []
    monkeypatch.setattr(
        llm_review,
        "call_llm_batch_review",
        lambda contexts, on_token=None: [[] for _ in contexts],
    )
    monkeypatch.setattr(llm_review, "call_llm_review", lambda _context, on_token=None: [])

    _execute_llm_reviews_streaming(
        scans,
        list(enumerate({"year": year} for year in years)),
        lambda year, signals: streamed_results.append((year, signals)),
    )

    assert sorted(year for year, _signals in streamed_results) == years
    for scan in scans:
        assert len(scan.ai_reviews) == 6
        assert {review.review_status for review in scan.ai_reviews} == {"未完成"}


def test_one_year_empty_review_is_explicit_for_streaming_and_sync(monkeypatch):
    import bazi_engine.llm_review as llm_review

    monkeypatch.setattr(llm_review, "call_llm_review", lambda _context, **_kwargs: [])

    streamed_scan = AnnualScan(2026, Tiangan("甲"), Dizhi("子"))
    streamed_results = []
    _execute_llm_reviews_streaming(
        [streamed_scan],
        [(0, {"year": 2026})],
        lambda year, signals: streamed_results.append((year, signals)),
    )

    sync_scan = AnnualScan(2027, Tiangan("乙"), Dizhi("丑"))
    _execute_llm_reviews_parallel([sync_scan], [(0, {"year": 2027})])

    assert [year for year, _signals in streamed_results] == [2026]
    assert len(streamed_results[0][1]) == 6
    for scan in (streamed_scan, sync_scan):
        assert len(scan.ai_reviews) == 6
        assert {review.review_status for review in scan.ai_reviews} == {"未完成"}


def test_annual_review_triggers_only_when_weak_rule_signals_need_explanation(monkeypatch):
    import bazi_engine.llm_review as llm_review

    monkeypatch.setattr(llm_review, "LLM_REVIEW_ENABLED", True)
    monkeypatch.setattr(llm_review, "DEEPSEEK_KEY", "test-key")
    one_weak = [EventSignal(category="事业", direction="中性", strength=1)]
    two_weak = [*one_weak, EventSignal(category="财运", direction="中性", strength=1)]
    all_strong = [
        EventSignal(category=category, direction="正面", strength=2)
        for category in ("婚嫁", "桃花", "事业", "财运", "健康")
    ]

    assert llm_review.should_invoke_llm(one_weak, 2026, 30)
    assert llm_review.should_invoke_llm(two_weak, 2026, 30)
    assert not llm_review.should_invoke_llm(all_strong, 2026, 30)
    assert not llm_review.should_invoke_llm([], 2026, 30)


def test_build_chart_can_defer_annual_reviews_without_calling_provider(monkeypatch):
    import bazi_engine.liunian.scanner as scanner
    import bazi_engine.llm_review as llm_review

    monkeypatch.setenv("BAZI_LLM_REVIEW", "1")
    monkeypatch.setattr(llm_review, "should_invoke_llm", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        scanner,
        "_execute_llm_reviews_streaming",
        lambda *_args, **_kwargs: pytest.fail("deferred build called streaming review"),
    )
    monkeypatch.setattr(
        scanner,
        "_execute_llm_reviews_parallel",
        lambda *_args, **_kwargs: pytest.fail("deferred build called parallel review"),
    )

    chart = build_chart(
        "测试",
        "男",
        2007,
        8,
        26,
        20,
        liunian_range=(2025, 2026),
        defer_llm=True,
    )

    assert len(chart._pending_llm_tasks) == 2
    assert all(not scan.ai_reviews for scan in chart.annual_scans)
