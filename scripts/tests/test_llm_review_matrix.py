"""LLM annual review must cover each configured category explicitly."""

import json

from bazi_engine.chart import build_chart
from bazi_engine.liunian.signal import EventSignal, EvidenceItem
from bazi_engine.llm_review import (
    _parse_batch_response,
    _parse_review_response,
    build_review_context,
    build_review_prompt,
)


def _review_context(year: int = 2027) -> dict:
    return {
        "natal": {
            "pillars": "丁亥 戊申 壬辰 庚戌",
            "day_master": "壬",
            "pattern": "偏印格",
            "strength": "偏强",
            "favorable": ["财星"],
            "harmful": ["比劫"],
            "favorable_wuxing": ["火"],
            "harmful_wuxing": ["水"],
            "key_interactions": [],
            "tiaohou": {},
        },
        "dayun": {"stem": "庚", "branch": "戌", "baseline_offset": 0},
        "liunian": {"year": year, "age": 20, "stem": "丁", "branch": "未"},
        "rule_signals": [],
        "year_features": {},
    }


def _matrix(**overrides) -> dict:
    values = {"婚嫁": 0, "桃花": 0, "事业": 0, "财运": 0, "健康": 0, "搬迁": 0}
    values.update(overrides)
    return values


def _positive_event(category: str) -> dict:
    return {
        "category": category,
        "direction": "正面",
        "strength": 2,
        "prediction": "人际吸引力增强",
        "reasoning": "多项关系特征同时出现",
        "confidence": 0.8,
    }


def test_review_prompt_requires_complete_compact_category_matrix():
    prompt = build_review_prompt(_review_context())

    assert "必须逐项审阅婚嫁、桃花、事业、财运、健康、搬迁六类" in prompt
    assert '"category_matrix"' in prompt
    for category in ("婚嫁", "桃花", "事业", "财运", "健康", "搬迁"):
        assert f'"{category}"' in prompt


def test_review_context_carries_decision_policy_and_rule_evidence():
    chart = build_chart(
        name="LLM上下文", gender="男",
        year=2007, month=8, day=26, hour=20,
    )
    signal = EventSignal(
        category="财运", direction="正面", strength=1,
        evidence=[EvidenceItem(
            rule="wealth_rule", layers=("原局", "流年"),
            pillars=("日柱", "流年"), relation="生克", detail="财星透干",
        )],
        conflicts=["调候与扶抑未完全一致"],
    )

    ctx = build_review_context(
        chart.to_dict(), 2026, 19, "丙", "午", None, None,
        [signal], year_features={"关系星透干": "偏财"},
    )
    prompt = build_review_prompt(ctx)

    assert ctx["natal"]["decision_policy"]["precedence"]
    assert ctx["rule_signals"][0]["evidence"][0]["pillars"] == ["日柱", "流年"]
    assert ctx["rule_signals"][0]["conflicts"]
    assert "不得自行重算三合、藏干、强弱或喜忌" in prompt


def test_single_response_keeps_positive_and_explicit_no_signal_states():
    content = json.dumps(
        {
            "category_matrix": _matrix(桃花=1),
            "events": [_positive_event("桃花")],
        },
        ensure_ascii=False,
    )

    results = _parse_review_response(content, 2027)
    statuses = {result.category: result.review_status for result in results}

    assert len(results) == 6
    assert statuses["桃花"] == "有信号"
    assert statuses["婚嫁"] == "无明显信号"
    assert next(result for result in results if result.category == "婚嫁").strength == 0


def test_incomplete_matrix_is_not_misreported_as_no_signal():
    matrix = _matrix()
    matrix.pop("健康")

    results = _parse_review_response(
        json.dumps({"category_matrix": matrix, "events": []}, ensure_ascii=False),
        2027,
    )
    statuses = {result.category: result.review_status for result in results}

    assert statuses["健康"] == "未完成"
    assert statuses["婚嫁"] == "无明显信号"


def test_matrix_response_ignores_categories_outside_fixed_review_scope():
    content = json.dumps(
        {
            "category_matrix": _matrix(),
            "events": [_positive_event("人际")],
        },
        ensure_ascii=False,
    )

    results = _parse_review_response(content, 2027)

    assert len(results) == 6
    assert {result.category for result in results} == set(_matrix())


def test_legacy_event_only_response_remains_compatible():
    results = _parse_review_response(
        json.dumps({"events": [_positive_event("事业")]}, ensure_ascii=False),
        2027,
    )

    assert len(results) == 1
    assert results[0].category == "事业"
    assert results[0].review_status == "有信号"


def test_batch_response_builds_a_matrix_for_each_year():
    ctxs = [_review_context(2027), _review_context(2029)]
    content = json.dumps(
        {
            "years": [
                {
                    "year": 2027,
                    "category_matrix": _matrix(桃花=1),
                    "events": [_positive_event("桃花")],
                },
                {"year": 2029, "category_matrix": _matrix(), "events": []},
            ]
        },
        ensure_ascii=False,
    )

    results = _parse_batch_response(content, ctxs)

    assert [len(year_results) for year_results in results] == [6, 6]
    assert any(result.category == "桃花" and result.review_status == "有信号" for result in results[0])
    assert all(result.review_status == "无明显信号" for result in results[1])


def test_positive_review_text_uses_larger_limits_and_complete_sentence_boundaries():
    prediction = "甲" * 70 + "。" + "乙" * 70 + "。"
    reasoning = "丙" * 150 + "。" + "丁" * 150 + "。"
    event = _positive_event("事业")
    event["prediction"] = prediction
    event["reasoning"] = reasoning

    results = _parse_review_response(
        json.dumps(
            {"category_matrix": _matrix(事业=1), "events": [event]},
            ensure_ascii=False,
        ),
        2027,
    )
    review = next(result for result in results if result.category == "事业")

    assert review.prediction == "甲" * 70 + "。"
    assert len(review.prediction) <= 120
    assert review.reasoning == "丙" * 150 + "。"
    assert len(review.reasoning) <= 240
    assert len(review.triggers[0]) <= 120
    assert review.triggers[0].endswith("…")
