"""True-solar birth-time resolution and its chart/API boundaries."""

from datetime import datetime

from fastapi.testclient import TestClient

from bazi_engine._chart_context import extract_base_context
from bazi_engine.api import app
from bazi_engine.chart import build_chart
from bazi_engine.pillars import compute_day_pillar
from bazi_engine.time_resolution import resolve_birth_time


def test_unknown_city_keeps_the_input_clock_and_uses_default_china_timezone():
    resolved = resolve_birth_time(year=2007, month=8, day=26, hour=20, minute=0)

    assert resolved.effective_time_mode == "civil_input"
    assert resolved.pillar_dt == datetime(2007, 8, 26, 20, 0)
    assert resolved.birth_instant_utc == datetime(2007, 8, 26, 12, 0)
    assert resolved.solar_correction_minutes == 0


def test_selected_city_uses_true_solar_time_and_keeps_audit_fields():
    resolved = resolve_birth_time(
        year=2007, month=8, day=26, hour=20, minute=0, city_id="chengdu",
    )

    assert resolved.effective_time_mode == "true_solar"
    assert resolved.city and resolved.city.name == "成都"
    assert resolved.longitude_source == "city_registry"
    assert resolved.pillar_dt != resolved.input_civil_dt
    assert resolved.to_report_input()["city"]["id"] == "chengdu"


def test_true_solar_cross_day_changes_only_day_hour_pillar_timeline(monkeypatch):
    import bazi_engine.solar_terms as solar_terms

    monkeypatch.setattr(
        solar_terms,
        "get_jie_datetime",
        lambda year, index: datetime(year, 2, 4, 12, 0) if index == 0 else datetime(year, 3, 5, 0, 0),
    )
    chart = build_chart(
        "cross-day", "男", 2024, 5, 10, 0, minute=30,
        city_id="urumqi", liunian_range=(2024, 2024), hour_confirmed=True,
    )

    expected_day_stem, expected_day_branch, _warnings = compute_day_pillar(2024, 5, 9)
    assert chart.pillar_dt.date().isoformat() == "2024-05-09"
    assert (chart.day.stem, chart.day.branch) == (expected_day_stem, expected_day_branch)
    assert chart.birth_instant_cst.date().isoformat() == "2024-05-10"
    assert any("真太阳时校正跨日" in warning for warning in chart.warnings)


def test_production_chart_path_applies_night_zi_day_rule():
    chart = build_chart("night-zi", "男", 2024, 5, 10, 23, minute=0, hour_confirmed=True)
    expected_day_stem, expected_day_branch, _warnings = compute_day_pillar(2024, 5, 11)

    assert (chart.day.stem, chart.day.branch) == (expected_day_stem, expected_day_branch)
    assert chart.hour_zi_flag == "夜子时"


def test_llm_context_receives_time_basis_without_changing_birth_age_date():
    chart = build_chart(
        "llm-time", "女", 2007, 8, 26, 20, minute=0,
        city_id="beijing", liunian_range=(2026, 2026), hour_confirmed=True,
    )
    context = extract_base_context(chart.to_dict())

    assert context["time_basis"]["effective_time_mode"] == "true_solar"
    assert context["time_basis"]["city"] == "北京市 北京"
    assert context["time_basis"]["pillar_time"] != chart.birth_dt.strftime("%Y-%m-%d %H:%M")


def test_location_search_and_time_preview_are_offline_api_contracts():
    client = TestClient(app)
    locations = client.get("/api/locations", params={"q": "成都"})
    preview = client.post("/api/time/preview", json={
        "year": 2007,
        "month": 8,
        "day": 26,
        "hour": 20,
        "minute": 0,
        "city_id": "chengdu",
    })

    assert locations.status_code == 200
    assert locations.json()["items"][0]["id"] == "chengdu"
    assert preview.status_code == 200
    assert preview.json()["effective_time_mode"] == "true_solar"
    assert preview.json()["city"]["id"] == "chengdu"
