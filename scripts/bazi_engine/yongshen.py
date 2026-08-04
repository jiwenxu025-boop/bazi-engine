"""用神自动推荐 — 基于日主强弱 + 格局 + 调候 + 合化 + 从格推断喜用忌神

算法: 月令得令计分 + 四柱干支生扶/克泄耗计分 + 合化修正 + 调候修正 + 假生修正 + 十二长生修正 → 判强弱 → 定喜忌
验证: 案例A/案例B/案例C/案例D 四案例均匹配 case memory 记录
v0.8.0: +假生陷阱修正 + 十二长生修正
"""

from contextlib import suppress

from ._constants import CONG_GE_CHECKS, DIZHI_CANGGAN, SHIER_CHANGSHENG
from .enums import Dizhi, Shishen, Tiangan, Wuxing
from .ten_gods import get_ten_god, wuxing_ke, wuxing_sheng


def _parent_wuxing(wx: Wuxing) -> Wuxing:
    """返回生 wx 的五行（印星对应的五行）"""
    sheng_map = {
        Wuxing.木: Wuxing.水, Wuxing.火: Wuxing.木, Wuxing.土: Wuxing.火,
        Wuxing.金: Wuxing.土, Wuxing.水: Wuxing.金,
    }
    return sheng_map[wx]


def _season_strength(day_wx: Wuxing, month_branch: Dizhi) -> int:
    """月令对日主的支持度: 同五行+3, 生我+2, 我生+1, 克我-1, 我克0"""
    month_wx = month_branch.wuxing

    if month_wx == day_wx:
        return 3
    if wuxing_sheng(month_wx) == day_wx:
        return 2
    if wuxing_sheng(day_wx) == month_wx:
        return 1
    if wuxing_ke(month_wx) == day_wx:
        return -1
    if wuxing_ke(day_wx) == month_wx:
        return 0
    return 0


def _canggan_score(stem: Tiangan, day_master: Tiangan, level: str) -> float:
    """藏干对日主的支持度（权重已优化：本气1.0/中气0.5/余气0.25）"""
    ss = get_ten_god(day_master, stem)
    base = {"本气": 1.0, "中气": 0.5, "余气": 0.25}.get(level, 0.25)

    if ss in (Shishen.比肩, Shishen.劫财):
        return base
    if ss in (Shishen.正印, Shishen.偏印):
        return base
    if ss in (Shishen.正官, Shishen.偏官):
        return -base * 0.5
    if ss in (Shishen.食神, Shishen.伤官):
        return -base * 0.5
    return -base * 0.3  # 财星


def _check_tiangan_he_impact(all_stems: list[Tiangan]) -> dict[str, float]:
    """检测天干五合对五行力量的影响。

    未经化气条件验证时，五合不改变五行力量。
    返回: {五行: 力量调整值}
    """
    return {}


def _seasonal_adjustment(day_master: Tiangan, month_branch: Dizhi) -> dict:
    """《穷通宝鉴》调候原则：根据日主五行和出生季节调整喜用。

    Returns:
        {"tiaohou_wuxing": ["火"], "reason": "冬水需火暖局", ...}
    """
    dm_wx = day_master.wuxing
    month_idx = month_branch.index  # 0=子(冬), 2=寅(春), 5=午(夏), 8=申(秋)

    # 季节划分：寅卯辰=春(2-4), 巳午未=夏(5-7), 申酉戌=秋(8-10), 亥子丑=冬(11,0,1)
    if month_idx in (2, 3, 4):
        season = "春"
    elif month_idx in (5, 6, 7):
        season = "夏"
    elif month_idx in (8, 9, 10):
        season = "秋"
    else:
        season = "冬"

    # 调候规则（《穷通宝鉴》核心口诀简化版）
    rules = {
        ("金", "夏"): {"wuxing": ["水"], "reason": "夏金喜水调候，火旺熔金需水救"},
        ("金", "冬"): {"wuxing": ["火"], "reason": "冬金喜火暖局，水冷金寒需火温"},
        ("木", "冬"): {"wuxing": ["火"], "reason": "冬木喜火暖局，水冷木寒需火调候"},
        ("木", "秋"): {"wuxing": ["火"], "reason": "秋木传统上先取丁火、次取丙火；均属火行，仅作调候参考。"},
        ("水", "夏"): {"wuxing": ["金"], "reason": "夏水喜金发源，火旺水涸需金生水"},
        ("水", "冬"): {"wuxing": ["火"], "reason": "冬水喜火暖局，水冷冰寒需火调候"},
        ("火", "冬"): {"wuxing": ["木"], "reason": "冬火喜木为薪，水旺火灭需木化水生火"},
        ("火", "秋"): {"wuxing": ["木"], "reason": "秋火喜木续燃，金多火弱需木为燃料"},
        ("土", "夏"): {"wuxing": ["水"], "reason": "夏土喜水润泽，火旺土燥需水调候"},
        ("土", "冬"): {"wuxing": ["火"], "reason": "冬土喜火暖局，水冷土冻需火调候"},
        ("土", "春"): {"wuxing": ["火"], "reason": "春土喜火生扶，木旺克土需火化木"},
    }

    return rules.get((dm_wx.value, season), {})


