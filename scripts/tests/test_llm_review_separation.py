"""LLM review results must not alter rule-engine signals."""

from bazi_engine.chart import build_chart
from bazi_engine.enums import Dizhi, Tiangan
from bazi_engine.liunian.llm_bridge import _execute_llm_reviews_parallel
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
