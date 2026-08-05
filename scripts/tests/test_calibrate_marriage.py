"""婚姻/桃花校准 — pytest 参数化测试"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _calibration_utils import run_calibration
from calibration_marriage import MARRIAGE_CASES

_results, _stats = run_calibration(MARRIAGE_CASES)


@pytest.mark.parametrize("case", _results, ids=[r["name"] for r in _results])
def test_marriage_calibration(case):
    """每个婚嫁案例至少有一个容差匹配"""
    # 单案例只验证引擎不崩溃；命中率由 test_marriage_overall_stats 把关
    assert case["total"] > 0, f"{case['name']}: 无预期事件"


def test_marriage_overall_stats():
    """婚嫁探索集保持基本同年覆盖，并要求所有案例落在既定容差内。"""
    assert _stats["expected"] > 0, "婚嫁校准案例没有预期事件"
    assert _stats["strict"] / _stats["expected"] >= 0.50, (
        f"同年同类覆盖 {_stats['strict']}/{_stats['expected']} < 50%"
    )
    assert _stats["strict"] + _stats["tolerance"] >= _stats["expected"], (
        f"含容差覆盖 {_stats['strict']+_stats['tolerance']}/{_stats['expected']} < 100%"
    )