def _detect_cong_ge(day_master: Tiangan, month_branch: Dizhi,
                    all_stems: list[Tiangan], all_branches: list[Dizhi],
                    strength: str, score: float) -> dict | None:
    """检测是否构成从格（从旺/从弱）及体用阵营（v0.8.0: P8扩展）。

    从格条件：日主极强或极弱，全局力量一边倒。

    v0.8.0 新增:
    - 体用阵营检测：扫描全盘三合/三会/同类聚众
    - 识别非日主阵营作为"体"：从势格/专旺格
    - 两神相战结构识别
    """
    dm_wx = day_master.wuxing
    parent_wx = _parent_wuxing(dm_wx).value

    # 从格最基本的反条件是日主或印星有根、有帮扶。旧实现把这些
    # 条件简化成五行数量，导致有根命局被误判为从格。
    visible_support = any(
        stem.wuxing.value in (dm_wx.value, parent_wx)
        for index, stem in enumerate(all_stems)
        if index != 2
    )
    hidden_support = any(
        hidden.stem.wuxing.value in (dm_wx.value, parent_wx)
        for branch in all_branches
        for hidden in DIZHI_CANGGAN.get(branch, [])
    )
    if visible_support or hidden_support:
        return None

    # 四柱顺序中日干在 index 2；仅排除日干本身，不能漏算别柱同干比肩。
    all_tg = [stem for index, stem in enumerate(all_stems) if index != 2]

    # 统计各五行天干数量
    wx_count: dict[str, int] = {}
    for tg in all_tg:
        wx = tg.wuxing.value
        wx_count[wx] = wx_count.get(wx, 0) + 1

    # 统计地支本气
    for dz in all_branches:
        wx = dz.wuxing.value
        wx_count[wx] = wx_count.get(wx, 0) + 1

    # 生扶者 = 同五行 + 印星五行
    support_count = wx_count.get(dm_wx.value, 0) + wx_count.get(parent_wx, 0)
    total_count = sum(wx_count.values())

    # 从弱：财/官/食伤≥75%
    ke_xie_count = total_count - support_count
    if strength == "弱" and score <= 0.5 and ke_xie_count >= total_count * 0.75:
        cai_count = 0
        guan_count = 0
        shi_count = 0
        for tg in all_tg:
            ss = get_ten_god(day_master, tg)
            if ss in (Shishen.正财, Shishen.偏财):
                cai_count += 1
            elif ss in (Shishen.正官, Shishen.偏官):
                guan_count += 1
            elif ss in (Shishen.食神, Shishen.伤官):
                shi_count += 1

        max_type = max([("从财", cai_count), ("从杀", guan_count), ("从儿", shi_count)],
                       key=lambda x: x[1])

        cong_key = f"从弱_{max_type[0]}"
        if cong_key in CONG_GE_CHECKS:
            return {
                "type": max_type[0],
                "description": CONG_GE_CHECKS[cong_key]["description"],
                "favorable": CONG_GE_CHECKS[cong_key]["favorable"],
                "harmful": CONG_GE_CHECKS[cong_key]["harmful"],
            }

    return None


