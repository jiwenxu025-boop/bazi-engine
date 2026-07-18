"""事业校准 — pytest 参数化测试"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _calibration_utils import run_calibration
from calibration_career import CAREER_CASES

CAREER_CALIBRATION_CASES = [
    {
        **case,
        "events": {year: category for year, category in case["events"].items() if category == "事业"},
    }
    for case in CAREER_CASES
]

_results, _stats = run_calibration(CAREER_CALIBRATION_CASES)


@pytest.mark.parametrize("case", _results, ids=[r["name"] for r in _results])
def test_career_calibration(case):
    """每个事业案例至少有一个容差匹配"""
    assert case["total"] > 0, f"{case['name']}: 无预期事件"


def test_career_cases_only_score_career_events():
    assert all(
        case["events"] and set(case["events"].values()) == {"事业"}
        for case in CAREER_CALIBRATION_CASES
    )


def test_career_overall_stats():
    """事业总体命中率 ≥60% 严格"""
    assert _stats["expected"] > 0, "事业校准案例没有预期事件"
    assert _stats["strict"] / _stats["expected"] >= 0.55, (
        f"严格命中率 {_stats['strict']}/{_stats['expected']} < 55%"
    )
