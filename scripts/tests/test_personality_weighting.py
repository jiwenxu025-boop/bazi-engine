"""Auditable personality weight report tests."""

import pytest

from bazi_engine._constants import DIZHI_LIUHE
from bazi_engine.interactions import find_dizhi_liuhe
from bazi_engine.personality_analysis.constants import (
    HIDDEN_WEIGHTS,
    MONTH_MULTIPLIER,
    SAME_PILLAR_BONUS,
    TOUGAN_WEIGHT,
)
from bazi_engine.personality_analysis.weighting import (
    _compute_weighted_shishen,
    get_weighted_shishen_report,
)

PILLARS = [
    {
        "pillar_type": "年柱",
        "stem": "戊",
        "branch": "丑",
        "ten_god": "正财",
        "hidden_stems": [{"stem": "己", "level": "本气"}],
        "hidden_ten_gods": ["偏财"],
    },
    {
        "pillar_type": "月柱",
        "stem": "庚",
        "branch": "酉",
        "ten_god": "偏印",
        "hidden_stems": [{"stem": "辛", "level": "本气"}],
        "hidden_ten_gods": ["正印"],
    },
    {
        "pillar_type": "日柱",
        "stem": "甲",
        "branch": "辰",
        "ten_god": None,
        "hidden_stems": [{"stem": "戊", "level": "本气"}],
        "hidden_ten_gods": ["正财"],
    },
    {
        "pillar_type": "时柱",
        "stem": "戊",
        "branch": "戌",
        "ten_god": "正财",
        "hidden_stems": [{"stem": "戊", "level": "本气"}],
        "hidden_ten_gods": ["正财"],
    },
]

INTERACTIONS = {
    "dizhi": [
        {
            "type": "地支六合",
            "result": "合土候选",
        }
    ]
}


def test_weight_report_preserves_existing_scores_and_ranking():
    expected_scores = {
        "正财": 11.0,
        "偏财": 2.0,
        "偏印": 4.5,
        "正印": 3.0,
    }

    assert _compute_weighted_shishen(PILLARS, INTERACTIONS) == expected_scores

    report = get_weighted_shishen_report(PILLARS, INTERACTIONS)
    assert report["scores"] == expected_scores
    assert report["top3"] == [("正财", 11.0), ("偏印", 4.5), ("正印", 3.0)]


def test_weight_breakdown_reconciles_to_each_score():
    report = get_weighted_shishen_report(PILLARS, INTERACTIONS)
    component_names = (
        "tougan",
        "hidden",
        "month_bonus",
        "same_pillar_bonus",
    )

    assert report["breakdown"]["正财"] == {
        "tougan": 6.0,
        "hidden": 4.0,
        "month_bonus": 0.0,
        "same_pillar_bonus": 1.0,
        "total": 11.0,
    }

    for ten_god, score in report["scores"].items():
        breakdown = report["breakdown"][ten_god]
        assert breakdown["total"] == score
        assert sum(breakdown[name] for name in component_names) == pytest.approx(score)


def test_weight_report_declares_scale_and_parameter_snapshot():
    metadata = get_weighted_shishen_report(PILLARS, INTERACTIONS)["scale_metadata"]

    assert metadata == {
        "aggregation": "unbounded_additive",
        "comparison_scope": "absolute_engine_heuristic",
        "ranking_scope": "within_chart_only",
        "banding_scope": "fixed_engine_thresholds",
        "provenance": "engineering_heuristic",
        "relationship_policy": "candidates_do_not_change_weight",
        "parameter_snapshot": {
            "tougan_weight": TOUGAN_WEIGHT,
            "hidden_weights": HIDDEN_WEIGHTS,
            "month_multiplier": MONTH_MULTIPLIER,
            "same_pillar_bonus": SAME_PILLAR_BONUS,
        },
    }


def test_relationship_candidates_do_not_change_weight():
    baseline = get_weighted_shishen_report(PILLARS, {"dizhi": []})
    candidate = get_weighted_shishen_report(PILLARS, INTERACTIONS)

    assert candidate["scores"] == baseline["scores"]
    assert candidate["heju_wuxing"] == {}
    assert candidate["scale_metadata"]["relationship_policy"] == (
        "candidates_do_not_change_weight"
    )


def test_production_relationship_objects_follow_the_no_weight_policy():
    pair = next(iter(DIZHI_LIUHE))
    relations = find_dizhi_liuhe([
        (branch, f"pillar-{index}") for index, branch in enumerate(pair)
    ])
    interactions = {"dizhi": [relation.to_dict() for relation in relations]}

    assert interactions["dizhi"][0]["result"].endswith("候选")
    assert get_weighted_shishen_report(PILLARS, interactions)["scores"] == (
        get_weighted_shishen_report(PILLARS, {"dizhi": []})["scores"]
    )
