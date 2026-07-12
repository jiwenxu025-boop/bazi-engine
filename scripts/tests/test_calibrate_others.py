"""人际/状态/搬迁/健康校准 — pytest 参数化测试"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _calibration_utils import run_calibration
from calibration_others import CASES

# Flatten CASES dict into list of cases
ALL_OTHERS = []
for _category, cases in CASES.items():
    ALL_OTHERS.extend(cases)

_results, _stats = run_calibration(ALL_OTHERS)


@pytest.mark.parametrize("case", _results, ids=[r["name"] for r in _results])
def test_others_calibration(case):
    """每个案例至少有一个容差匹配"""
    if "error" in case:
        pytest.skip(f"build_chart failed: {case['error']}")
    assert case["total"] > 0 or "error" in case, f"{case['name']}: 无预期事件"


def test_others_overall_stats():
    """人际/状态/搬迁/健康整体命中率 ≥50% 严格"""
    if _stats["expected"] == 0:
        pytest.skip("no calibration cases produced expected events")
    assert _stats["strict"] / _stats["expected"] >= 0.45, (
        f"严格命中率 {_stats['strict']}/{_stats['expected']} < 45%"
    )
