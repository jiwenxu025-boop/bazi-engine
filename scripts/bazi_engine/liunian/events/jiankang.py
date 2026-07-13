"""健康信号检测"""
from ..._constants import (
    DIAOKE,
    DIZHI_CANGGAN,
    SANGMEN,
    ZAISHA,
    chong_pair,
)
from ...enums import TIANGAN_LU, TIANGAN_YANGREN, Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal
from ..utils import (
    _changsheng_status,
    _has_branch_interaction,
    _is_kongwang,
    _kongwang_branches,
    _make_prediction,
    is_favorable,
)


def detect_jiankang_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                            day_branch: Dizhi, day_master: Tiangan,
                            year_branch: Dizhi,
                            dayun_stem: Tiangan | None = None,
                            dayun_branch: Dizhi | None = None,
                            favorable: set[str] | None = None,
                            all_branches: tuple[Dizhi, ...] = (),
                            health_profile: dict | None = None,
                            first_year: bool = False,
                            ) -> list[EventSignal]:
    """检测健康信号 — v0.10.0: +调候体质筛查 + 五行脏腑预警"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)

    strength = 0
    triggers = []
    notes = []

    fav = is_favorable(ln_shishen, favorable)

    # ── 多柱联动: 三合官杀局 ──
    # 流年+大运+原局三合官杀局 → 官杀过旺克身
    dm_wx = day_master.wuxing
    from ...enums import Wuxing
    ke_wx_map = {Wuxing.木: Wuxing.土, Wuxing.火: Wuxing.金, Wuxing.土: Wuxing.水,
                 Wuxing.金: Wuxing.木, Wuxing.水: Wuxing.火}
    guansha_wx = ke_wx_map.get(dm_wx)  # 克日主的五行=官杀

    if guansha_wx:
        # 找对应的三合局(如官杀=火→寅午戌)
        sanhe_wx = {Wuxing.木: {Dizhi.亥, Dizhi.卯, Dizhi.未},
                    Wuxing.火: {Dizhi.寅, Dizhi.午, Dizhi.戌},
                    Wuxing.金: {Dizhi.巳, Dizhi.酉, Dizhi.丑},
                    Wuxing.水: {Dizhi.申, Dizhi.子, Dizhi.辰}}
        target_trio = sanhe_wx.get(guansha_wx, set())
        # 收集所有相关地支
        all_dz = set(all_branches)
        if dayun_branch:
            all_dz.add(dayun_branch)
        all_dz.add(ln_branch)
        # 计算命中数
        hits = len(target_trio & all_dz)
        if hits >= 3:
            strength = 3
            triggers.append(f"三合官杀局(流年+大运+原局){hits}柱→克身重灾")
            notes.append("官杀汇聚成局→防重大疾病/手术/意外 (《渊海子平》)")

    # ── 多柱联动: 羊刃聚会 ──
    yangren_jk = TIANGAN_YANGREN.get(day_master)
    if yangren_jk:
        all_dz_y = set(all_branches)
        if dayun_branch:
            all_dz_y.add(dayun_branch)
        all_dz_y.add(ln_branch)
        yr_count = sum(1 for dz in all_dz_y if dz == yangren_jk)
        if yr_count >= 3:
            strength = max(strength, 3)
            triggers.append(f"羊刃聚会({yr_count}重)→血光/手术/中风")
            notes.append("多柱羊刃汇聚→防意外血光/心脑血管 (textbook: 五羊刃聚会中风案)")

    # ── 多柱联动: 墓库相冲核爆（v0.8.0）──
    # 流年引动原局/大运中辰戌或丑未冲 → 土气激增+杂气损毁
    # v0.10.1: 仅流年参与的墓库冲才触发年度健康信号（原局墓库冲是体质，非年度事件）
    # v0.11.1: 去重——同一流年支可能与原局+大运中相同地支形成多对，只计一次
    from ...interactions import analyze_muku_chong
    muku_branches = list(all_branches)
    if dayun_branch:
        muku_branches.append(dayun_branch)
    muku_branches.append(ln_branch)
    muku_results = analyze_muku_chong(muku_branches, day_master)
    seen_muku_names: set[str] = set()
    for mr in muku_results:
        if ln_branch not in mr.pair:
            continue  # 流年未参与→原局体质特征，非年度健康事件
        if mr.name in seen_muku_names:
            continue  # 已处理过的墓库冲类型（如原局戌+流年辰与大运戌+流年辰重复）
        seen_muku_names.add(mr.name)
        if mr.zaqi_damaged:
            strength = max(strength, 2)
            triggers.append(f"流年引动墓库相冲({mr.name})→杂气损毁")
            notes.append(mr.health_note)
            notes.append(f"土气×{mr.tu_boost}倍暴增→脾胃消化系统负担加重")
        if day_branch in mr.pair or (dayun_branch and dayun_branch in mr.pair):
            strength = max(strength, 3)
            triggers.append("墓库冲涉日柱/大运→重灾级")
            notes.append("墓库冲直击日主根基→防突发重病/手术")

    # ═══ ★★★ 级别 ═══

    # 岁运并临+日柱受冲（需要第二个凶信号才3★）
    is_suiyun_binglin = (dayun_stem == ln_stem and dayun_branch == ln_branch)
    if is_suiyun_binglin and _has_branch_interaction(day_branch, ln_branch, "六冲"):
        # 检查是否有额外凶信号（七杀/偏印/三刑等）
        has_extra = (ln_shishen in (Shishen.偏官, Shishen.偏印) or
                     _changsheng_status(day_master, ln_branch) in ("死", "绝"))
        if has_extra:
            strength = 3
            triggers.append("岁运并临+日柱受冲+凶星叠加")
            notes.append("多重凶信号叠加→需高度重视健康安全")
        else:
            strength = 2
            triggers.append("岁运并临+日柱受冲")
            notes.append("注意健康/安全，避免重大决策")

    # 羊刃逢冲 + 羊刃聚会（阴干+阳干通用）
    yangren = TIANGAN_YANGREN.get(day_master)
    if ln_branch == yangren:
        chong_target = chong_pair(ln_branch)
        if dayun_branch == chong_target:
            strength = 3
            triggers.append("羊刃逢冲+大运来冲")
            notes.append("大运冲流年羊刃→防意外血光/手术")
        elif _has_branch_interaction(ln_branch, chong_target, "六冲"):
            strength = max(strength, 2)
            triggers.append("羊刃逢冲")
            notes.append("羊刃逢冲→注意运动安全，避免冲突")

    # 流年临帝旺之地(禄/羊刃) → 对所有天干通用
    if not yangren:  # 阴干无羊刃时，禄/帝旺等同羊刃效应
        cs_temp = _changsheng_status(day_master, ln_branch)
        if cs_temp in ("帝旺", "临官"):
            # 临官+七杀/偏官叠加 → 旺极招灾
            has_sha_risk = any(
                get_ten_god(day_master, hs.stem) == Shishen.偏官
                for hs in DIZHI_CANGGAN.get(ln_branch, [])
            )
            if has_sha_risk:
                strength = max(strength, 2)
                triggers.append("流年临禄旺之地+藏七杀")
                notes.append("旺极+七杀→防意外血光/心脑血管 (textbook)")
            elif ln_branch == TIANGAN_LU.get(day_master):
                strength = max(strength, 1)
                triggers.append("流年临禄地")
                notes.append("禄地太旺→注意劳逸结合，防止过劳")

    # ═══ ★★ 级别 ═══

    # 岁运并临 (calibration: 2026 案例A，喜用非凶)
    if is_suiyun_binglin:
        strength = max(strength, 2)
        triggers.append("岁运并临")
        notes.append("岁运并临≠必然凶；喜用则凶性大减 (校准: 案例A2026)")

    # 日柱天克地冲（降级: 2★改为1★基础，有额外凶星才2★）
    if _has_branch_interaction(day_branch, ln_branch, "六冲"):
        if strength > 0:  # 已有其他健康信号→叠加
            strength = max(strength, 2)
            triggers.append("流年与日柱天克地冲→叠加")
        else:
            strength = max(strength, 1)
            triggers.append("流年冲日柱")
            notes.append("自身或配偶有波动，注意休息")

    # 日主入流年死/绝/病/墓（十二长生）— 仅叠加，需至少2个其他信号
    cs = _changsheng_status(day_master, ln_branch)
    if cs in ("死", "绝", "病", "墓") and strength >= 2:
        strength = max(strength, 2)
        triggers.append(f"日主入流年{cs}地→叠加")
        notes.append(f"日主临{cs}→健康低谷/精力不足 (textbook)")

    # 官杀攻身（七杀旺+无制）
    if ln_shishen == Shishen.偏官 and fav is False:
        strength = max(strength, 2)
        triggers.append("流年七杀攻身")
        notes.append("七杀为忌→压力伤害/意外风险 (textbook)")

    # 地支藏七杀+日主临衰地 → 隐性七杀攻身
    # 注意：十二长生"病/死/绝/墓"是流年气数，不等于全局身强弱
    if ln_shishen != Shishen.偏官:
        ln_canggan_sha = [get_ten_god(day_master, hs.stem) for hs in DIZHI_CANGGAN.get(ln_branch, [])]
        has_sha_in_branch = Shishen.偏官 in ln_canggan_sha
        cs_sha = _changsheng_status(day_master, ln_branch)
        if has_sha_in_branch and cs_sha in ("病", "死", "绝", "墓"):
            strength = max(strength, 2)
            triggers.append(f"流年地支藏七杀+日主临{cs_sha}地")
            notes.append(f"隐性七杀攻身+日主流年气衰(临{cs_sha})→健康风险/意外手术 (textbook)")

    # 枭神夺食
    if ln_shishen == Shishen.偏印 and not is_suiyun_binglin:
        # 检查是否有食神被夺（食神为日主所生+同性）
        # 简化：偏印年+地支含食神日主衰地
        shen_shishen = get_ten_god(day_master, ln_stem)
        if shen_shishen == Shishen.偏印:
            cs2 = _changsheng_status(day_master, ln_branch)
            if cs2 in ("病", "死", "绝"):
                strength = max(strength, 2)
                triggers.append("枭神夺食")
                notes.append("影响饮食消化/精神状态 (textbook)")

    # 三刑入命 — 仅叠加
    if strength >= 2:
        xt_hits = []
        if _has_branch_interaction(day_branch, ln_branch, "相刑"):
            xt_hits.append("日柱")
        if dayun_branch and _has_branch_interaction(dayun_branch, ln_branch, "相刑"):
            xt_hits.append("大运")
        # 自刑：必须有伏吟（流年支与四柱重复）才算
        if ln_branch in (Dizhi.辰, Dizhi.午, Dizhi.酉, Dizhi.亥):
            if day_branch == ln_branch:
                xt_hits.append("日柱自刑")
            elif dayun_branch == ln_branch:
                xt_hits.append("大运自刑")
        if xt_hits:
            strength = max(strength, 2)
            triggers.append(f"三刑入命({'&'.join(xt_hits)})")
            notes.append("刑入命→健康隐患/慢性问题 (textbook)")

    # ═══ ★ 级别 ═══

    # 灾煞/丧门/吊客 — 流年逢之叠加健康风险（2026-05-23 WebSearch 验证）
    zaisha_target = ZAISHA.get(year_branch)
    sangmen_target = SANGMEN.get(year_branch)
    diaoke_target = DIAOKE.get(year_branch)
    if zaisha_target and ln_branch == zaisha_target and strength >= 2:
        strength = max(strength, 2)
        triggers.append("流年逢灾煞→叠加")
        notes.append("灾煞(白虎)→防意外血光")
    if sangmen_target and ln_branch == sangmen_target and strength >= 2:
        strength = max(strength, 2)
        triggers.append("流年逢丧门→叠加")
        notes.append("丧门→注意家人健康/白事")
    if diaoke_target and ln_branch == diaoke_target and strength >= 2:
        strength = max(strength, 2)
        triggers.append("流年逢吊客→叠加")
        notes.append("吊客→注意六亲孝服")

    # 七杀透干
    if ln_shishen == Shishen.偏官:
        strength = max(strength, 1)
        triggers.append("流年七杀透干")
        # 凶星落空则凶减（WebSearch 2026-05-23 验证）
        kw_jk = _kongwang_branches(day_master, day_branch)
        if _is_kongwang(ln_branch, kw_jk):
            notes.append("七杀落空亡→凶性大减")
            strength = max(strength - 1, 1)
        elif fav is True:
            notes.append("七杀为喜→压力可控")
        elif fav is False:
            notes.append("七杀为忌→注意压力")

    # ── v0.10.0: 五行脏腑交叉引用 ──
    # 已有健康触发时，附加对应脏腑风险提示
    if triggers and health_profile:
        wx_risks = health_profile.get("wuxing_risks", [])
        if wx_risks:
            high_risks = [r for r in wx_risks if r["severity"] == "高"]
            if high_risks:
                organ_labels = "、".join(r["organ"] for r in high_risks[:3])
                notes.append(f"体质弱点（{organ_labels}）：{'; '.join(r['note'] for r in high_risks[:2])}")

    # ── v0.10.0: 调候体质基线筛查（首年输出体质画像）──
    if first_year and health_profile:
        tiaohou_label = health_profile.get("tiaohou_label", "")
        if "高风险" in tiaohou_label:
            strength = max(strength, 1)
            triggers.append(f"体质基线：{tiaohou_label}")
            for risk in health_profile.get("tiaohou_risks", [])[:2]:
                notes.append(risk)
            if health_profile.get("tiaohou_advice"):
                notes.append(health_profile["tiaohou_advice"])

    if triggers:
        signals.append(EventSignal(
            category="健康",
            direction="负面",
            strength=min(strength, 3),
            prediction=_make_prediction("健康", "负面", min(strength,3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals

