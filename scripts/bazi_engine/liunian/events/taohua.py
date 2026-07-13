"""桃花/感情信号检测"""
from ..._constants import DIZHI_LIUHE, HONGLUAN, TAOHUA, TIANXI
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

    Incorporates calibration rules from bazi-ganzhi-interactions.md:
    - 天喜合动 = 感情机遇打开 (2/2 verified)
    - 红鸾+伏吟 = 方向取决于有无自刑和前一年感情状态
    - 卯辰穿 = 负面人际/情绪困扰 (3/3)
    - v0.11.2: 双场景标注——每个信号同时说明单身和已有对象两种情况
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
    # 天喜合动 (calibration: 3/3 verified: 案例A2023卯戌合, 2026午戌半合, 案例B2022寅亥合)
    # 三种情况: 流年直接=天喜, 六合天喜, 半合/三合天喜
    if ln_branch == tianxi:
        strength = max(strength, 2)
        triggers.append("流年天喜入命")
        notes.append("天喜合动: 感情机遇打开 (校准 3/3)")
    elif _has_branch_interaction(ln_branch, tianxi, "六合"):
        strength = max(strength, 2)
        triggers.append(f"{ln_branch.value}{tianxi.value}合→天喜被合动")
        notes.append("天喜合动: 感情机遇打开 (校准 3/3)")
    elif tianxi and _is_in_same_sanhe(ln_branch, tianxi):
        strength = max(strength, 2)
        triggers.append(f"{ln_branch.value}{tianxi.value}半/三合→天喜被合动")
        notes.append("天喜合动: 感情机遇打开 (校准 3/3)")

    # 流年地支合日支
    if _has_branch_interaction(day_branch, ln_branch, "六合"):
        strength = max(strength, 2)
        triggers.append("流年合夫妻宫")

    # 桃花年
    if ln_branch == taohua:
        strength = max(strength, 2)
        triggers.append("流年桃花入命")

    # 红鸾+伏吟 (calibration: direction depends on自刑 and prev year)
    # 扩展至全部四柱伏吟，不限于日支
    if ln_branch == hongluan:
        fuyin_on_ri = ln_branch == day_branch
        fuyin_on_any = any(ln_branch == br for br in all_branches)
        has_zixing = fuyin_on_any and _has_branch_interaction(ln_branch, ln_branch, "自刑")

        if fuyin_on_ri and has_zixing:
            strength = max(strength, 2)
            triggers.append("红鸾入命+夫妻宫伏吟+自刑")
            notes.append("红鸾伏吟+自刑→倾向感情结束 (校准 1/2: 案例A2024)")
        elif fuyin_on_any and has_zixing:
            strength = max(strength, 2)
            triggers.append("红鸾入命+命局伏吟+自刑")
            notes.append("红鸾伏吟+自刑→情绪内耗/矛盾 (校准: 案例C2024)")
        elif fuyin_on_ri and prev_year_has_relationship:
            strength = max(strength, 2)
            triggers.append("红鸾入命+夫妻宫伏吟")
            notes.append("红鸾伏吟+前一年有感情→倾向节点性变化")
        elif fuyin_on_ri:
            strength = max(strength, 2)
            triggers.append("红鸾入命+夫妻宫伏吟")
            notes.append("红鸾伏吟+前一年空窗→倾向新开始 (校准 1/2: 案例B2022)")

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

    # 卯辰穿 (calibration: 3/3 负面) — 扩展至全部四柱
    tianxi_activated = (
        ln_branch == tianxi
        or (tianxi and (ln_branch, tianxi) in DIZHI_LIUHE)
    )
    # 检查流年是否与四柱中任一柱形成卯辰穿
    maochen_chuan = False
    maochen_on_ri = False
    for br in all_branches:
        if (Dizhi.卯, Dizhi.辰) in [(ln_branch, br), (br, ln_branch)]:
            maochen_chuan = True
            if br == day_branch:
                maochen_on_ri = True
    if maochen_chuan:
        if maochen_on_ri and tianxi_activated:
            strength = max(strength, 2)
            triggers.append("卯辰穿夫妻宫+天喜伴生")
            notes.append("卯辰穿+天喜伴生→可进入但根基不稳 (校准 1/1: 案例A2023)")
        elif maochen_on_ri:
            strength = max(strength, 2)
            triggers.append("卯辰穿夫妻宫")
            notes.append("卯辰穿→感情困扰/走不出来 (校准 3/3)")
        else:
            strength = max(strength, 2)
            triggers.append("卯辰穿命局")
            notes.append("卯辰穿→人际/情绪困扰 (校准: 案例B2023/案例C2023时柱)")

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

    # 劫财年+男命 → 感情竞争/分手风险 (即使无神煞)
    if ln_shishen == Shishen.劫财 and gender == "男":
        strength = max(strength, 2)
        triggers.append("劫财夺财→感情竞争风险")
        notes.append("劫财年→比劫夺财，感情易被第三者介入 (段建业: 比劫争妻)")
    if ln_shishen == Shishen.比肩 and gender == "男" and strength < 2:
        strength = max(strength, 1)
        triggers.append("比肩透干→同辈竞争可能影响感情")
        notes.append("比肩年→注意感情竞争 (段建业)")

    # 伤官年+女命 → 克夫/婚姻危机
    if ln_shishen == Shishen.伤官 and gender == "女":
        strength = max(strength, 2)
        triggers.append("伤官克官→婚姻危机")
        notes.append("伤官年→伤官见官，女命婚姻高危年 (段建业: 伤官运找不到老公)")

    # 伤官年+男命+合/冲夫妻宫 → 克妻/婚姻危机（v0.9.1: M14王宝强案）
    if ln_shishen == Shishen.伤官 and gender == "男":
        gong_he_taohua = _has_branch_interaction(day_branch, ln_branch, "六合")
        gong_chong_taohua = _has_branch_interaction(day_branch, ln_branch, "六冲")
        if gong_he_taohua or gong_chong_taohua:
            strength = max(strength, 3)
            triggers.append("伤官合/冲夫妻宫→婚灾信号")
            notes.append("男命伤官克正官+妻宫引动→克妻/婚姻危机 (《渊海子平》: 伤官见官为祸百端)")
        else:
            strength = max(strength, 2)
            triggers.append("伤官透干→感情波动")
            notes.append("男命伤官年→注意与伴侣口舌争执，克正官不利婚姻稳定")

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

        # 比劫夺财/争官 → 负面（第三者竞争信号）
        if ln_shishen == Shishen.劫财:
            if gender == "男":
                direction = "负面"
                notes.append("劫财夺财→感情竞争/第三者风险 (段建业: 比劫争夫/争妻)")
            elif gender == "女" and any("官" in t for t in triggers):
                direction = "负面"
                notes.append("劫财争合官星→感情竞争/三角关系 (段建业: 比劫争夫)")

        # 伤官见官(女命) → 负面（克夫信号）
        if gender == "女" and ln_shishen == Shishen.伤官:
            direction = "负面"
            notes.append("伤官见官→克夫/婚姻危机 (段建业: 伤官运找不到老公)")

        # 伤官见官(男命+妻宫引动) → 负面（克妻信号）v0.9.1
        if gender == "男" and ln_shishen == Shishen.伤官 and any("夫妻宫" in t or "妻宫" in t or "婚灾" in t for t in triggers):
            direction = "负面"
            notes.append("伤官克正官+妻宫引动→克妻/婚姻高危 (《渊海子平》: 伤官见官为祸百端)")

        # 夫妻宫逢冲+七杀 → 负面
        if "冲夫妻宫" in _triggers_str and ln_shishen == Shishen.偏官:
            direction = "负面"
            notes.append("冲夫妻宫+七杀→感情危机加剧 (段建业: 夫宫冲穿必离婚)")

        # 冲夫妻宫 → 负面
        if "冲夫妻宫" in _triggers_str or "分手" in _notes_str or ("卯辰穿" in _triggers_str and "天喜伴生" not in _triggers_str) or ("自刑" in _triggers_str and "伏吟" in _triggers_str):
            direction = "负面"
        # 卯辰穿+天喜伴生 → 中性（校准 1/1: 可进入但根基不稳）
        elif ("卯辰穿" in _triggers_str and "天喜伴生" in _triggers_str) or "困扰" in _notes_str or "不稳" in _notes_str:
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

