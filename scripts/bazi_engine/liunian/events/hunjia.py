"""婚嫁/婚姻信号检测"""
from ..._constants import DIZHI_CANGGAN, HONGLUAN, TAOHUA, TIANXI
from ...enums import Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal, ScoreAccumulator
from ..utils import (
    HEAVENLY_HE,
    _has_branch_interaction,
    _has_root,
    _make_prediction,
    is_favorable,
)


def detect_hunjia_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          day_branch: Dizhi, day_master: Tiangan,
                          year_branch: Dizhi, gender: str,
                          favorable: set[str] | None = None,
                          dayun_branch: Dizhi | None = None,
                          age: int = 0,
                          all_branches: tuple[Dizhi, ...] = ()) -> list[EventSignal]:
    """检测婚嫁/婚姻信号 — v0.6.0: 打分制 + 大运联动"""
    signals: list[EventSignal] = []
    spouse_star = Shishen.正财 if gender == "男" else Shishen.正官
    spouse_name = "正财" if gender == "男" else "正官"
    second_star = Shishen.偏财 if gender == "男" else Shishen.偏官
    second_name = "偏财" if gender == "男" else "七杀"
    ln_shishen = get_ten_god(day_master, ln_stem)
    s = ScoreAccumulator(favorable)
    s.set_shishen(ln_shishen.value, is_favorable(ln_shishen, favorable))
    s.set_modulate(False)  # 婚嫁只标记不调分

    hongluan = HONGLUAN.get(year_branch)
    tianxi_dz = TIANXI.get(year_branch)
    taohua = TAOHUA.get(year_branch)

    gong_he = _has_branch_interaction(day_branch, ln_branch, "六合")
    gong_sanhe = _has_branch_interaction(day_branch, ln_branch, "三合")
    gong_chong = _has_branch_interaction(day_branch, ln_branch, "六冲")

    # ── 大运联动: 夫妻宫冲处逢合 / 合处逢冲 ──
    if dayun_branch:
        dy_chong_gong = _has_branch_interaction(dayun_branch, day_branch, "六冲")
        dy_he_gong = _has_branch_interaction(dayun_branch, day_branch, "六合")
        # 大运冲日支、流年合入只记录关系结构组合，不单独判定婚期。
        if dy_chong_gong and (gong_he or gong_sanhe):
            s.add(0, "大运冲日支+流年合入→关系结构引动",
                  "冲合组合需结合配偶星及其他现实信息，不单独判断婚期。", fixed=True)
        # 大运合日支、流年冲入只记录关系结构组合，不单独判定婚变。
        if dy_he_gong and gong_chong:
            s.add(0, "大运合日支+流年六冲→关系结构引动",
                  "合冲组合需结合配偶星及其他现实信息，不单独判断婚变。", fixed=True)

    # 检查流年地支藏干是否含配偶星
    ln_canggan_shishen = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
    has_spouse_in_branch = (spouse_star in ln_canggan_shishen or second_star in ln_canggan_shishen)
    spouse_in_branch_label = spouse_name if spouse_star in ln_canggan_shishen else (second_name if second_star in ln_canggan_shishen else "")

    tianxi_activated = False
    if tianxi_dz:
        tianxi_activated = (_has_branch_interaction(tianxi_dz, ln_branch, "六合")
                            or _has_branch_interaction(tianxi_dz, ln_branch, "三合"))

    # ════════════════════════════════════════════════
    # 正面因子（结婚应期）
    # ════════════════════════════════════════════════

    # 配偶星合日主
    he_pair = HEAVENLY_HE.get(day_master)
    if he_pair and ln_stem == he_pair and ln_shishen in (spouse_star, second_star):
        star_label = spouse_name if ln_shishen == spouse_star else second_name
        s.add(4, f"流年{star_label}合日主→婚期最强信号", "配偶星合入日主 (段建业: 星宫同现)")

    # 日柱天合地合必须同时满足天干五合与地支六合。
    has_stem_he = HEAVENLY_HE.get(day_master) == ln_stem
    if gong_he and has_stem_he and ln_shishen == spouse_star:
        s.add(4, f"流年与日柱天合地合+{spouse_name}透干")

    # 天喜入命 + 合夫妻宫
    if ln_branch == tianxi_dz and (gong_he or gong_sanhe):
        s.add(3, "天喜入命+合夫妻宫→婚期")
    elif ln_branch == tianxi_dz:
        s.add(2, "流年天喜入命")

    # 合动天喜 + 夫妻宫引动
    if tianxi_activated and (gong_he or gong_sanhe):
        s.add(3, "流年合动天喜+夫妻宫引动→婚期")

    # 配偶星合入夫妻宫
    if ln_shishen in (spouse_star, second_star) and gong_he:
        s.add(3, "配偶星透干合入夫妻宫")

    # 地支藏配偶星 + 合夫妻宫
    if has_spouse_in_branch and (gong_he or gong_sanhe):
        s.add(3, f"地支{spouse_in_branch_label}合入夫妻宫→婚期")

    # 红鸾/天喜/桃花叠加 + 配偶星
    triple = sum([ln_branch == hongluan, ln_branch == tianxi_dz, ln_branch == taohua])
    if triple >= 2 and (ln_shishen in (spouse_star, second_star) or has_spouse_in_branch):
        s.add(3, "红鸾/天喜/桃花叠加+配偶星")

    # 红鸾+配偶星
    if ln_branch == hongluan and (ln_shishen in (spouse_star, second_star) or has_spouse_in_branch):
        s.add(2, "红鸾入命+配偶星")

    # 地支藏配偶星 — 成人+3, 学生+1(暗恋非婚)
    if has_spouse_in_branch:
        sp_visible = ln_shishen in (spouse_star, second_star)
        is_student = age and age <= 21
        if sp_visible:
            s.add(3, f"干支皆见{spouse_in_branch_label}(配偶星透+藏)", "配偶星公开→正缘/婚期")
        elif is_student:
            s.add(1, f"地支暗藏{spouse_in_branch_label}(配偶星·学生)", "藏干不透+学生→暗恋, 待透干之年转正")
        else:
            s.add(3, f"地支暗藏{spouse_in_branch_label}(配偶星·不透干)", "藏干不透→暗处流动, 但成人仍可成婚")

    # 流年合夫妻宫（弱因子，需搭配配偶星或天喜）
    if gong_he:
        s.add(1, "流年合夫妻宫")
    if gong_sanhe:
        s.add(1, "流年三合夫妻宫")

    # 配偶星透干（有根=有力, 无根=虚浮）
    if ln_shishen == spouse_star:
        if _has_root(ln_stem, ln_branch):
            s.add(2, f"流年{spouse_name}透干有根", "配偶星有力→正缘/正妻")
        else:
            s.add(1, f"流年{spouse_name}透干虚浮", "天干无根→有气无力/机会虚浮")
    if ln_shishen == second_star:
        if _has_root(ln_stem, ln_branch):
            s.add(1, f"流年{second_name}透干有根")
        else:
            s.add(0, f"流年{second_name}透干虚浮", "偏星无根→短暂/非正式")

    # ════════════════════════════════════════════════
    # 关系结构提示（不单独决定方向）
    # ════════════════════════════════════════════════

    if gong_chong:
        s.add(0, "流年与日支六冲→关系结构引动",
              "六冲只记录关系变化候选，不单独判断分手、婚变或离婚。", fixed=True)

    # 比劫夺财(男) / 比劫争官(女) — 弱风险，不抵消婚期
    if ln_shishen == Shishen.劫财:
        if gender == "男":
            s.add(-1, "劫财夺财→感情竞争", "比劫争妻/注意第三者 (段建业)")
        else:
            s.add(-1, "劫财争合→感情竞争", "比劫争夫/注意三角关系 (段建业)")

    # 夫妻宫被穿害 — v0.12.0: 实现穿害检测
    if all_branches:
        for br in all_branches:
            if br == day_branch and _has_branch_interaction(ln_branch, br, "相害"):
                hai_pair = f"{ln_branch.value}{br.value}穿"
                s.add(-2, f"{hai_pair}夫妻宫→婚姻不和", "穿害入夫妻宫→感情伤害/离婚风险")

    # ════════════════════════════════════════════════
    # 输出判断
    # ════════════════════════════════════════════════
    if s.is_significant():
        # 学生年龄段(≤21岁): 婚嫁降级为桃花(只恋不爱, 不论婚嫁)
        cat = "婚嫁"
        pred_cat = "婚嫁"
        if age and age <= 21:
            cat = "桃花"
            pred_cat = "桃花"
        # v0.10.1: 仅≥★2输出——★1弱信号不独立发信号
        if s.strength >= 2:
            signals.append(EventSignal(
                category=cat,
                direction=s.direction,
                strength=s.strength,
                prediction=_make_prediction(pred_cat, s.direction, s.strength, s.triggers(), s.notes()),
                triggers=s.triggers(),
                notes=s.notes(),
            ))
    return signals

