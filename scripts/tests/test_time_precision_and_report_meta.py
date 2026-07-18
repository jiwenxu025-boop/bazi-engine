"""Minute-level input, boundary warning, and report metadata contracts."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import bazi_engine.solar_terms as solar_terms
from bazi_engine.api import ChartStreamRequest
from bazi_engine.chart import build_chart
from bazi_engine.enums import Dizhi
from bazi_engine.pillars import (
    WARNING_SHICHEN_BOUNDARY,
    build_four_pillars,
    compute_month_pillar,
    compute_year_pillar,
)


def test_minute_is_used_for_jieqi_year_and_month_boundaries(monkeypatch):
    def fake_jie_datetime(year, index):
        if year == 2024 and index == 0:
            return datetime(2024, 2, 4, 12, 0)
        if year == 2024 and index == 1:
            return datetime(2024, 3, 5, 0, 0)
        return datetime(year, 1, 5, 0, 0)

    monkeypatch.setattr(solar_terms, "get_jie_datetime", fake_jie_datetime)

    _stem, _branch, before_warnings = compute_year_pillar(2024, 2, 4, 11, 59)
    _stem, _branch, after_warnings = compute_year_pillar(2024, 2, 4, 12, 0)
    before_month = compute_month_pillar(
        _stem, 2, 4, 11, gregorian_year=2024, birth_minute=59,
    )[1]
    after_month = compute_month_pillar(
        _stem, 2, 4, 12, gregorian_year=2024, birth_minute=0,
    )[1]

    assert before_warnings
    assert not after_warnings
    assert before_month == Dizhi.丑
    assert after_month == Dizhi.寅


def test_shichen_boundary_warning_uses_odd_hour_boundaries():
    at_boundary = build_four_pillars(2024, 5, 10, 23, minute=0)
    outside_window = build_four_pillars(2024, 5, 10, 23, minute=31)
    even_hour = build_four_pillars(2024, 5, 10, 0, minute=0)

    assert WARNING_SHICHEN_BOUNDARY in at_boundary["warnings"]
    assert WARNING_SHICHEN_BOUNDARY not in outside_window["warnings"]
    assert WARNING_SHICHEN_BOUNDARY not in even_hour["warnings"]


def test_chart_report_meta_records_time_input_sources_and_uncertainty(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    chart = build_chart(
        "metadata-case", "男", 2007, 8, 26, 23,
        minute=0, liunian_range=(2024, 2024), hour_confirmed=True,
    )

    meta = chart.to_dict()["report_meta"]

    assert meta["input"] == {
        "birth_time": "2007-08-26 23:00",
        "time_precision": "minute",
        "hour_confirmed": True,
    }
    assert meta["traceability"]["day_pillar_source"] == "formula"
    assert meta["traceability"]["annual_signal_sources"] == ["rule"]
    assert meta["uncertainty"]["boundary_sensitive"] is True
    assert WARNING_SHICHEN_BOUNDARY in meta["uncertainty"]["warnings"]


def test_chart_stream_request_validates_minute_range():
    payload = ChartStreamRequest(
        gender="男", year=2007, month=8, day=26, hour=20, minute=5,
    )

    assert payload.minute == 5
    with pytest.raises(ValidationError):
        ChartStreamRequest(gender="男", year=2007, month=8, day=26, hour=20, minute=60)


def test_frontend_collects_and_renders_minute_metadata_contract():
    root = Path(__file__).resolve().parents[2]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (root / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'id="minute"' in html
    assert "minute: document.getElementById('minute').value || '0'" in app
    assert "d.report_meta" in app
    assert "报告依据与边界" in app
