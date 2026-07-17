"""Gender-specific chart behavior."""

from bazi_engine.chart import build_chart
from bazi_engine.enums import Dizhi, Tiangan
from bazi_engine.liunian.events.taohua import detect_taohua_signals
from bazi_engine.personality_analysis.special_combos import _check_special_combos
from bazi_engine.personality_analysis.stress import analyze_stress_profile
from bazi_engine.spirits import SpiritAgent, compute_spirit_score


def _same_chart(gender: str) -> dict:
    return build_chart(
        name=f"same-{gender}",
        gender=gender,
        year=2007,
        month=8,
        day=26,
        hour=20,
        liunian_range=(2026, 2026),
    ).to_dict()


def test_same_birth_gender_changes_dayun_jiaoyun_and_xiaoyun():
    male = _same_chart("男")
    female = _same_chart("女")

    assert male["dayun"]["direction"] == "逆排"
    assert female["dayun"]["direction"] == "顺排"
    assert male["dayun"]["periods"][0]["stem"] + male["dayun"]["periods"][0]["branch"] == "丁未"
    assert female["dayun"]["periods"][0]["stem"] + female["dayun"]["periods"][0]["branch"] == "己酉"

    male_jiaoyun = male["dayun"]["jiao_yun"]
    female_jiaoyun = female["dayun"]["jiao_yun"]
    assert male_jiaoyun["reference"] == "上一节"
    assert female_jiaoyun["reference"] == "下一节"
    assert {"years", "months", "days", "hours", "total_days"} <= set(male_jiaoyun)
    assert {"years", "months", "days", "hours", "total_days"} <= set(female_jiaoyun)

    assert male["xiaoyun"]["direction"] == "逆排"
    assert female["xiaoyun"]["direction"] == "顺排"
    assert male["xiaoyun"]["periods"][0]["stem"] + male["xiaoyun"]["periods"][0]["branch"] == "己酉"
    assert female["xiaoyun"]["periods"][0]["stem"] + female["xiaoyun"]["periods"][0]["branch"] == "辛亥"


def test_gender_kinship_mapping_is_exposed_and_used_in_romance_text():
    male = _same_chart("男")
    female = _same_chart("女")

    assert male["kinship"]["spouse"]["label"] == "妻星"
    assert male["kinship"]["spouse"]["stars"] == ["正财", "偏财"]
    assert male["kinship"]["child"]["stars"] == ["正官", "偏官"]
    assert female["kinship"]["spouse"]["label"] == "夫星"
    assert female["kinship"]["spouse"]["stars"] == ["正官", "偏官"]
    assert female["kinship"]["child"]["stars"] == ["食神", "伤官"]

    male_romance = male["personality"]["traits"]["感情"]
    female_romance = female["personality"]["traits"]["感情"]
    assert "妻星" in male_romance
    assert "夫星" in female_romance
    assert male_romance != female_romance


def test_spirit_score_adjusts_guchen_guasu_by_gender():
    guchen = SpiritAgent(name="孤辰", category="凶神", pillar="年柱", source="test")
    guasu = SpiritAgent(name="寡宿", category="凶神", pillar="年柱", source="test")

    assert compute_spirit_score([guchen], gender="男")["unfavorable"] == -2
    assert compute_spirit_score([guchen], gender="女")["unfavorable"] == -1
    assert compute_spirit_score([guasu], gender="女")["unfavorable"] == -2
    assert compute_spirit_score([guasu], gender="男")["unfavorable"] == -1

    male = _same_chart("男")
    female = _same_chart("女")
    assert any(spirit["name"] == "寡宿" for spirit in male["spirits"])
    assert male["spirit_score"]["unfavorable"] == -1
    assert female["spirit_score"]["unfavorable"] == -2


