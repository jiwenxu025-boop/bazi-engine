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
                          favorable: set[str] | None = None) -> list[EventSignal]:
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
    is_weak = cs_cai in ("死", "病", "绝", "墓")

    # ── 正面: 得财 ──
    if _has_tiangan_wuhe(ln_stem, day_master):
        hua_wx = TIANGAN_WUHE.get((ln_stem, day_master)) or TIANGAN_WUHE.get((day_master, ln_stem))
        if hua_wx and _is_ke_wx(day_master.wuxing, hua_wx):
            s.add(2 if is_weak else 4, "财来合我→化财", "身弱不担财→大额支出" if is_weak else "最直接的得财信号 (textbook)")

    if _has_branch_interaction(ln_branch, caiku, "六冲"):
        s.add(3, "冲开财库→财务重大变动", "喜财则发财/忌财则破财 (textbook)")

    # ── 墓库相冲核爆（v0.8.0: 涉及财库时升级为资金巨变）──
    from ...interactions import analyze_muku_chong
    muku_cai_check = [ln_branch]
    muku_cai_results = analyze_muku_chong(muku_cai_check, day_master, caiku_branch=caiku)
    for mr in muku_cai_results:
        if caiku in mr.pair:
            s.add(4, f"墓库相冲({mr.name})冲开财库→资金巨变",
                  f"土气×{mr.tu_boost}倍+财库冲开→"
                  f"{'暴富机会' if fav is not False else '大破财风险'}")
        else:
            # 墓库冲虽不涉财库，但全局五行失衡
            s.add(-2, f"墓库相冲({mr.name})→全局五行失衡",
                  "土气暴增→间接影响财运稳定", fixed=True)

    tianyi_cy = _TIANYI_FLAT.get(day_master)
    if is_cai and tianyi_cy and ln_branch in tianyi_cy:
        s.add(4, "财星+天乙贵人→贵人带财", "收入增+贵人助 (textbook)")

    if is_shishang and cs_cai in ("临官", "帝旺", "冠带"):
        s.add(3, "食伤生财+身强→财可得", "靠技能/创意赚钱 (textbook)")
    elif is_shishang:
        s.add(2, "食伤生财", "靠技能/创意赚钱" if fav is not False else "投机冲动消费")
        s.guarantee(2)

    if is_cai:
        cai_l = "正财" if ln_shishen == Shishen.正财 else "偏财"
        s.add(3, f"流年{cai_l}透干", f"{cai_l}年→财运关注 (textbook)")

    if is_piancai and ln_branch == yima:
        s.add(3, "偏财+驿马→远方得财/投资机会")

    cai_types_cy = (Shishen.正财, Shishen.偏财)
    if not is_cai:
        ln_cg_cy = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
        if any(c in cai_types_cy for c in ln_cg_cy):
            c_l = "正财" if Shishen.正财 in ln_cg_cy else "偏财"
            s.add(3, f"地支藏{c_l}→隐性得财", "暗财/偏门收入 (段建业)")

    # ── 负面: 破财 ──
    if is_jiecai and fav is not True:
        s.add(-2, "劫财夺财→破财/被借钱", "劫财为忌→注意破耗 (textbook)")
        s.guarantee(2)
    elif is_jiecai:
        s.add(-1, "劫财透干→开销增大")
    elif is_bijian:
        s.add(-1, "比肩透干→竞争分财/开销", "比肩年→注意同辈竞争 (textbook)" if fav is False else "比肩→社交开销增加")

    if is_cai and _has_branch_interaction(ln_branch, day_branch, "六冲"):
        s.add(-2, "财星+冲夫妻宫→财损风险")

    if lu_cai and _has_branch_interaction(ln_branch, lu_cai, "六冲"):
        s.add(-2, "冲禄→破财/花费大增")

    kw_cy = _kongwang_branches(day_master, day_branch)
    if _is_kongwang(ln_branch, kw_cy) and is_cai:
        s.add(-1, "财星落空亡→得财虚浮")

    if s.is_significant():
        magnitude = _wealth_magnitude(s.total)
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

    return signals

