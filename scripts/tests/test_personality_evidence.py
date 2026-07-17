"""Evidence-contract and field-semantics regression tests."""

from bazi_engine.personality_analysis.evidence import (
    build_fusion_trait_signals,
    build_personality_evidence_view,
    build_trait_signal_evidence,
    normalize_strength_label,
    weighted_score_level,
)
from bazi_engine.personality_analysis.main import (
    _canonical_pattern_name,
    _compute_decision_score,
    _pattern_is_favorable,
)


def test_weighted_score_levels_use_one_unbounded_additive_scale():
    assert weighted_score_level(1.9) == "较弱"
    assert weighted_score_level(2.0) == "中等"
    assert weighted_score_level(4.9) == "中等"
    assert weighted_score_level(5.0) == "较强"
    assert weighted_score_level(18.0) == "较强"


def test_trait_signal_evidence_does_not_band_modifiers_or_differences():
    evidence = build_trait_signal_evidence({
        "决策": {
            "果断度_七杀": 6.0,
            "战略思维": 0,
            "综合倾向": "分析后决策",
        },
        "事业": {
            "体制_管理": 8.0,
            "技术_创意": 7.5,
            "主导方向": "体制/管理",
            "次要方向": "技术/创意",
            "方向差距": 0.5,
        },
    })

    decision = evidence["决策"]
    assert decision["signals"] == [{
        "label": "果断度_七杀",
        "display_label": "推进与决断",
        "kind": "weighted_score",
        "value": 6.0,
        "level": "较强",
    }]
    assert "战略思维" not in str(decision)

    career = evidence["事业"]
    assert career["comparison"] == "方向接近"
    assert all(signal["kind"] == "relative_score" for signal in career["signals"])
    assert [signal["label"] for signal in career["signals"]] == ["体制_管理", "技术_创意"]
    assert "较弱" not in str(career)


def test_fusion_signals_are_qualitative_and_exclude_pending_rules():
    package = build_fusion_trait_signals({
        "感情": {
            "责任感_官杀": 6.0,
            "夫妻宫状态": "冲",
            "桃花坐日支": False,
        },
        "财富观": {"欲望_财星": 4.0},
    })

    assert package["感情"] == {"强度信号": {"关系责任": "较强"}}
    assert package["财富观"] == {"强度信号": {"资源目标": "中等"}}
    assert "夫妻宫" not in str(package)
    assert "桃花" not in str(package)


def test_evidence_view_explains_score_scope_and_components():
    view = build_personality_evidence_view({
        "strength_label": "偏强（7.2分）",
        "pattern_validation": {"status": "成格"},
        "weighted_shishen": {
            "scores": {"偏印": 8.0},
            "breakdown": {
                "偏印": {"tougan": 3.0, "hidden": 2.0, "month_bonus": 3.0},
            },
            "scoring": {
                "kind": "unbounded_additive",
                "comparison_scope": "absolute_engine_heuristic",
                "ranking_scope": "within_chart_only",
                "banding_scope": "fixed_engine_thresholds",
                "source_status": "engineering_heuristic",
            },
        },
    }, pattern="偏印格")

    assert view["score_scale"]["comparison_scope"] == "absolute_engine_heuristic"
    assert view["score_scale"]["ranking_scope"] == "within_chart_only"
    assert view["score_scale"]["source_status"] == "engineering_heuristic"
    assert view["status"]["pattern"] == "偏印格"
    assert view["weighted_scores"][0] == {
        "name": "偏印",
        "score": 8.0,
        "level": "较强",
        "breakdown": {"tougan": 3.0, "hidden": 2.0, "month_bonus": 3.0},
    }


def test_decision_score_is_continuous_when_shangguan_crosses_shishen():
    before = _compute_decision_score(0.0, 3.0, 3.0, 0.0)
    after = _compute_decision_score(0.0, 3.1, 3.0, 0.0)

    assert before == 3.9
    assert round(after - before, 6) == 0.1


def test_career_candidates_are_sorted_by_relative_score():
    evidence = build_trait_signal_evidence({
        "事业": {
            "体制_管理": 2.0,
            "商业_经营": 8.0,
            "技术_创意": 6.0,
            "主导方向": "商业/经营",
        }
    })

    assert [signal["display_label"] for signal in evidence["事业"]["signals"]] == [
        "商业经营",
        "技术创意",
        "组织管理",
    ]
    assert build_fusion_trait_signals({"事业": {
        "体制_管理": 2.0,
        "商业_经营": 8.0,
        "技术_创意": 6.0,
    }})["事业"]["候选方向排序"] == ["商业经营", "技术创意", "组织管理"]


def test_strength_label_and_pattern_aliases_do_not_leak_or_misclassify():
    verbose = "极弱（0.8分）。现实中容易表现为：对压力敏感、需要外力推动。"

    assert normalize_strength_label(verbose) == "极弱（0.8分）"
    assert _pattern_is_favorable("七杀格", ["偏官"]) is False
    assert _pattern_is_favorable("偏官格", ["偏官"]) is False
    assert _pattern_is_favorable("建禄格", ["比肩"]) is False
    assert _pattern_is_favorable("羊刃格", ["劫财"]) is False
    assert _pattern_is_favorable("正印格", ["偏官"]) is True
    assert _canonical_pattern_name("偏官格") == "七杀格"
