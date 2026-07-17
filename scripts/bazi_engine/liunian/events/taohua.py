"""桃花/感情信号检测"""
from ..._constants import HONGLUAN, TAOHUA, TIANXI
from ...enums import Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal
from ..utils import (
    _has_branch_interaction,
    _is_in_same_sanhe,
    _is_kongwang,
    _kongwang_branches,
    _make_prediction,
)


def detect_taohua_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          year_branch: Dizhi, day_branch: Dizhi,
                          day_master: Tiangan, gender: str,
                          dayun_stem: Tiangan | None, dayun_branch: Dizhi | None,
                          prev_year_has_relationship: bool = False,
                          favorable: set[str] | None = None,
                          all_branches: tuple[Dizhi, ...] = ()) -> list[EventSignal]:
    """检测桃花/感情信号

    神煞与干支关系只作文化参考，不以个别校准案例推导普遍感情结果。
    """
    signals: list[EventSignal] = []

    # 红鸾/天喜
    hongluan = HONGLUAN.get(year_branch)
    tianxi = TIANXI.get(year_branch)
    taohua = TAOHUA.get(year_branch)

    spouse_star = Shishen.正财 if gender == "男" else Shishen.正官
    spouse_star_name = "正财" if gender == "男" else "正官"
    ln_shishen = get_ten_god(day_master, ln_stem)

    strength = 0
    triggers = []
    notes = []

    # ── ★★★ 级别 ──
    # 流年地支合入夫妻宫（桃花合入日支）
    if _has_branch_interaction(day_branch, ln_branch, "六合"):
        strength = max(strength, 3)
        triggers.append("桃花合入夫妻宫")

    # 红鸾/天喜叠临桃花
    if ln_branch in (hongluan, tianxi) and ln_branch == taohua:
        strength = max(strength, 3)
        triggers.append("红鸾/天喜叠桃花")

    # 配偶星透干+合入日柱
    if ln_shishen == spouse_star and _has_branch_interaction(day_branch, ln_branch, "六合"):
        strength = max(strength, 3)
        triggers.append(f"{spouse_star_name}透干合入夫妻宫")

    # ── ★★ 级别 ──
    # 三种情况：流年直接见天喜、六合天喜、同三合组天喜。
    if ln_branch == tianxi:
        strength = max(strength, 2)
        triggers.append("流年天喜入命")
        notes.append("天喜入命，作为传统神煞的文化参考。")
    elif _has_branch_interaction(ln_branch, tianxi, "六合"):
        strength = max(strength, 2)
        triggers.append(f"{ln_branch.value}{tianxi.value}合→天喜被合动")
        notes.append("天喜被六合引动，作为传统神煞的文化参考。")
    elif tianxi and _is_in_same_sanhe(ln_branch, tianxi):
        strength = max(strength, 2)
        triggers.append(f"{ln_branch.value}{tianxi.value}半/三合→天喜被合动")
        notes.append("天喜同三合组出现，作为传统神煞的文化参考。")

    # 流年地支合日支
    if _has_branch_interaction(day_branch, ln_branch, "六合"):
        strength = max(strength, 2)
        triggers.append("流年合夫妻宫")

    # 桃花年
    if ln_branch == taohua:
        strength = max(strength, 2)
        triggers.append("流年桃花入命")
        if gender == "女" and ln_shishen in (Shishen.偏官, Shishen.正官):
            notes.append("女命七杀坐桃花→异性缘复杂，偏向感情困扰/关系受制，择偶需看边界感")
        elif gender == "男" and ln_shishen in (Shishen.偏财, Shishen.正财):
            notes.append("男命财星坐桃花→异性缘旺、风流机会多，需防感情消费和多线暧昧")
        if all_branches.count(taohua) >= 1:
            notes.append("原局桃花被流年引动→吸引力增强，也会放大感情波动")

    # 天喜合动+偏财/正财 (男) or 官星 (女)
    if ln_branch == tianxi:
        if gender == "男" and ln_shishen in (Shishen.偏财, Shishen.正财):
            strength = max(strength, 2)
            triggers.append("天喜+财星同现")
        elif gender == "女" and ln_shishen in (Shishen.偏官, Shishen.正官):
            strength = max(strength, 2)
            triggers.append("天喜+官星同现")

    # 流年支冲夫妻宫
    if _has_branch_interaction(day_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲夫妻宫")
        notes.append("夫妻宫逢冲→感情波动/分手可能性")

    # ── ★ 级别 ──
    # 空亡：降星+加备注（升级：统一降强度）
    kw = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw) and triggers:
        notes.append("流年落空亡→机会真实但结果虚浮不实（《三命通会》：吉神空亡则吉减半，非无吉也）")

    if ln_branch == hongluan:
        strength = max(strength, 1)
        if "红鸾" not in str(triggers):
            triggers.append("流年红鸾入命")

    if ln_shishen == spouse_star:
        strength = max(strength, 1)
        if spouse_star_name not in str(triggers):
            triggers.append(f"流年{spouse_star_name}透干")

    if ln_branch == taohua and strength < 2:
        strength = max(strength, 1)
        triggers.append("流年桃花")

    # 偏财/正财向正财过渡模式检查
    if gender == "男":
        if ln_shishen == Shishen.偏财:
            notes.append("偏财年→吸引/机会，看次年正财是否接得住")
        elif ln_shishen == Shishen.正财:
            notes.append("正财年→妻星出现，关系转正机会")

    if triggers:
        direction = "正面"
        # 校准数据驱动的方向修正（v0.7.0）
        _triggers_str = str(triggers)
        _notes_str = str(notes)

        # 夫妻宫逢冲+七杀 → 负面
        if "冲夫妻宫" in _triggers_str and ln_shishen == Shishen.偏官:
            direction = "负面"
            notes.append("冲夫妻宫+七杀→感情危机加剧 (段建业: 夫宫冲穿必离婚)")

        # 冲夫妻宫 → 负面
        if "冲夫妻宫" in _triggers_str or "分手" in _notes_str or ("卯辰穿" in _triggers_str and "天喜伴生" not in _triggers_str) or ("自刑" in _triggers_str and "伏吟" in _triggers_str):
            direction = "负面"
        elif "困扰" in _notes_str or "不稳" in _notes_str:
            direction = "中性"

        # ── v0.11.2: 双场景标注——不猜状态，两种情况都说清楚 ──
        if direction == "正面":
            notes.insert(0, "若单身→恋爱机会/脱单窗口；若已有对象→关系升温/深化/里程碑")
        elif direction == "负面":
            notes.insert(0, "若单身→烂桃花/感情困扰；若已有对象→感情危机/分手风险")
        else:
            notes.insert(0, "若单身→感情波动期，宜观望；若已有对象→关系平淡期或小摩擦")

        # v0.10.1: 仅≥★2桃花输出——★1弱信号(红鸾/桃花/配偶星透干/流年合夫妻宫)不独立发信号
        if strength >= 2:
            signals.append(EventSignal(
                category="桃花",
                direction=direction,
                strength=min(strength, 3),
                prediction=_make_prediction("桃花", direction, min(strength,3), triggers, notes),
                triggers=triggers,
                notes=notes,
                calibration_refs=[t for t in triggers if "校准" in t or "calibration" in str(t)],
            ))

    return signals

