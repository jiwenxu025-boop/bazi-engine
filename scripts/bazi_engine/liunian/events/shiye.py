"""事业/工作变动信号检测"""
from ..._constants import DIZHI_CANGGAN, YIMA
from ...enums import TIANGAN_LU, Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal, ScoreAccumulator
from ..utils import (
    _has_branch_interaction,
    _has_tiangan_wuhe,
    _is_ke_wx,
    _is_kongwang,
    _kongwang_branches,
    _make_prediction,
    is_favorable,
)


def detect_shiye_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                         day_master: Tiangan, year_branch: Dizhi,
                         month_branch: Dizhi,
                         day_branch: Dizhi,
                         hour_branch: Dizhi | None = None,
                         dayun_stem: Tiangan | None = None,
                         dayun_branch: Dizhi | None = None,
                         favorable: set[str] | None = None) -> list[EventSignal]:
    """检测事业/工作变动信号 — v0.5.0: 打分制"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    yima = YIMA.get(year_branch)
    lu = TIANGAN_LU.get(day_master)
    s = ScoreAccumulator(favorable)
    fav = is_favorable(ln_shishen, favorable)
    s.set_shishen(ln_shishen.value, fav)
    s.set_modulate(False)  # 事业只标记不调分（跳槽/晋升不因忌神而消失）

    is_guan = ln_shishen in (Shishen.正官, Shishen.偏官)
    is_ying = ln_shishen in (Shishen.正印, Shishen.偏印)
    is_shang = ln_shishen == Shishen.伤官
    is_shishang = ln_shishen in (Shishen.食神, Shishen.伤官)

    # ── 正面: 晋升/机会 ──
    if is_guan and _has_tiangan_wuhe(ln_stem, day_master):
        s.add(4, "官来合我→晋升/上级赏识", "流年官星合日主 (textbook)")

    # 财官双透
    cai_types = (Shishen.正财, Shishen.偏财)
    ln_cg = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
    if is_guan and any(c in cai_types for c in ln_cg):
        s.add(4, "财官双美→加薪+晋升同现", "财生官 (textbook)")

    # 官印相生
    if is_guan and dayun_stem and get_ten_god(day_master, dayun_stem) in (Shishen.正印, Shishen.偏印):
        s.add(3, "大运印+流年官→官印相生晋升")

    # 禄神到位（固定: 临官总是好事）
    if ln_branch == lu:
        s.add(3, "禄神到位→事业自我实现", "日主临官/能量充足", fixed=True)

    # 官星到位
    if is_guan:
        has_cai = any(c in cai_types for c in ln_cg)
        if has_cai:
            s.add(2, "官星到位+财生官", "间接晋升/加薪")
        else:
            s.add(2, "流年官星到位")

    # 杀印相生
    if ln_shishen == Shishen.偏官 and Shishen.偏印 in ln_cg:
        s.add(2, "偏官+偏印→杀印相生", "压力转化动力")

    # 地支藏官
    if not is_guan and any(c in (Shishen.正官, Shishen.偏官) for c in ln_cg):
        guan_l = "正官" if Shishen.正官 in ln_cg else "偏官"
        s.add(2, f"地支藏{guan_l}→隐性晋升机会")

    # 驿马+官/食伤/财 → 工作变动
    if ln_branch == yima:
        if is_guan:
            s.add(2, "驿马+官星→工作调动")
        elif is_shishang:
            s.add(1, "驿马+食伤→主动跳槽/创业")
        elif ln_shishen in (Shishen.正财, Shishen.偏财):
            s.add(1, "驿马+财星→为财换工作")
        else:
            s.add(1, "流年驿马")

    # 印星 → 入职签约（固定: 签约不因忌神失效）
    if is_ying:
        y_l = "正印" if ln_shishen == Shishen.正印 else "偏印"
        s.add(1, f"印星透干→签约/入职 ({y_l})", fixed=True)

    # 冲月柱(事业宫)（固定: 环境变动不因喜忌消失）
    if _has_branch_interaction(month_branch, ln_branch, "六冲"):
        s.add(1, "冲月柱(事业宫)→工作环境变动", fixed=True)

    # 冲时柱(门户)
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        s.add(1, "冲时柱→工作地点变动", fixed=True)

    # ── 负面: 挫折/风险 (方向固定，不受喜忌翻转) ──
    if is_shang:
        s.add(-1, "伤官透干→想改变/离职风险", "伤官=变革冲动 (textbook)", fixed=True)
        s.guarantee(2)

    if dayun_branch and _has_branch_interaction(dayun_branch, ln_branch, "六冲"):
        tianke = dayun_stem and ln_stem and _is_ke_wx(ln_stem.wuxing, dayun_stem.wuxing)
        s.add(-2 if tianke else -1, "天克地冲→重大变动" if tianke else "大运流年冲→环境变化", fixed=True)

    if is_guan:
        dn_s = get_ten_god(day_master, dayun_stem) if dayun_stem else None
        if dn_s in (Shishen.正官, Shishen.偏官) and dn_s != ln_shishen:
            s.add(-1, "官杀混杂→选择困难/多重压力", fixed=True)

    # 空亡
    if is_guan:
        kw_s = _kongwang_branches(day_master, day_branch)
        if _is_kongwang(ln_branch, kw_s) and s.total >= 2:
            s.add(-1, "官星落空亡→机会虚浮", fixed=True)

    if s.is_significant():
        signals.append(EventSignal(
            category="事业",
            direction=s.direction,
            strength=s.strength,
            prediction=_make_prediction("事业", s.direction, s.strength, s.triggers(), s.notes()),
            triggers=s.triggers(),
            notes=s.notes(),
        ))
    return signals