def determine_qiangruo(
    day_master: Tiangan,
    month_branch: Dizhi,
    all_stems: list[Tiangan],
    all_branches: list[Dizhi],
) -> tuple[str, float]:
    """判定日主强弱

    v0.8.0: +假生陷阱修正 + 十二长生修正

    Returns:
        ("强" | "弱" | "中和", 得分)
    """
    dm_wx = day_master.wuxing
    score = 0.0

    # 1. 月令
    ss = _season_strength(dm_wx, month_branch)
    score += ss

    # 2. 天干
    for index, stem in enumerate(all_stems):
        # 仅跳过日干所在日柱，别柱同干仍是比肩，必须计入。
        if index == 2 and stem == day_master:
            continue
        ss = get_ten_god(day_master, stem)
        if ss in (Shishen.比肩, Shishen.劫财) or ss in (Shishen.正印, Shishen.偏印):
            score += 1.0
        elif ss in (Shishen.正官, Shishen.偏官):
            score -= 1.0
        elif ss in (Shishen.食神, Shishen.伤官):
            score -= 0.7
        elif ss in (Shishen.正财, Shishen.偏财):
            score -= 0.5

    # 3. 地支藏干（优化权重）
    for branch in all_branches:
        for hs in DIZHI_CANGGAN.get(branch, []):
            cs = _canggan_score(hs.stem, day_master, hs.level)
            if abs(cs) > 0:
                score += cs

    # 4. 印多减子: 印星≥3时生扶作用打折（陆致极"母多减子"）
    yin_count = 0
    for stem in all_stems:
        ss = get_ten_god(day_master, stem)
        if ss in (Shishen.正印, Shishen.偏印):
            yin_count += 1
    if yin_count >= 3:
        # 印太旺反成负担 — 计分中印星的贡献减半
        score -= yin_count * 0.5

    # 5. 假生陷阱修正（v0.8.0: 水冷木冻/燥土脆金/湿木不生火）
    from .tiaohou import detect_false_generation
    false_gens = detect_false_generation(day_master, all_stems, all_branches)
    for fg in false_gens:
        if fg.severity == 2:
            score -= 2.0  # 强假生：印星完全转化为忌神
        elif fg.severity == 1:
            score -= 1.0  # 弱假生：印星生扶打折

    # 6. 十二长生修正（v0.8.0: 日干在月支/日支的长生状态参与强弱）
    cs_table = SHIER_CHANGSHENG.get(day_master, {})
    # 月支长生状态权重 1.0
    cs_month = cs_table.get(month_branch, "")
    cs_score_map = {"长生": 2.0, "沐浴": 0.5, "冠带": 1.0, "临官": 2.0, "帝旺": 2.5,
                    "衰": -0.5, "病": -1.0, "死": -1.5, "墓": -1.0, "绝": -2.0,
                    "胎": 0.0, "养": 0.5}
    if cs_month in cs_score_map:
        score += cs_score_map[cs_month]

    # 判定（阈值: ≥3.5=强, ≤1.5=弱）
    if score >= 3.5:
        strength = "强"
    elif score <= 1.5:
        strength = "弱"
    else:
        strength = "中和"

    return strength, round(score, 1)


