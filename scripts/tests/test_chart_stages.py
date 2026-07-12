"""Chart build stage helper tests."""

from datetime import date, datetime

import bazi_engine.chart as chart_module
from bazi_engine.chart import (
    _attach_hidden_stems_and_nayin,
    _compute_body_use_stage,
    _compute_dayun_stage,
    _compute_dayun_modulation_stage,
    _compute_four_pillars,
    _compute_interactions_stage,
    _compute_changsheng_stage,
    _compute_life_stage,
    _compute_liunian_stage,
    _compute_nayin_relations,
    _compute_palace_origins,
    _compute_palace_star_stage,
    _compute_personality_family_stage,
    _compute_pattern_stage,
    _compute_spirits_stage,
    _compute_tiaohou_health_stage,
    _compute_ten_gods_stage,
    _compute_void_gods_stage,
    _compute_yongshen_stage,
    _init_chart_shell,
)
from bazi_engine.enums import Dizhi, Tiangan


def _case_a_chart():
    return _init_chart_shell(
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


def _prepare_case_a_through_spirits():
    chart = _case_a_chart()
    _compute_four_pillars(chart, 2007, 8, 26, 20, None)
    _attach_hidden_stems_and_nayin(chart)
    _, all_branches = _compute_yongshen_stage(chart, favorable=None)
    _compute_tiaohou_health_stage(chart, [chart.year.stem, chart.month.stem, chart.day.stem, chart.hour.stem], all_branches)
    _compute_ten_gods_stage(chart)
    all_stems = _compute_pattern_stage(chart)
    _compute_void_gods_stage(chart, all_stems)
    start_age = _compute_dayun_stage(chart, gender="男")
    _compute_dayun_modulation_stage(chart, start_age)
    _, branch_labels = _compute_interactions_stage(chart, all_branches)
    _compute_spirits_stage(chart, branch_labels)
    return chart, start_age


def _prepare_case_a_through_liunian(liunian_range=(2023, 2024)):
    chart, start_age = _prepare_case_a_through_spirits()
    _compute_liunian_stage(
        chart,
        gender="男",
        start_age=start_age,
        liunian_range=liunian_range,
        known_events=None,
        favorable=None,
    )
    return chart, start_age


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


def test_compute_dayun_modulation_stage_sets_known_case_modulations():
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
    start_age = _compute_dayun_stage(chart, gender="男")

    _compute_dayun_modulation_stage(chart, start_age)

    assert len(chart.dayun_modulations) == 8
    first, second = chart.dayun_modulations[:2]
    assert first["period_index"] == 0
    assert first["dayun_stem"] == "丁"
    assert first["dayun_branch"] == "未"
    assert first["age_range"] == "6-15岁"
    assert first["stem_interactions"] == ["与原局壬合化木"]
    assert first["branch_interactions"] == ["与原局亥半合木"]
    assert first["stem_is_favorable"] is True
    assert first["branch_is_favorable"] is True
    assert first["baseline_offset"] == 1
    assert first["theme"] == "财运"
    assert second["period_index"] == 1
    assert second["dayun_stem"] == "丙"
    assert second["dayun_branch"] == "午"
    assert second["age_range"] == "16-25岁"
    assert second["branch_interactions"] == ["与原局戌半合火"]
    assert second["baseline_offset"] == 1


def test_compute_interactions_stage_sets_interactions_and_returns_labels():
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
    _, all_branches = _compute_yongshen_stage(chart, favorable=None)

    stem_labels, branch_labels = _compute_interactions_stage(chart, all_branches)

    assert [(stem.value, label) for stem, label in stem_labels] == [
        ("丁", "年柱"),
        ("戊", "月柱"),
        ("壬", "日柱"),
        ("庚", "时柱"),
    ]
    assert [(branch.value, label) for branch, label in branch_labels] == [
        ("亥", "年柱"),
        ("申", "月柱"),
        ("辰", "日柱"),
        ("戌", "时柱"),
    ]
    assert [item.to_dict() for item in chart.tiangan_interactions] == [
        {
            "type": "天干五合",
            "participants": ["丁", "壬"],
            "pillars": ["年柱", "日柱"],
            "result": "化木",
            "notes": [],
        }
    ]
    dizhi_relations = {
        (item.inter_type, frozenset(p.value for p in item.participants))
        for item in chart.dizhi_interactions
    }
    assert {
        ("六冲", frozenset({"辰", "戌"})),
        ("相害", frozenset({"亥", "申"})),
        ("墓库相冲", frozenset({"辰", "戌"})),
    }.issubset(dizhi_relations)
    half_relations = {relation for relation in dizhi_relations if relation[0] == "半合"}
    assert half_relations in ({("半合", frozenset({"申", "辰"}))}, set())
    assert chart.tansheng_wangke == []
    assert chart.false_generations is None


def test_compute_spirits_stage_sets_known_case_spirits():
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
    _, all_branches = _compute_yongshen_stage(chart, favorable=None)
    _, branch_labels = _compute_interactions_stage(chart, all_branches)

    _compute_spirits_stage(chart, branch_labels)

    assert [spirit.to_dict() for spirit in chart.spirits] == [
        {"name": "天乙贵人", "category": "吉神", "pillar": "年柱", "source": "以年干丁查", "notes": []},
        {"name": "学堂", "category": "吉神", "pillar": "月柱", "source": "以日干壬查", "notes": []},
        {"name": "太极贵人", "category": "吉神", "pillar": "月柱", "source": "以日干壬查", "notes": []},
        {"name": "福星贵人", "category": "吉神", "pillar": "日柱", "source": "以日干壬查", "notes": []},
        {"name": "红鸾", "category": "吉神", "pillar": "日柱", "source": "以年支亥查", "notes": []},
        {"name": "天喜", "category": "吉神", "pillar": "时柱", "source": "以年支亥查（红鸾对冲）", "notes": []},
        {"name": "寡宿", "category": "凶神", "pillar": "时柱", "source": "以年支亥查", "notes": []},
        {"name": "禄", "category": "吉神", "pillar": "年柱", "source": "以日干壬查", "notes": []},
    ]


def test_compute_liunian_stage_scans_known_two_year_range(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    chart, _ = _prepare_case_a_through_liunian()

    assert [scan.year for scan in chart.annual_scans] == [2023, 2024]
    assert [scan.age for scan in chart.annual_scans] == [16, 17]
    assert [scan.to_dict()["liunian"] for scan in chart.annual_scans] == ["癸卯", "甲辰"]
    assert [scan.to_dict()["dayun"] for scan in chart.annual_scans] == ["丙午", "丙午"]
    assert [
        (event.category, event.direction, event.strength)
        for event in chart.annual_scans[0].events[:4]
    ] == [
        ("桃花", "中性", 2),
        ("财运", "负面", 2),
        ("人际", "负面", 2),
        ("状态", "负面", 2),
    ]
    second_year_events = {
        (event.category, event.direction, event.strength)
        for event in chart.annual_scans[1].events
    }
    assert {
        ("升学", "正面", 3),
        ("学业", "正面", 3),
        ("财运", "正面", 3),
    }.issubset(second_year_events)


def test_compute_changsheng_stage_sets_pillar_dayun_and_liunian_states(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    chart, _ = _prepare_case_a_through_liunian()

    _compute_changsheng_stage(chart)

    assert len(chart.changsheng_states) == 14
    assert [
        (
            state.subject,
            state.stem.value,
            state.branch.value,
            state.state,
            state.pillar_label,
            state.year,
        )
        for state in chart.changsheng_states[:5]
    ] == [
        ("日主", "壬", "亥", "临官", "年柱", None),
        ("日主", "壬", "申", "长生", "月柱", None),
        ("日主", "壬", "辰", "墓", "日柱", None),
        ("日主", "壬", "戌", "冠带", "时柱", None),
        ("大运", "壬", "未", "养", "大运", None),
    ]
    assert [
        (state.subject, state.branch.value, state.state, state.year)
        for state in chart.changsheng_states[-2:]
    ] == [
        ("流年", "卯", "死", 2023),
        ("流年", "辰", "墓", 2024),
    ]


def test_compute_life_stage_honors_manual_override():
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

    _compute_life_stage(chart, life_stage_override="职场", start_age=0)

    assert chart.life_stage == "职场"


def test_compute_life_stage_uses_fixed_current_age_and_liunian_signal(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 7, 12)

    monkeypatch.setattr(chart_module, "date", FixedDate)
    chart, start_age = _prepare_case_a_through_liunian(liunian_range=(2025, 2026))

    _compute_life_stage(chart, life_stage_override="", start_age=start_age)

    assert chart.life_stage == "大学"


def test_compute_personality_family_stage_sets_analysis_and_returns_context(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    monkeypatch.setenv("BAZI_FUSION_ENGINE", "0")
    chart, start_age = _prepare_case_a_through_liunian()
    _compute_changsheng_stage(chart)
    _compute_life_stage(chart, life_stage_override="大学", start_age=start_age)

    pd, interactions_dict = _compute_personality_family_stage(chart, gender="男", family_context=None)

    assert pd is not None
    assert set(interactions_dict) == {"tiangan_wuhe", "dizhi"}
    assert chart.personality_result["strength_label"] == "强（5.5分）"
    assert chart.personality_result["pattern_validation"]["status"] == "成格"
    assert chart.family_result["level"] == "普通"


def test_compute_palace_star_stage_sets_four_palace_entries(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    monkeypatch.setenv("BAZI_FUSION_ENGINE", "0")
    chart, _ = _prepare_case_a_through_liunian()
    pd, _ = _compute_personality_family_stage(chart, gender="男", family_context=None)

    _compute_palace_star_stage(chart, pd)

    assert [entry["pillar_type"] for entry in chart.palace_star_result["entries"]] == ["年柱", "月柱", "日柱", "时柱"]
    assert chart.palace_star_result["entries"][0]["occupying_ten_god"] == "正财"
    assert chart.palace_star_result["entries"][0]["spirits_at_palace"] == ["天乙贵人", "禄"]
    assert "年柱（正财）" in chart.palace_star_result["summary"]


def test_compute_body_use_stage_sets_balance_and_muku_signals(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    monkeypatch.setenv("BAZI_FUSION_ENGINE", "0")
    chart, _ = _prepare_case_a_through_liunian()
    pd, interactions_dict = _compute_personality_family_stage(chart, gender="男", family_context=None)

    _compute_body_use_stage(chart, pd, interactions_dict)

    assert chart.body_use_result["body_stars"] == ["偏印"]
    assert chart.body_use_result["use_stars"] == ["正财", "偏官"]
    assert chart.body_use_result["body_count"] == 1
    assert chart.body_use_result["use_count"] == 2
    assert chart.body_use_result["mu_ku_signals"] == ["原局辰+戌冲→墓库逢冲，重大转机信号"]
