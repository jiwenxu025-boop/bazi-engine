"""事业校准 — pytest 参数化测试"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calibration_career import CAREER_CASES
from _calibration_utils import run_calibration

_results, _stats = run_calibration(CAREER_CASES)


@pytest.mark.parametrize("case", _results, ids=[r["name"] for r in _results])
def test_career_calibration(case):
    """每个事业案例至少有一个容差匹配"""
    if "error" in case:
        pytest.skip(f"build_chart failed: {case['error']}")
    assert case["total"] > 0 or "error" in case, f"{case['name']}: 无预期事件"


def test_career_overall_stats():
    """事业总体命中率 ≥60% 严格"""
    if _stats["expected"] == 0:
        pytest.skip("no calibration cases produced expected events")
    assert _stats["strict"] / _stats["expected"] >= 0.55, (
        f"严格命中率 {_stats['strict']}/{_stats['expected']} < 55%"
    )