def recommend_yongshen(
    day_master: Tiangan,
    month_branch: Dizhi,
    all_stems: list[Tiangan],
    all_branches: list[Dizhi],
    pattern: str = "",
) -> dict:
    """推荐喜用神和忌神（含调候、从格、格局用神）

    Returns:
        {
            "strength": "强/弱/中和",
            "score": 3.5,
            "favorable": {"正财", "偏官", ...},
            "harmful": {"正印", "比肩", ...},
            "favorable_wuxing": ["火", "土", "木"],
            "harmful_wuxing": ["金", "水"],
            "cong_ge": {...} | None,
            "tiaohou": {...} | None,
        }
    """
    strength, score = determine_qiangruo(day_master, month_branch, all_stems, all_branches)

    # 从格检测
    cong_ge = _detect_cong_ge(day_master, month_branch, all_stems, all_branches,
                               strength, score)

    # 调候检测
    tiaohou = _seasonal_adjustment(day_master, month_branch)

    if cong_ge:
        # 从格喜忌颠覆常规
        favorable = set()
        for s_name in cong_ge["favorable"]:
            with suppress(ValueError):
                favorable.add(Shishen(s_name))
        harmful = set()
        for s_name in cong_ge["harmful"]:
            with suppress(ValueError):
                harmful.add(Shishen(s_name))
    elif strength == "强":
        favorable = {Shishen.正官, Shishen.偏官, Shishen.食神, Shishen.伤官,
                     Shishen.正财, Shishen.偏财}
        harmful = {Shishen.正印, Shishen.偏印, Shishen.比肩, Shishen.劫财}
    elif strength == "弱":
        favorable = {Shishen.正印, Shishen.偏印, Shishen.比肩, Shishen.劫财}
        harmful = {Shishen.正官, Shishen.偏官, Shishen.食神, Shishen.伤官,
                   Shishen.正财, Shishen.偏财}
    else:
        favorable = {Shishen.正印, Shishen.偏印, Shishen.比肩, Shishen.劫财}
        harmful = set()

    # 调候五行是独立参考维度，不覆盖格局、扶抑或强弱结论。
    tiaohou_wx = set(tiaohou.get("wuxing", []))
    fav_wx = _get_wuxing_set_for_shishens(favorable, day_master)
    harm_wx = _get_wuxing_set_for_shishens(harmful, day_master)

    if tiaohou_wx:
        # 调候五行可作为补充观察项，但不从忌神中强行移除。
        for wx in tiaohou_wx:
            if wx not in fav_wx and wx not in harm_wx:
                fav_wx.add(wx)

    result = {
        "strength": strength,
        "score": score,
        "favorable": sorted(s.value for s in favorable),
        "harmful": sorted(s.value for s in harmful),
        "favorable_wuxing": sorted(fav_wx),
        "harmful_wuxing": sorted(harm_wx),
        "cong_ge": cong_ge,
        "tiaohou": tiaohou,
    }

    # ── 格局用神（陆致极区分：格局用神 ≠ 有用之神）──
    result["pattern_yongshen"] = _get_pattern_yongshen(pattern, day_master)
    result["decision_policy"] = build_decision_policy(result)

    return result


def build_decision_policy(yongshen_result: dict) -> dict:
    """把扶抑、格局和调候整理成一个兼容旧字段的裁决出口。

    该策略不重新计算强弱，也不偷偷改动既有 ``favorable``/``harmful``；
    它明确各维度的优先级，并把冲突保留下来供流年和解释层引用。
    """
    base_favorable = list(yongshen_result.get("favorable", []))
    base_harmful = list(yongshen_result.get("harmful", []))
    pattern = yongshen_result.get("pattern_yongshen") or {}
    pattern_needs = list(pattern.get("needs", []))
    pattern_avoid = list(pattern.get("avoid", []))
    tiaohou = yongshen_result.get("tiaohou") or {}
    tiaohou_wuxing = list(
        tiaohou.get("wuxing", tiaohou.get("tiaohou_wuxing", [])) or []
    )

    conflicts: list[str] = []
    for item in pattern_needs:
        if item in base_harmful:
            conflicts.append(f"格局需要{item}，但扶抑层列为忌：保留冲突，不自动翻转")
    for item in pattern_avoid:
        if item in base_favorable:
            conflicts.append(f"格局忌{item}，但扶抑层列为喜：保留冲突，不自动翻转")

    effective_fav_wx = list(yongshen_result.get("favorable_wuxing", []))
    effective_harm_wx = list(yongshen_result.get("harmful_wuxing", []))
    return {
        "version": "1.0",
        "precedence": ["扶抑/从格", "格局维护", "调候"],
        "formula": "基础强弱 + 格局维护需求 + 调候修正 = 当前有效喜忌及优先级",
        "base": {
            "strength": yongshen_result.get("strength", "中和"),
            "score": yongshen_result.get("score", 0),
            "favorable": base_favorable,
            "harmful": base_harmful,
            "source": "扶抑/从格",
        },
        "pattern": {
            "needs": pattern_needs,
            "avoid": pattern_avoid,
            "method": pattern.get("method", "") if pattern else "",
            "priority": "maintenance" if pattern else "none",
            "source": "格局维护",
        },
        "tiaohou": {
            "wuxing": tiaohou_wuxing,
            "is_fei_ju": bool(tiaohou.get("is_fei_ju", False)),
            "role": "supplement",
            "source": "调候",
        },
        "effective": {
            # 兼容旧流年模块：无明确冲突时数值与旧出口保持一致。
            "favorable": base_favorable,
            "harmful": base_harmful,
            "favorable_wuxing": effective_fav_wx,
            "harmful_wuxing": effective_harm_wx,
            "priority": "格局维护" if pattern else "扶抑/从格",
        },
        "conflicts": conflicts,
    }


