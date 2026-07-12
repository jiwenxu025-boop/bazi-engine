"""Chart build stage helper tests."""

from datetime import datetime

from bazi_engine.chart import (
    _attach_hidden_stems_and_nayin,
    _compute_dayun_stage,
    _compute_four_pillars,
    _compute_nayin_relations,
    _compute_palace_origins,
    _compute_pattern_stage,
    _compute_tiaohou_health_stage,
    _compute_ten_gods_stage,
    _compute_void_gods_stage,
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


def test_compute_ten_gods_stage_sets_visible_and_hidden_ten_gods():
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

    _compute_ten_gods_stage(chart)

    assert chart.year.ten_god.value == "正财"
    assert chart.month.ten_god.value == "偏官"
    assert chart.day.ten_god is None
    assert chart.hour.ten_god.value == "偏印"
    assert {k.value: v.value for k, v in chart.year.ten_gods_map.items()} == {
        "壬": "比肩",
        "甲": "食神",
    }
    assert {k.value: v.value for k, v in chart.month.ten_gods_map.items()} == {
        "庚": "偏印",
        "壬": "比肩",
        "戊": "偏官",
    }
    assert {k.value: v.value for k, v in chart.day.ten_gods_map.items()} == {
        "戊": "偏官",
        "乙": "伤官",
        "癸": "劫财",
    }
    assert {k.value: v.value for k, v in chart.hour.ten_gods_map.items()} == {
        "戊": "偏官",
        "辛": "正印",
        "丁": "正财",
    }


def test_compute_pattern_stage_sets_pattern_and_pattern_yongshen():
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
    _compute_yongshen_stage(chart, favorable=None)

    all_stems = _compute_pattern_stage(chart)

    assert all_stems == [Tiangan.丁, Tiangan.戊, Tiangan.壬, Tiangan.庚]
    assert chart.pattern == "偏印格"
    assert chart.pattern_notes == ["月支申 本气庚透干"]
    assert chart._yongshen_result["pattern_yongshen"] == {
        "method": "逆用→喜财制枭",
        "needs": ["正财", "偏财"],
        "avoid": ["食神"],
        "note": "格局偏印格逆用→喜财制枭。格局用神推荐：正财/偏财；忌：食神。",
    }


def test_compute_void_gods_stage_sets_month_hidden_unrevealed_gods():
    chart = _init_chart_shell(
        name="test",
        gender="男",
        year=1990,
        month=6,
        day=15,
        hour=12,
        day_pillar_override=None,
        favorable=None,
        life_stage_override="",
        family_context=None,
        hour_confirmed=True,
    )
    _compute_four_pillars(chart, 1990, 6, 15, 12, None)
    _compute_yongshen_stage(chart, favorable=None)
    all_stems = _compute_pattern_stage(chart)

    _compute_void_gods_stage(chart, all_stems)

    void_gods = [vg.to_dict() for vg in chart.void_gods]
    assert [
        (vg["hidden_stem"], vg["source_branch"], vg["level"], vg["ten_god"], vg["is_favorable"])
        for vg in void_gods
    ] == [
        ("丁", "午", "本气", "偏官", False),
        ("己", "午", "中气", "偏印", False),
    ]
    assert "月支午藏丁" in void_gods[0]["interpretation"]
    assert "月支午藏己" in void_gods[1]["interpretation"]


def test_compute_dayun_stage_sets_direction_start_age_and_periods():
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

    start_age = _compute_dayun_stage(chart, gender="男")

    assert start_age == 6
    assert chart.dayun_direction_str == "逆排"
    assert chart.start_age == 6
    assert [(stem.value, branch.value) for stem, branch in chart.luck_pillars[:6]] == [
        ("丁", "未"),
        ("丙", "午"),
        ("乙", "巳"),
        ("甲", "辰"),
        ("癸", "卯"),
        ("壬", "寅"),
    ]
    assert chart.luck_periods[0]["大运"] == "丁未"
    assert chart.luck_periods[0]["年龄"] == "6-15岁"
    assert chart.luck_periods[0]["序"] == 1
