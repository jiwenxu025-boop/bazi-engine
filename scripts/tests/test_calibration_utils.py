"""Regression tests for calibration match contracts."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _calibration_utils import check_case, run_calibration


def _annual_scan(year, category, *, strength=2, direction="正面"):
    return [{"year": year, "events": [{"category": category, "strength": strength, "direction": direction}]}]


@pytest.mark.parametrize(
    ("annual_scans", "year", "category", "expected_status", "expected_label"),
    [
        (_annual_scan(2024, "婚嫁"), 2024, "婚嫁", "HIT", "2024 婚嫁"),
        (_annual_scan(2024, "桃花"), 2024, "婚嫁", "TOL", "2024 婚嫁←桃花"),
        (_annual_scan(2023, "婚嫁"), 2024, "婚嫁", "TOL", "2024 婚嫁←2023年"),
        (_annual_scan(2025, "桃花"), 2024, "婚嫁", "TOL", "2024 婚嫁←2025年桃花"),
    ],
)
def test_check_case_returns_a_three_part_result(
    annual_scans, year, category, expected_status, expected_label
):
    result = check_case(annual_scans, year, category)

    assert len(result) == 3
    status, label, detail = result
    assert status == expected_status
    assert label == expected_label
    assert detail


def test_check_case_marks_a_weak_signal_as_a_miss():
    status, label, detail = check_case(_annual_scan(2024, "婚嫁", strength=1), 2024, "婚嫁")

    assert status == "MISS"
    assert label == "2024 婚嫁"
    assert "弱信号" in detail


def test_run_calibration_propagates_engine_errors(monkeypatch):
    def raise_engine_error(**_kwargs):
        raise RuntimeError("engine failed")

    monkeypatch.setattr("bazi_engine.chart.build_chart", raise_engine_error)
    case = {
        "name": "broken-case",
        "gender": "男",
        "year": 1990,
        "month": 1,
        "day": 1,
        "hour": 0,
        "events": {2024: "事业"},
    }

    with pytest.raises(RuntimeError, match="engine failed"):
        run_calibration([case])
