"""Chart build stage helper tests."""

from datetime import datetime

from bazi_engine.chart import (
    _attach_hidden_stems_and_nayin,
    _compute_four_pillars,
    _compute_nayin_relations,
    _compute_palace_origins,
    _compute_tiaohou_health_stage,
    _compute_yongshen_stage,
    _init_chart_shell,
)
from bazi_engine.enums import Dizhi, Tiangan


def test_init_chart_shell_sets_input_state_and_hour_warning():
    chart = _init_chart_shell(
        name="test",
        gender="男",
        year=1990,
        month=6,
        day=15,
        hour=12,
        day_pillar_override=None,
        favorable={"正印"},
        life_stage_override="职场",
        family_context={"economic_level": "普通"},
        hour_confirmed=False,
    )

    assert chart.name == "test"
    assert chart.gender == "男"
    assert chart.birth_dt == datetime(1990, 6, 15, 12)
    assert chart.day_pillar_source == "formula"
    assert chart.favorable_tags == {"正印"}
    assert chart.life_stage_override == "职场"
    assert chart._life_stage_override == "职场"
    assert chart.family_context == {"economic_level": "普通"}
    assert chart.hour_confirmed is False
    assert chart.warnings


def test_compute_four_pillars_sets_expected_known_case():
    chart = _init_chart_shell(
        name="案例A",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        day_pillar_override=None,
        favorable=None,
        life_stage_override="",
        family_context=None,
        hour_confirmed=True,
    )

    _compute_four_pillars(
        chart,
        year=2007,
        month=8,
        day=26,
        hour=20,
        day_pillar_override=None,
    )

    assert chart.year.stem == Tiangan.丁
    assert chart.year.branch == Dizhi.亥
    assert chart.month.stem == Tiangan.戊
    assert chart.month.branch == Dizhi.申
    assert chart.day.stem == Tiangan.壬
    assert chart.day.branch == Dizhi.辰
    assert chart.hour.stem == Tiangan.庚
    assert chart.hour.branch == Dizhi.戌
    assert chart.day_master == Tiangan.壬


def test_attach_hidden_stems_and_nayin_sets_pillar_details():
    chart = _init_chart_shell(
        name="案例A",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        day_pillar_override=None,
        favorable=None,
        life_stage_override="",
        family_context=None,
        hour_confirmed=True,
    )
    _compute_four_pillars(chart, 2007, 8, 26, 20, None)

    _attach_hidden_stems_and_nayin(chart)

    assert [hs.stem for hs in chart.year.hidden_stems] == [Tiangan.壬, Tiangan.甲]
    assert [hs.level for hs in chart.year.hidden_stems] == ["本气", "中气"]
    assert chart.year.nayin == "屋上土"


def test_compute_palace_origins_sets_minggong_shengong_taiyuan():
    chart = _init_chart_shell(
        name="案例A",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        day_pillar_override=None,
        favorable=None,
        life_stage_override="",
        family_context=None,
        hour_confirmed=True,
    )
    y_tg, m_tg, m_dz, h_dz = _compute_four_pillars(chart, 2007, 8, 26, 20, None)

    _compute_palace_origins(chart, y_tg, m_tg, m_dz, h_dz)

    assert chart.minggong_stem == Tiangan.辛
    assert chart.minggong_branch == Dizhi.亥
    assert chart.minggong_nayin == "钗钏金"
    assert chart.shengong_stem == Tiangan.丁
    assert chart.shengong_branch == Dizhi.未
    assert chart.shengong_nayin == "天河水"
    assert chart.taiyuan_stem == Tiangan.己
    assert chart.taiyuan_branch == Dizhi.亥
    assert chart.taiyuan_nayin == "平地木"


def test_compute_nayin_relations_sets_known_case_relations():
    chart = _init_chart_shell(
        name="案例A",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        day_pillar_override=None,
        favorable=None,
        life_stage_override="",
        family_context=None,
        hour_confirmed=True,
    )
    _compute_four_pillars(chart, 2007, 8, 26, 20, None)
    _attach_hidden_stems_and_nayin(chart)

    _compute_nayin_relations(chart)

    relation_types = [r.relation_type for r in chart.nayin_relations]
    assert relation_types == ["同类比和", "年纳音克他柱", "年纳音生他柱"]


def test_compute_yongshen_stage_sets_result_and_returns_pillar_lists():
    chart = _init_chart_shell(
        name="案例A",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        day_pillar_override=None,
        favorable={"正印"},
        life_stage_override="",
        family_context=None,
        hour_confirmed=True,
    )
    _compute_four_pillars(chart, 2007, 8, 26, 20, None)

    all_stems, all_branches = _compute_yongshen_stage(chart, favorable={"正印"})

    assert all_stems == [Tiangan.丁, Tiangan.戊, Tiangan.壬, Tiangan.庚]
    assert all_branches == [Dizhi.亥, Dizhi.申, Dizhi.辰, Dizhi.戌]
    assert chart._yongshen_result["strength"] == "强"
    assert chart._yongshen_result["score"] == 5.5
    assert chart._yongshen_result["favorable"] == ["正印"]
    assert chart._yongshen_result["harmful"] == ["偏印", "劫财", "正印", "比肩"]


def test_compute_tiaohou_health_stage_sets_known_case_results():
    chart = _init_chart_shell(
        name="案例A",
        gender="男",
        year=2007,
        month=8,
        day=26,
        hour=20,
        day_pillar_override=None,
        favorable=None,
        life_stage_override="",
        family_context=None,
        hour_confirmed=True,
    )
    _compute_four_pillars(chart, 2007, 8, 26, 20, None)
    all_stems, all_branches = _compute_yongshen_stage(chart, favorable=None)

    _compute_tiaohou_health_stage(chart, all_stems, all_branches)

    assert chart.tiaohou_result == {
        "season": "秋",
        "climate": "中和",
        "is_fei_ju": False,
        "tiaohou_wuxing": [],
        "reason": "",
        "priority_note": "原局寒暖燥湿适中，调候无忧。",
    }
    assert chart.health_profile["tiaohou_label"] == "寒暖适中（基础体质良好）"
    assert chart.health_profile["tiaohou_risks"] == []
    assert chart.health_profile["tiaohou_advice"] == "无特殊偏颇，保持均衡饮食和适度运动即可"
    assert [risk["wuxing"] for risk in chart.health_profile["wuxing_risks"]] == ["木", "火"]
