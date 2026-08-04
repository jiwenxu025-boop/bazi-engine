"""古籍审计中确认的关系与事件反例。"""

from bazi_engine.chart import build_chart
from bazi_engine.enums import Dizhi, Tiangan
from bazi_engine.interactions import analyze_muku_chong, find_dizhi_sanhe, find_tiangan_wuhe
from bazi_engine.liunian.calibration import apply_shishen_year_notes
from bazi_engine.liunian.events.caiyun import detect_caiyun_signals
from bazi_engine.liunian.events.hunjia import detect_hunjia_signals
from bazi_engine.liunian.events.jiankang import detect_jiankang_signals
from bazi_engine.liunian.events.zhuangtai import detect_zhuangtai_signals
from bazi_engine.liunian.signal import EventSignal
from bazi_engine.liunian.utils import _wealth_magnitude, get_caiku_branch
from bazi_engine.tiaohou import analyze_tiaohou
from bazi_engine.yongshen import _detect_cong_ge, determine_qiangruo, recommend_yongshen


def test_he_relations_are_candidates_not_automatic_transformations():
    stem_relation = find_tiangan_wuhe([(Tiangan.甲, "年柱"), (Tiangan.己, "月柱")])[0]
    assert stem_relation.result == "合土候选"
    assert "化" not in stem_relation.result

    sanhe = find_dizhi_sanhe([
        (Dizhi.辰, "日柱"), (Dizhi.申, "年柱"), (Dizhi.子, "月柱"),
    ])[0]
    assert sanhe.participants == (Dizhi.子, Dizhi.辰, Dizhi.申)
    assert sanhe.result == "三合水局候选"


def test_muku_relation_does_not_infer_health_or_extreme_wealth():
    result = analyze_muku_chong([Dizhi.辰, Dizhi.戌], Tiangan.甲)[0]
    assert result.tu_boost == 1
    assert result.zaqi_damaged == []
    assert "不推断健康" in result.health_note
    assert result.wealth_note == ""


def test_muku_chong_does_not_escalate_health_signal_or_wealth_magnitude():
    signals = detect_jiankang_signals(
        Tiangan.乙, Dizhi.戌, Dizhi.辰, Tiangan.甲, Dizhi.子,
        all_branches=(Dizhi.辰,),
    )

    assert signals[0].strength == 1
    assert all("墓库" not in trigger for signal in signals for trigger in signal.triggers)
    assert _wealth_magnitude(2, ["流年冲原局财库"]) == "弱"
    assert _wealth_magnitude(2, ["财来合我"]) == "弱"


def test_wealth_signals_do_not_predict_money_or_loss_amounts():
    signals = detect_caiyun_signals(
        Tiangan.戊, Dizhi.子, Tiangan.甲, Dizhi.申, Dizhi.子,
    )

    assert signals[0].magnitude == "弱"
    for prohibited in ("投资收益", "大额进账", "皆有收获", "损失或支出规模"):
        assert prohibited not in signals[0].prediction


def test_unverified_shishen_quotations_are_not_injected_into_events():
    signal = EventSignal(category="财运", direction="正面", strength=1)
    apply_shishen_year_notes([signal], "偏财")

    assert signal.notes == []


def test_fuyin_requires_the_full_day_pillar():
    different_stem = detect_zhuangtai_signals(Tiangan.丙, Dizhi.子, Tiangan.甲, Dizhi.子)
    same_pillar = detect_zhuangtai_signals(Tiangan.甲, Dizhi.子, Tiangan.甲, Dizhi.子)

    assert not any("伏吟" in trigger for signal in different_stem for trigger in signal.triggers)
    assert any("伏吟" in trigger for signal in same_pillar for trigger in signal.triggers)


def test_tianhe_dihe_requires_both_stem_and_branch_matches():
    not_tianhe = detect_hunjia_signals(
        Tiangan.戊, Dizhi.丑, Dizhi.子, Tiangan.甲, Dizhi.申, "男", age=28,
    )
    tianhe_dihe = detect_hunjia_signals(
        Tiangan.己, Dizhi.丑, Dizhi.子, Tiangan.甲, Dizhi.申, "男", age=28,
    )

    assert not any("天合地合" in trigger for signal in not_tianhe for trigger in signal.triggers)
    assert any("天合地合" in trigger for signal in tianhe_dihe for trigger in signal.triggers)