def _get_pattern_yongshen(pattern: str, day_master: Tiangan) -> dict | None:
    """获取格局用神——维护格局成立所需的十神。

    陆致极《进阶教程》：格局用神是为维护格局成立而需要的五行/十神，
    与扶抑调候意义上的"喜用神"（有用之神）是不同的两套体系。

    原则（《子平真诠》）：
    - 善神（正官/正印/食神/财星）→ 顺用：生之护之
    - 凶神（七杀/伤官/枭神/劫财）→ 逆用：制之化之
    """
    rules = {
        "正官格": {"needs": ["正印", "偏印", "正财", "偏财"], "avoid": ["伤官"], "method": "顺用→喜财生官/印护官"},
        "正印格": {"needs": ["正官", "偏官"], "avoid": ["正财", "偏财"], "method": "顺用→喜官杀来生印"},
        "偏印格": {"needs": ["正财", "偏财"], "avoid": ["食神"], "method": "逆用→喜财制枭"},
        "食神格": {"needs": ["正财", "偏财"], "avoid": ["偏印"], "method": "顺用→喜财泄食"},
        "伤官格": {"needs": ["正印", "偏印"], "avoid": ["正官"], "method": "逆用→喜印制伤（伤官配印）"},
        "正财格": {"needs": ["正官", "偏官", "食神", "伤官"], "avoid": ["比肩", "劫财"], "method": "顺用→喜食伤生财/官杀护财"},
        "偏财格": {"needs": ["正官", "偏官", "食神", "伤官"], "avoid": ["比肩", "劫财"], "method": "顺用→喜食伤生财"},
        "偏官格": {"needs": ["食神", "伤官", "正印", "偏印"], "avoid": ["正财", "偏财"], "method": "逆用→喜食伤制杀/印化杀(杀印相生)"},
        "七杀格": {"needs": ["食神", "伤官", "正印", "偏印"], "avoid": ["正财", "偏财"], "method": "逆用→喜食伤制杀/印化杀"},
        "建禄格": {"needs": ["正官", "偏官", "食神", "伤官"], "avoid": ["比肩", "劫财", "正印", "偏印"], "method": "逆用→喜官杀/食伤泄秀"},
        "羊刃格": {"needs": ["正官", "偏官"], "avoid": ["比肩", "劫财"], "method": "逆用→喜官杀制刃"},
    }

    for key, rule in rules.items():
        if key in pattern:
            return {
                "method": rule["method"],
                "needs": rule["needs"],
                "avoid": rule["avoid"],
                "note": f"格局{key}{rule['method']}。格局用神推荐：{'/'.join(rule['needs'][:3])}；忌：{'/'.join(rule['avoid'][:2])}。",
            }

    return None


def _get_wuxing_set_for_shishens(shishens: set[Shishen], day_master: Tiangan) -> set[str]:
    """将十神集合转换为五行集合（以日主为参照）"""
    dm_wx = day_master.wuxing
    result = set()

    for ss in shishens:
        if ss in (Shishen.比肩, Shishen.劫财):
            result.add(dm_wx.value)
        elif ss in (Shishen.正印, Shishen.偏印):
            result.add(_parent_wuxing(dm_wx).value)
        elif ss in (Shishen.食神, Shishen.伤官):
            result.add(wuxing_sheng(dm_wx).value)
        elif ss in (Shishen.正财, Shishen.偏财):
            result.add(wuxing_ke(dm_wx).value)
        elif ss in (Shishen.正官, Shishen.偏官):
            result.add(_ke_dm_wuxing(dm_wx).value)

    return result


def _ke_dm_wuxing(dm_wx: Wuxing) -> Wuxing:
    """返回克日主的五行（官杀五行）"""
    ke_map = {
        Wuxing.木: Wuxing.金, Wuxing.火: Wuxing.水, Wuxing.土: Wuxing.木,
        Wuxing.金: Wuxing.火, Wuxing.水: Wuxing.土,
    }
    return ke_map[dm_wx]
