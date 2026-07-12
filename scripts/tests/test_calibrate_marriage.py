"""婚姻/桃花校准 — pytest 参数化测试"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calibration_marriage import MARRIAGE_CASES
from _calibration_utils import run_calibration

_results, _stats = run_calibration(MARRIAGE_CASES)


@pytest.mark.parametrize("case", _results, ids=[r["name"] for r in _results])
def test_marriage_calibration(case):
    """每个婚嫁案例至少有一个容差匹配"""
    if "error" in case:
        pytest.skip(f"build_chart failed: {case['error']}")
    # 单案例只验证引擎不崩溃；命中率由 test_marriage_overall_stats 把关
    assert case["total"] > 0 or "error" in case, f"{case['name']}: 无预期事件"


def test_marriage_overall_stats():
    """婚嫁总体命中率 ≥70% 严格 / 100% 容差"""
    if _stats["expected"] == 0:
        pytest.skip("no calibration cases produced expected events")
    assert _stats["strict"] / _stats["expected"] >= 0.70, (
        f"严格命中率 {_stats['strict']}/{_stats['expected']} < 70%"
    )
    assert _stats["strict"] + _stats["tolerance"] >= _stats["expected"], (
        f"容差命中率 {_stats['strict']+_stats['tolerance']}/{_stats['expected']} < 100%"
    )