def test_caiku_trigger_requires_the_storage_branch_in_the_natal_chart():
    day_master = Tiangan.甲
    caiku = get_caiku_branch(day_master)
    opposing_branch = next(branch for branch in Dizhi if branch != caiku and (branch.index - caiku.index) % 12 == 6)

    absent = detect_caiyun_signals(Tiangan.戊, opposing_branch, day_master, Dizhi.申, Dizhi.子)
    present = detect_caiyun_signals(
        Tiangan.戊, opposing_branch, day_master, Dizhi.申, Dizhi.子,
        all_branches=(Dizhi.申, Dizhi.子, caiku, Dizhi.卯),
    )

    assert not any("冲原局财库" in trigger for signal in absent for trigger in signal.triggers)
    assert any("冲原局财库" in trigger for signal in present for trigger in signal.triggers)


def test_peer_stem_is_counted_and_a_root_blocks_cong_ge():
    branches = [Dizhi.申, Dizhi.酉, Dizhi.戌, Dizhi.亥]
    with_robber = determine_qiangruo(
        Tiangan.甲, Dizhi.申, [Tiangan.乙, Tiangan.戊, Tiangan.甲, Tiangan.庚], branches,
    )[1]
    with_peer = determine_qiangruo(
        Tiangan.甲, Dizhi.申, [Tiangan.甲, Tiangan.戊, Tiangan.甲, Tiangan.庚], branches,
    )[1]

    assert with_peer == with_robber
    assert _detect_cong_ge(
        Tiangan.甲, Dizhi.申, [Tiangan.甲, Tiangan.庚, Tiangan.甲, Tiangan.丙],
        [Dizhi.申, Dizhi.子, Dizhi.辰, Dizhi.寅], "弱", 0.0,
    ) is None


def test_tiaohou_is_supplementary_and_autumn_wood_lists_fire_before_water():
    result = recommend_yongshen(
        Tiangan.甲, Dizhi.酉,
        [Tiangan.庚, Tiangan.辛, Tiangan.甲, Tiangan.戊],
        [Dizhi.申, Dizhi.酉, Dizhi.卯, Dizhi.戌],
    )
    tiaohou = analyze_tiaohou(
        Tiangan.甲, Dizhi.酉, Dizhi.卯,
        [Dizhi.申, Dizhi.酉, Dizhi.卯, Dizhi.戌],
        all_stems=[Tiangan.庚, Tiangan.辛, Tiangan.甲, Tiangan.戊],
    )

    assert result["tiaohou"]["wuxing"] == ["火"]
    assert tiaohou.is_fei_ju is False
    assert "不据此否定格局" in tiaohou.priority_note


def test_yongshen_exposes_one_decision_policy_without_erasing_legacy_fields():
    result = recommend_yongshen(
        Tiangan.甲, Dizhi.酉,
        [Tiangan.庚, Tiangan.辛, Tiangan.甲, Tiangan.戊],
        [Dizhi.申, Dizhi.酉, Dizhi.卯, Dizhi.戌],
        pattern="正官格",
    )

    policy = result["decision_policy"]
    assert policy["precedence"] == ["扶抑/从格", "格局维护", "调候"]
    assert policy["effective"]["favorable"] == result["favorable"]
    assert policy["effective"]["harmful"] == result["harmful"]
    assert policy["pattern"]["needs"]
    assert policy["tiaohou"]["role"] == "supplement"


def test_chart_output_excludes_diagnostic_and_deterministic_harm_language():
    chart = build_chart(
        name="safety", gender="男", year=2007, month=8, day=26, hour=20,
        liunian_range=(2024, 2024),
    )
    output = str(chart.to_dict())

    for prohibited in ("克妻", "克夫", "寿元", "肿瘤倾向", "先天不足", "赌博或挥霍"):
        assert prohibited not in output


def test_suiyun_liuhe_does_not_apply_clash_penalty_to_year_events():
    chart = build_chart(
        name="suiyun-liuhe", gender="男", year=2007, month=8, day=26, hour=20,
        liunian_range=(2027, 2027),
    )
    scan = chart.to_dict()["annual_scans"][0]

    assert scan["liunian"] == "丁未"
    assert scan["dayun"] == "丙午"
    assert any(
        "流年未合大运午" in trigger
        for event in scan["events"]
        for trigger in event["triggers"]
    )
    assert all(
        "岁运交战" not in note and "岁运地战" not in note
        for event in scan["events"]
        for note in event["notes"]
    )


def test_actual_suiyun_clash_still_applies_conflict_note():
    chart = build_chart(
        name="suiyun-clash", gender="男", year=2007, month=8, day=26, hour=20,
        liunian_range=(2030, 2030),
    )
    scan = chart.to_dict()["annual_scans"][0]

    assert scan["liunian"] == "庚戌"
    assert scan["dayun"] == "丙午"
    assert any(
        "天战" in trigger
        for event in scan["events"]
        for trigger in event["triggers"]
    )
    assert any(
        "岁运交战" in note
        for event in scan["events"]
        for note in event["notes"]
    )
