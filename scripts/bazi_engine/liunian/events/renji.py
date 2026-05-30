"""人际关系信号检测"""
from ..._constants import TIANXI
from ...enums import Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal
from ..utils import (
    _has_branch_interaction,
    _is_in_same_sanhe,
    _make_prediction,
    is_favorable,
)


def detect_renji_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          year_branch: Dizhi, month_branch: Dizhi,
                          day_branch: Dizhi, hour_branch: Dizhi,
                          day_master: Tiangan,
                          all_branches: tuple[Dizhi, ...],
                          favorable: set[str] | None = None) -> list[EventSignal]:
    """检测人际关系信号（朋友/同事/社交）— v0.4.0"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    strength = 0
    triggers = []
    notes = []

    is_bijian = ln_shishen == Shishen.比肩
    is_jiecai = ln_shishen == Shishen.劫财
    is_shang = ln_shishen == Shishen.伤官
    fav = is_favorable(ln_shishen, favorable)

    # ── ★★★: 三刑汇聚 ──
    # 流年+命局凑齐三刑(寅巳申/丑未戌/子卯)
    sanxing_sets = [
        ({Dizhi.寅, Dizhi.巳, Dizhi.申}, "寅巳申三刑→官非/人际重大冲突"),
        ({Dizhi.丑, Dizhi.未, Dizhi.戌}, "丑未戌三刑→口舌/纠纷"),
    ]
    for trio, label in sanxing_sets:
        yr_set = set(all_branches)
        yr_set.add(ln_branch)
        if len(trio & yr_set) >= 3:  # 流年+原局凑齐三刑
            strength = max(strength, 3)
            triggers.append(label)
            notes.append("三刑汇聚→重大人际冲突/官非 (《渊海子平》)")
            break

    # ── ★★: 卯辰穿/子未穿等相害 ──
    # 日支参与的害更严重，非日支也有影响
    for br in all_branches:
        if _has_branch_interaction(ln_branch, br, "相害"):
            hai_pair = f"{ln_branch.value}{br.value}"
            if br == day_branch:
                strength = max(strength, 2)
                triggers.append(f"{hai_pair}穿夫妻宫→人际困扰")
                notes.append("夫妻宫被穿→情绪/人际受影响 (textbook)")
            elif br == month_branch:
                strength = max(strength, 2)
                triggers.append(f"{hai_pair}穿月柱→职场人际摩擦")
                notes.append("穿月柱→同事/朋友关系受损")
            else:
                strength = max(strength, 1)
                if not any("穿" in t for t in triggers):
                    triggers.append(f"{hai_pair}穿→隐性人际摩擦")

    # ── ★★: 相刑 ──
    has_xing = False
    for br in all_branches:
        if _has_branch_interaction(ln_branch, br, "相刑"):
            has_xing = True
            break
    if has_xing:
        strength = max(strength, 2)
        triggers.append("流年与原局相刑")
        notes.append("刑→人际摩擦/口舌是非 (textbook)")

    # ── ★★: 比劫夺财/争官 → 人际竞争 ──
    if is_jiecai and fav is not True:
        strength = max(strength, 2)
        triggers.append("劫财透干→朋友竞争/被借钱")
        notes.append("劫财→人际竞争加剧，慎防被友拖累 (段建业)")
    elif is_bijian and fav is False:
        strength = max(strength, 1)
        triggers.append("比肩透干→同辈竞争")
        notes.append("比肩→注意同辈间的竞争比较")

    # ── ★★: 伤官+人际 → 口舌惹事 ──
    if is_shang:
        strength = max(strength, 1)
        triggers.append("伤官透干→言语直接易得罪人")
        notes.append("伤官→直言不讳，注意言语冲突")

    # ── ★: 流年合动 → 社交活跃 ──
    for br in all_branches:
        if _has_branch_interaction(ln_branch, br, "六合"):
            if strength < 2:
                strength = max(strength, 1)
                triggers.append("流年合动→社交活跃")
                notes.append("六合→人缘好/社交机会多")
            break

    # ── ★: 天喜合动 → 社交活跃 ──
    tianxi_rj = TIANXI.get(year_branch)
    if tianxi_rj and (ln_branch == tianxi_rj or _is_in_same_sanhe(ln_branch, tianxi_rj)):
        strength = max(strength, 1)
        triggers.append("流年合动天喜→社交活跃")
        notes.append("天喜年→人缘提升/社交机会增多")

    if triggers:
        is_negative = any(kw in str(triggers) for kw in ["刑", "穿", "劫财", "伤官"])
        direction = "负面" if is_negative else "正面"
        # v0.10.1: 仅≥★2输出——★1弱信号不独立发信号
        if strength >= 2:
            signals.append(EventSignal(
                category="人际",
                direction=direction,
                strength=min(strength, 3),
                prediction=_make_prediction("人际", direction, min(strength, 3), triggers, notes),
                triggers=triggers,
                notes=notes,
            ))
    return signals

