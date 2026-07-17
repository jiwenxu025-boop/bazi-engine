"""病药组合候选文案的安全边界与数据契约。"""

import pytest

from bazi_engine.personality_analysis.bingyao import detect_bingyao_combos

_ADJACENT_PILLARS = [
    {"ten_god": "偏官", "hidden_ten_gods": []},
    {"ten_god": "正印", "hidden_ten_gods": []},
]

_CASES = [
    ("伤官见官", {"伤官": 3.0, "正官": 3.0}, "中和", [], 1,
     {"伤官": 3.0, "正官": 3.0}),
    ("食神制杀", {"偏官": 6.0, "食神": 3.0}, "中和", [], 1,
     {"七杀": 6.0, "食伤": 3.0, "食神": 3.0, "伤官": 0}),
    ("伤官驾杀", {"偏官": 6.0, "伤官": 3.0}, "中和", [], 1,
     {"七杀": 6.0, "食伤": 3.0, "食神": 0, "伤官": 3.0}),
    ("比劫夺财", {"比肩": 6.0}, "中和", [], 2,
     {"比劫": 6.0, "财星": 0, "官杀": 0}),
    ("财多身弱", {"正财": 6.0}, "偏弱", [], 1,
     {"财星": 6.0, "印星": 0, "比劫": 0, "身强弱": "偏弱"}),
    ("杀印相生", {"偏官": 6.0, "正印": 3.0}, "中和", _ADJACENT_PILLARS, 1,
     {"七杀": 6.0, "印星": 3.0, "贴身": True}),
    ("枭神夺食", {"偏印": 6.0, "食神": 3.0}, "中和", [], 1,
     {"偏印": 6.0, "食神": 3.0}),
    ("印重身滞", {"正印": 8.0}, "中和", [], 1,
     {"印星": 8.0, "食伤": 0}),
    ("财破印", {"正财": 5.0, "正印": 3.0}, "中和", [], 2,
     {"财星": 5.0, "印星": 3.0}),
    ("食伤过旺泄身", {"食神": 8.0}, "偏弱", [], 1,
     {"食伤": 8.0, "食神": 8.0, "伤官": 0, "身强弱": "偏弱"}),
    ("官杀混杂", {"正官": 3.0, "偏官": 3.0}, "中和", [], 2,
     {"正官": 3.0, "七杀": 3.0}),
]

_FORBIDDEN_DIRECTIVE_TERMS = (
    "强制约束",
    "神经系统",
    "战神",
    "慢性休克",
    "唯一破局",
    "绝对禁止",
    "选择困难症",
    "被害感",
    "不输出会死",
    "burnout",
    "必须",
    "立刻",
    "铁律",
    "每天运动",
    "生存必需品",
    "独立开发者",
    "创意总监",
    "大公司",
    "技术咨询",
    "产品策划",
    "付费对赌",
)


def _find_combo(name, scores, strength, pillars):
    combos = detect_bingyao_combos(scores, strength, "测试格局", pillars)
    return next(combo for combo in combos if combo["combo"] == name)


@pytest.mark.parametrize(
    ("name", "scores", "strength", "pillars", "priority", "evidence"),
    _CASES,
)
def test_bingyao_candidates_preserve_priority_and_evidence(
    name, scores, strength, pillars, priority, evidence,
):
    combo = _find_combo(name, scores, strength, pillars)

    assert combo["priority"] == priority
    assert combo["evidence"] == evidence
    assert combo["evidence_status"] == "heuristic_candidate"


@pytest.mark.parametrize(
    ("name", "scores", "strength", "pillars", "_priority", "_evidence"),
    _CASES,
)
def test_bingyao_directives_are_conditional_and_non_diagnostic(
    name, scores, strength, pillars, _priority, _evidence,
):
    directive = _find_combo(name, scores, strength, pillars)["directive"]

    assert directive.startswith("规则候选说明：")
    assert "可能" in directive
    assert "需结合" in directive
    assert "不直接推断" in directive
    assert len(directive) <= 110
    for forbidden in _FORBIDDEN_DIRECTIVE_TERMS:
        assert forbidden not in directive


def test_bingyao_trigger_boundary_is_unchanged_for_present_threshold():
    below = detect_bingyao_combos(
        {"伤官": 2.9, "正官": 3.0}, "中和", "测试格局", [],
    )
    at_threshold = detect_bingyao_combos(
        {"伤官": 3.0, "正官": 3.0}, "中和", "测试格局", [],
    )

    assert all(combo["combo"] != "伤官见官" for combo in below)
    assert any(combo["combo"] == "伤官见官" for combo in at_threshold)
