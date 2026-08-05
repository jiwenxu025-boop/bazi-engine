"""LLM annual review must cover each configured category explicitly."""

import json

from bazi_engine.chart import build_chart
from bazi_engine.enums import Dizhi, Tiangan
from bazi_engine.liunian.features import _extract_year_features
from bazi_engine.liunian.signal import EventSignal, EvidenceItem
from bazi_engine.llm_review import (
    _enforce_relationship_review_policy,
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
    assert "不得新增规则层没有的事件类别" in prompt
    assert "慢性病发作" not in prompt
    assert "被裁员" not in prompt


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
    assert "字段缺失表示本年没有该项证据" in prompt
    assert "不得把当前婚恋状态本身当作桃花或婚嫁证据" in prompt


def test_inactive_relationship_spirits_are_not_exposed_as_ai_evidence():
    features = _extract_year_features(
        Tiangan.戊,
        Dizhi.申,
        Dizhi.亥,
        Dizhi.辰,
        Tiangan.壬,
        "男",
        Tiangan.丙,
        Dizhi.午,
    )

    assert "红鸾" not in features
    assert "天喜" not in features
    assert "天喜合动" not in features
    assert "桃花" not in features


def test_triggered_relationship_spirit_remains_ai_evidence():
    features = _extract_year_features(
        Tiangan.丙,
        Dizhi.午,
        Dizhi.亥,
        Dizhi.辰,
        Tiangan.壬,
        "男",
        Tiangan.丙,
        Dizhi.午,
    )

    assert "天喜" not in features
    assert "天喜合动" in features


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


def test_ai_cannot_upgrade_taohua_into_hunjia_without_rule_signal():
    results = [_positive_event("婚嫁")]
    parsed = _parse_review_response(
        json.dumps({"events": results}, ensure_ascii=False), 2027,
    )
    constrained = _enforce_relationship_review_policy(
        parsed,
        {"rule_signals": [], "relationship_context": {"state": "unknown"}},
    )
    marriage = next(result for result in constrained if result.category == "婚嫁")
    assert marriage.review_status == "无明显信号"
    assert marriage.strength == 0


def test_ai_cannot_create_or_reverse_non_relationship_rule_signals():
    parsed = _parse_review_response(
        json.dumps({
            "category_matrix": _matrix(事业=1, 财运=1),
            "events": [
                _positive_event("事业"),
                _positive_event("财运"),
            ],
        }, ensure_ascii=False),
        2027,
    )
    constrained = _enforce_relationship_review_policy(
        parsed,
        {
            "rule_signals": [
                {"category": "财运", "direction": "负面", "strength": 1},
            ],
            "relationship_context": {"state": "unknown"},
        },
    )

    career = next(result for result in constrained if result.category == "事业")
    wealth = next(result for result in constrained if result.category == "财运")
    assert career.review_status == "无明显信号"
    assert career.strength == 0
    assert wealth.review_status == "有信号"
    assert wealth.direction == "负面"
    assert wealth.strength == 1


def test_ai_specific_health_and_career_claims_fall_back_to_rule_text():
    unsafe_health = _positive_event("健康")
    unsafe_health.update({
        "direction": "负面",
        "prediction": "今年会确诊疾病并做手术",
        "reasoning": "羊刃说明会住院",
    })
    unsafe_career = _positive_event("事业")
    unsafe_career.update({
        "direction": "负面",
        "prediction": "今年一定会被裁员",
        "reasoning": "伤官意味着失业",
    })
    parsed = _parse_review_response(
        json.dumps({"events": [unsafe_health, unsafe_career]}, ensure_ascii=False),
        2027,
    )

    constrained = _enforce_relationship_review_policy(
        parsed,
        {
            "rule_signals": [
                {
                    "category": "健康", "direction": "负面", "strength": 1,
                    "prediction": "留意作息、运动和出行安排",
                },
                {
                    "category": "事业", "direction": "负面", "strength": 1,
                    "prediction": "工作调整主题出现，需结合现实安排核对",
                },
            ],
            "relationship_context": {"state": "unknown"},
        },
    )

    combined = " ".join(
        f"{result.prediction} {result.reasoning} {' '.join(result.triggers)}"
        for result in constrained
    )
    for forbidden in ("确诊", "疾病", "手术", "住院", "裁员", "失业", "一定会"):
        assert forbidden not in combined
    assert "留意作息、运动和出行安排" in combined
    assert "工作调整主题出现" in combined


def test_rule_and_ai_context_do_not_reuse_predicted_relationship_state(monkeypatch):
    import bazi_engine.llm_review as llm_review

    monkeypatch.setenv("BAZI_LLM_REVIEW", "1")
    monkeypatch.setattr(llm_review, "LLM_REVIEW_ENABLED", True)
    monkeypatch.setattr(llm_review, "DEEPSEEK_KEY", "test-key")
    monkeypatch.setattr(llm_review, "should_invoke_llm", lambda *_args, **_kwargs: True)
    chart = build_chart(
        name="状态回灌回归",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        liunian_range=(2026, 2030),
        relationship_status="single",
        defer_llm=True,
    )

    contexts = {
        chart.annual_scans[index].year: context
        for index, context in chart._pending_llm_tasks
    }
    assert chart.annual_scans[0].relationship_state == "single"
    assert all(
        scan.relationship_state == "unknown"
        for scan in chart.annual_scans[1:]
    )
    assert contexts[2026]["relationship_context"]["state"] == "single"
    assert all(
        contexts[year]["relationship_context"]["state"] == "unknown"
        for year in (2027, 2028, 2029, 2030)
    )


def test_ai_context_uses_final_rule_signals_after_post_processing(monkeypatch):
    import bazi_engine.llm_review as llm_review

    monkeypatch.setenv("BAZI_LLM_REVIEW", "1")
    monkeypatch.setattr(llm_review, "LLM_REVIEW_ENABLED", True)
    monkeypatch.setattr(llm_review, "DEEPSEEK_KEY", "test-key")
    monkeypatch.setattr(llm_review, "should_invoke_llm", lambda *_args, **_kwargs: True)
    chart = build_chart(
        name="最终规则上下文",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        liunian_range=(2026, 2030),
        defer_llm=True,
    )

    contexts = {
        chart.annual_scans[index].year: context
        for index, context in chart._pending_llm_tasks
    }
    for scan in chart.annual_scans:
        expected = [
            {
                "category": event.category,
                "direction": event.direction,
                "strength": event.strength,
                "prediction": event.prediction,
                "triggers": event.triggers[:5],
                "evidence": [item.to_dict() for item in event.evidence[:5]],
                "conflicts": event.conflicts[:5],
            }
            for event in scan.events
        ]
        assert contexts[scan.year]["rule_signals"] == expected


def test_ai_marriage_wording_is_state_aware_for_married_users():
    parsed = _parse_review_response(
        json.dumps({"events": [_positive_event("婚嫁")]}, ensure_ascii=False), 2029,
    )
    constrained = _enforce_relationship_review_policy(
        parsed,
        {
            "rule_signals": [{"category": "婚嫁", "strength": 3}],
            "relationship_context": {"state": "married", "phase": "peak"},
        },
    )
    marriage = next(result for result in constrained if result.category == "婚嫁")
    assert "再次结婚" in marriage.prediction


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