def test_static_pattern_text_branches_by_gender():
    shangguan_zhengguan = [
        {"pillar_type": "年柱", "stem": "甲", "branch": "子", "ten_god": "伤官", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "月柱", "stem": "乙", "branch": "丑", "ten_god": "正官", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "日柱", "stem": "丙", "branch": "寅", "ten_god": None, "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "时柱", "stem": "丁", "branch": "卯", "ten_god": "偏印", "source": "stem", "hidden_ten_gods": []},
    ]
    male_sg = "；".join(_check_special_combos("丙", "火", shangguan_zhengguan, {}, "男", [], ""))
    female_sg = "；".join(_check_special_combos("丙", "火", shangguan_zhengguan, {}, "女", [], ""))
    assert "职场变动" in male_sg
    assert "边界与沟通" in female_sg

    bijie_cai = [
        {"pillar_type": "年柱", "stem": "甲", "branch": "子", "ten_god": "比肩", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "月柱", "stem": "乙", "branch": "丑", "ten_god": "劫财", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "日柱", "stem": "丙", "branch": "寅", "ten_god": None, "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "时柱", "stem": "丁", "branch": "卯", "ten_god": "正财", "source": "stem", "hidden_ten_gods": []},
    ]
    male_bj = "；".join(_check_special_combos("丙", "火", bijie_cai, {}, "男", [], ""))
    female_bj = "；".join(_check_special_combos("丙", "火", bijie_cai, {}, "女", [], ""))
    assert "合作与财务安排" in male_bj
    assert "性格刚强" in female_bj


def test_qisha_stress_profile_branches_by_gender():
    qisha_pillars = [
        {"ten_god": "偏官", "hidden_ten_gods": []},
        {"ten_god": "偏官", "hidden_ten_gods": []},
        {"ten_god": None, "hidden_ten_gods": []},
        {"ten_god": "正官", "hidden_ten_gods": []},
    ]

    male = analyze_stress_profile([], ["偏官"], "弱", "", "男", qisha_pillars, [])
    female = analyze_stress_profile([], ["偏官"], "弱", "", "女", qisha_pillars, [])

    assert "生存压力" in male["pressure_source"]
    assert "小人犯险" in male["pressure_source"]
    assert "感情受制" in female["pressure_source"]
    assert "异性缘复杂" in female["pressure_source"]


def test_taohua_static_text_branches_for_qisha_and_cai_by_gender():
    female_qisha_taohua = [
        {"pillar_type": "年柱", "stem": "甲", "branch": "寅", "ten_god": "正印", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "月柱", "stem": "庚", "branch": "酉", "ten_god": "偏官", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "日柱", "stem": "甲", "branch": "子", "ten_god": None, "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "时柱", "stem": "丁", "branch": "卯", "ten_god": "伤官", "source": "stem", "hidden_ten_gods": []},
    ]
    female_text = "；".join(_check_special_combos("甲", "木", female_qisha_taohua, {}, "女", [], ""))
    assert "七杀坐桃花" in female_text
    assert "感情困扰" in female_text

    male_cai_taohua = [
        {"pillar_type": "年柱", "stem": "甲", "branch": "寅", "ten_god": "比肩", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "月柱", "stem": "戊", "branch": "酉", "ten_god": "偏财", "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "日柱", "stem": "甲", "branch": "子", "ten_god": None, "source": "stem", "hidden_ten_gods": []},
        {"pillar_type": "时柱", "stem": "丁", "branch": "卯", "ten_god": "伤官", "source": "stem", "hidden_ten_gods": []},
    ]
    male_text = "；".join(_check_special_combos("甲", "木", male_cai_taohua, {}, "男", [], ""))
    assert "财星坐桃花" in male_text
    assert "风流" in male_text


def test_liunian_taohua_notes_branch_by_gender():
    female_signals = detect_taohua_signals(
        ln_stem=Tiangan.庚,
        ln_branch=Dizhi.酉,
        year_branch=Dizhi.子,
        day_branch=Dizhi.寅,
        day_master=Tiangan.甲,
        gender="女",
        dayun_stem=None,
        dayun_branch=None,
    )
    female_notes = "；".join(female_signals[0].notes)
    assert "女命七杀坐桃花" in female_notes
    assert "感情困扰" in female_notes

    male_signals = detect_taohua_signals(
        ln_stem=Tiangan.戊,
        ln_branch=Dizhi.酉,
        year_branch=Dizhi.子,
        day_branch=Dizhi.寅,
        day_master=Tiangan.甲,
        gender="男",
        dayun_stem=None,
        dayun_branch=None,
    )
    male_notes = "；".join(male_signals[0].notes)
    assert "男命财星坐桃花" in male_notes
    assert "风流" in male_notes
