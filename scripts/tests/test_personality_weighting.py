"""Auditable personality weight report tests."""

import pytest

from bazi_engine.personality_analysis.constants import (
    HEJU_WEIGHTS,
    HIDDEN_WEIGHTS,
    MONTH_MULTIPLIER,
    SAME_PILLAR_BONUS,
    TOUGAN_WEIGHT,
)
from bazi_engine.personality_analysis.weighting import (
    _compute_weighted_shishen,
    _extract_heju_wuxing,
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
            "result": "化土",
        }
    ]
}


def test_weight_report_preserves_existing_scores_and_ranking():
    expected_scores = {
        "正财": 13.0,
        "偏财": 4.0,
        "偏印": 4.5,
        "正印": 3.0,
    }

    assert _compute_weighted_shishen(PILLARS, INTERACTIONS) == expected_scores

    report = get_weighted_shishen_report(PILLARS, INTERACTIONS)
    assert report["scores"] == expected_scores
    assert report["top3"] == [("正财", 13.0), ("偏印", 4.5), ("偏财", 4.0)]


def test_weight_breakdown_reconciles_to_each_score():
    report = get_weighted_shishen_report(PILLARS, INTERACTIONS)
    component_names = (
        "tougan",
        "hidden",
        "month_bonus",
        "same_pillar_bonus",
        "heju_bonus",
    )

    assert report["breakdown"]["正财"] == {
        "tougan": 6.0,
        "hidden": 4.0,
        "month_bonus": 0.0,
        "same_pillar_bonus": 1.0,
        "heju_bonus": 2.0,
        "total": 13.0,
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
        "heju_application": "once_per_matching_ten_god",
        "parameter_snapshot": {
            "tougan_weight": TOUGAN_WEIGHT,
            "hidden_weights": HIDDEN_WEIGHTS,
            "month_multiplier": MONTH_MULTIPLIER,
            "same_pillar_bonus": SAME_PILLAR_BONUS,
            "heju_weights": HEJU_WEIGHTS,
        },
    }


def test_heju_extraction_accepts_production_result_formats():
    interactions = {
        "dizhi": [
            {"type": "地支六合", "result": "化土"},
            {"type": "三合", "result": "合火"},
            {"type": "半合", "result": "合木"},
            {"type": "三会", "result": "会金"},
        ]
    }

    assert _extract_heju_wuxing(interactions) == {
        "土": 2.0,
        "火": 2.5,
        "木": 1.5,
        "金": 3.0,
    }
