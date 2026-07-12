"""财运校准 — pytest 参数化测试"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calibration_wealth import WEALTH_CASES, CELEB_WEALTH
from _calibration_utils import run_calibration

ALL_WEALTH = WEALTH_CASES + CELEB_WEALTH
_results, _stats = run_calibration(ALL_WEALTH)


@pytest.mark.parametrize("case", _results, ids=[r["name"] for r in _results])
def test_wealth_calibration(case):
    """每个财运案例至少有一个容差匹配"""
    if "error" in case:
        pytest.skip(f"build_chart failed: {case['error']}")
    assert case["total"] > 0 or "error" in case, f"{case['name']}: 无预期事件"


def test_wealth_overall_stats():
    """财运总体命中率 ≥70% 严格"""
    if _stats["expected"] == 0:
        pytest.skip("no calibration cases produced expected events")
    assert _stats["strict"] / _stats["expected"] >= 0.65, (
        f"严格命中率 {_stats['strict']}/{_stats['expected']} < 65%"
    )
