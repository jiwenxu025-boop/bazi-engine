"""LLM review results must not alter rule-engine signals."""

from bazi_engine.chart import build_chart
from bazi_engine.enums import Dizhi, Tiangan
from bazi_engine.liunian.llm_bridge import (
    _execute_llm_reviews_parallel,
    _execute_llm_reviews_streaming,
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


def test_multi_year_batch_is_chunked_and_empty_results_fall_back(monkeypatch):
    import bazi_engine.llm_review as llm_review

    years = list(range(2023, 2028))
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
    assert all(len(scan.ai_reviews) == 1 for scan in scans)
    assert sorted(year for year, _signals in streamed_results) == years
    assert sorted(streamed_tokens) == [(year, "ok") for year in years]
