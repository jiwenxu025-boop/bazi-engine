"""财运信号检测"""
from ..._constants import _TIANYI_FLAT, DIZHI_CANGGAN, TIANGAN_WUHE, YIMA
from ...enums import TIANGAN_LU, Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal, ScoreAccumulator
from ..utils import (
    _changsheng_status,
    _has_branch_interaction,
    _has_tiangan_wuhe,
    _is_ke_wx,
    _is_kongwang,
    _kongwang_branches,
    _make_prediction,
    _wealth_magnitude,
    get_caiku_branch,
    is_favorable,
)


def detect_caiyun_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                          day_master: Tiangan, year_branch: Dizhi,
                          day_branch: Dizhi,
                          favorable: set[str] | None = None,
                          all_branches: tuple[Dizhi, ...] = ()) -> list[EventSignal]:
    """检测财运信号 — v0.5.0: 打分制"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    s = ScoreAccumulator(favorable)
    fav = is_favorable(ln_shishen, favorable)
    s.set_shishen(ln_shishen.value, fav)

    is_cai = ln_shishen in (Shishen.正财, Shishen.偏财)
    is_piancai = ln_shishen == Shishen.偏财
    is_shishang = ln_shishen in (Shishen.食神, Shishen.伤官)
    is_bijian = ln_shishen == Shishen.比肩
    is_jiecai = ln_shishen == Shishen.劫财

    fav = is_favorable(ln_shishen, favorable)
    yima = YIMA.get(year_branch)
    caiku = get_caiku_branch(day_master)
    lu_cai = TIANGAN_LU.get(day_master)
    cs_cai = _changsheng_status(day_master, ln_branch)

    # ── 正面: 得财 ──
    if _has_tiangan_wuhe(ln_stem, day_master):
        hua_wx = TIANGAN_WUHE.get((ln_stem, day_master)) or TIANGAN_WUHE.get((day_master, ln_stem))
        if hua_wx and _is_ke_wx(day_master.wuxing, hua_wx):
            s.add(3, "财来合我", "合而是否化须另验，此处仅记录财务主题可能被引动。")

    if caiku in all_branches and _has_branch_interaction(ln_branch, caiku, "六冲"):
        s.add(2, "流年冲原局财库", "财务事项可能有调整；不推断发财或破财。")

    tianyi_cy = _TIANYI_FLAT.get(day_master)
    if is_cai and tianyi_cy and ln_branch in tianyi_cy:
        s.add(4, "财星+天乙贵人→协作主题", "财务与协作主题同时出现，需以现实条件核对结果。")

    if is_shishang and cs_cai in ("临官", "帝旺", "冠带"):
        s.add(3, "食伤生财→技能主题", "可关注技能或创意相关安排，不推断收入结果。")
    elif is_shishang:
        s.add(2, "食伤生财", "财务主题可与技能、创意或消费安排交叉核对。")
        s.guarantee(2)

    if is_cai:
        cai_l = "正财" if ln_shishen == Shishen.正财 else "偏财"
        s.add(3, f"流年{cai_l}透干", "财务主题候选，需以实际收支和合同信息为准。")

    if is_piancai and ln_branch == yima:
        s.add(3, "偏财+驿马→流动性财务主题")

    cai_types_cy = (Shishen.正财, Shishen.偏财)
    if not is_cai:
        ln_cg_cy = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
        if any(c in cai_types_cy for c in ln_cg_cy):
            c_l = "正财" if Shishen.正财 in ln_cg_cy else "偏财"
            s.add(3, f"地支藏{c_l}→非固定收入主题", "仅作财务主题候选，不推断收入来源或金额。")

    # ── 负面: 破财 ──
    if is_jiecai and fav is not True:
        s.add(-2, "劫财→支出与借贷检查", "可复核预算、借贷和合作安排，不推断损失。")
        s.guarantee(2)
    elif is_jiecai:
        s.add(-1, "劫财透干→开销增大")
    elif is_bijian:
        s.add(-1, "比肩透干→竞争分财/开销", "比肩年→注意同辈竞争 (textbook)" if fav is False else "比肩→社交开销增加")

    if is_cai and _has_branch_interaction(ln_branch, day_branch, "六冲"):
        s.add(-2, "财星+冲日柱→财务关系主题叠加")

    if lu_cai and _has_branch_interaction(ln_branch, lu_cai, "六冲"):
        s.add(-2, "冲禄→预算调整主题")

    kw_cy = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw_cy) and is_cai:
        s.add(-1, "财星落空亡→财务信号待验")

    if s.is_significant():
        magnitude = _wealth_magnitude(s.total, s.triggers())
        signals.append(EventSignal(
            category="财运",
            direction=s.direction,
            strength=s.strength,
            prediction=_make_prediction("财运", s.direction, s.strength, s.triggers(), s.notes()),
            triggers=s.triggers(),
            notes=s.notes(),
            magnitude=magnitude,
        ))
    return signals

