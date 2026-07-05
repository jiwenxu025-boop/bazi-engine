"""岁运交战处理器 — 流年 vs 大运冲突拦截。"""
from .._constants import DIZHI_LIUCHONG, DIZHI_LIUHE, DIZHI_XIANGHAI, DIZHI_XIANGXING
from .signal import EventSignal


def _process_suiyun_clash(ln_stem, ln_branch, dn_stem, dn_branch,
                           day_master, dayun_mod: dict | None) -> list[EventSignal]:
    """流年 vs 大运冲突拦截。

    优先级体系:
    - 太岁为君 (ROOT)，大运为臣 (ADMIN)
    - 天干冲(天战): 表层，事业/人际
    - 地支冲(地战): 底层，环境/健康/家庭 (比天干冲严重1.5-2倍)
    - 刑害不分局（无论喜忌一律负面）

    Returns:
        岁运交战产生的 EventSignal 列表
    """
    signals: list[EventSignal] = []


    has_conflict = False

    # ── 1. 天干冲（天战）──
    # 天干相克: 甲乙木克戊己土, 丙丁火克庚辛金, 戊己土克壬癸水, 庚辛金克甲乙木, 壬癸水克丙丁火
    from ..ten_gods import TIANGAN_KE_PAIRS
    ln_tg_val = ln_stem.value if hasattr(ln_stem, 'value') else str(ln_stem)
    dn_tg_val = dn_stem.value if hasattr(dn_stem, 'value') else str(dn_stem)
    tg_clash = (ln_tg_val, dn_tg_val) in TIANGAN_KE_PAIRS or (dn_tg_val, ln_tg_val) in TIANGAN_KE_PAIRS

    if tg_clash:
        # 判定大运天干是否为喜用
        dn_tg_fav = dayun_mod.get("stem_is_favorable") if dayun_mod else None
        if dn_tg_fav is True:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=2,
                prediction="岁运天战：流年克大运喜神→十年保护伞被太岁打破，事业/人际面临较大压力",
                triggers=[f"流年{ln_tg_val}克大运{dn_tg_val}(天战)"],
                notes=["岁运天战→权威之争/环境剧变", "大运天干为喜→保护被掀翻，压力增大"],
            ))
        elif dn_tg_fav is False:
            signals.append(EventSignal(
                category="状态",
                direction="正面",
                strength=1,
                prediction="岁运天战：流年克大运忌神→十年枷锁被太岁打破，困境出现转机",
                triggers=[f"流年{ln_tg_val}克大运{dn_tg_val}(天战)"],
                notes=["岁运天战→打破困局", "大运天干为忌→枷锁被破，转机出现"],
            ))
        else:
            signals.append(EventSignal(
                category="状态",
                direction="中性",
                strength=1,
                prediction="岁运天战：流年与大运天干相克，有权威之争或环境变化",
                triggers=[f"流年{ln_tg_val}克大运{dn_tg_val}(天战)"],
                notes=["岁运天战→注意职场人际摩擦"],
            ))
        has_conflict = True

    # ── 2. 地支冲（地战）── 比天干冲严重1.5-2倍
    dz_clash = (ln_branch, dn_branch) in DIZHI_LIUCHONG
    if dz_clash:
        dn_dz_fav = dayun_mod.get("branch_is_favorable") if dayun_mod else None
        if dn_dz_fav is True:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=3,
                prediction="岁运地战：流年冲大运喜神→十年根基被太岁动摇，环境/健康/家庭面临重大变动",
                triggers=[f"流年{ln_branch.value}冲大运{dn_branch.value}(地战)"],
                notes=["岁运地战→根基动摇，程度远大于天战",
                       "大运地支为喜→十年保护地基被破，重大变动"],
            ))
        elif dn_dz_fav is False:
            signals.append(EventSignal(
                category="状态",
                direction="正面",
                strength=2,
                prediction="岁运地战：流年冲大运忌神→十年困局被太岁打破根基，旧格局瓦解迎新生",
                triggers=[f"流年{ln_branch.value}冲大运{dn_branch.value}(地战)"],
                notes=["岁运地战→打破困局根基", "大运地支为忌→地基被翻，旧环境瓦解"],
            ))
        else:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=2,
                prediction="岁运地战：流年与大运地支相冲，环境/家庭有较大动荡",
                triggers=[f"流年{ln_branch.value}冲大运{dn_branch.value}(地战)"],
                notes=["岁运地战→根基动摇，注意家庭/居住环境变动"],
            ))
        has_conflict = True

    # ── 3. 岁运相刑/相害 ── 不分局，一律负面
    if not dz_clash:
        dz_xing = (ln_branch, dn_branch) in DIZHI_XIANGXING
        dz_hai = (ln_branch, dn_branch) in DIZHI_XIANGHAI
        if dz_xing:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=1,
                prediction="岁运相刑：流年与大运相刑，有慢性摩擦或法律/健康隐患",
                triggers=[f"流年{ln_branch.value}刑大运{dn_branch.value}"],
                notes=["岁运相刑→慢性损耗/官非隐忧（不分局）"],
            ))
            has_conflict = True
        if dz_hai:
            signals.append(EventSignal(
                category="状态",
                direction="负面",
                strength=1,
                prediction="岁运相害：流年与大运相害，有人际暗害或健康隐患",
                triggers=[f"流年{ln_branch.value}害大运{dn_branch.value}"],
                notes=["岁运相害→暗箭难防/隐性疾病（不分局）"],
            ))
            has_conflict = True

    # ── 4. 岁运相合 ── 中性偏吉，十年力量被引导到具体事件
    if not has_conflict:
        dz_he = (ln_branch, dn_branch) in DIZHI_LIUHE
        if dz_he:
            signals.append(EventSignal(
                category="状态",
                direction="正面",
                strength=1,
                prediction="岁运相合：流年与大运地支六合，十年积累的力量在这一年集中兑现",
                triggers=[f"流年{ln_branch.value}合大运{dn_branch.value}"],
                notes=["岁运相合→力量聚焦，十年势能转化为年度事件"],
            ))

    return signals

