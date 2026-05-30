"""用神自动推荐 — 基于日主强弱 + 格局 + 调候 + 合化 + 从格推断喜用忌神

算法: 月令得令计分 + 四柱干支生扶/克泄耗计分 + 合化修正 + 调候修正 + 假生修正 + 十二长生修正 → 判强弱 → 定喜忌
验证: 案例A/案例B/案例C/案例D 四案例均匹配 case memory 记录
v0.8.0: +假生陷阱修正 + 十二长生修正
"""

from ._constants import CONG_GE_CHECKS, DIZHI_CANGGAN, SHIER_CHANGSHENG, TIANGAN_WUHE
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

    合化后，参与合的两干五行属性减弱。
    返回: {五行: 力量调整值}
    """
    adjustments: dict[str, float] = {}
    checked = set()

    for i, s1 in enumerate(all_stems):
        for j, s2 in enumerate(all_stems):
            if i >= j:
                continue
            pair = (s1, s2)
            if pair in TIANGAN_WUHE:
                key = tuple(sorted([s1.value, s2.value]))
                skey = str(key)
                if skey in checked:
                    continue
                checked.add(skey)
                hua_wx = TIANGAN_WUHE[pair]
                # 参与合的两干五行力量减弱，化神力量增强
                for s in (s1, s2):
                    wx = s.wuxing.value
                    adjustments[wx] = adjustments.get(wx, 0) - 0.5
                adjustments[hua_wx.value] = adjustments.get(hua_wx.value, 0) + 1.0

    return adjustments


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
        ("木", "秋"): {"wuxing": ["水"], "reason": "秋木凋零喜水滋润，金旺克木需水通关"},
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
    dm_stems = [day_master]
    all_tg = dm_stems + [s for s in all_stems if s != day_master]

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
    parent_wx = _parent_wuxing(dm_wx).value
    support_count = wx_count.get(dm_wx.value, 0) + wx_count.get(parent_wx, 0)
    total_count = sum(wx_count.values())

    # ── 体用阵营检测（v0.8.0: P8）──
    from ._constants import DIZHI_SANHE, DIZHI_SANHUI

    # 检测地支三合/三会 → 阵营加成
    camp_bonus: dict[str, int] = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for trio_set, wx in DIZHI_SANHE.items():
        trio = list(trio_set)
        matches = sum(1 for dz in all_branches if dz in trio)
        if matches >= 3:
            camp_bonus[wx.value] = camp_bonus.get(wx.value, 0) + 3
        elif matches == 2:
            camp_bonus[wx.value] = camp_bonus.get(wx.value, 0) + 1

    for trio_set, wx in DIZHI_SANHUI.items():
        trio = list(trio_set)
        matches = sum(1 for dz in all_branches if dz in trio)
        if matches >= 3:
            camp_bonus[wx.value] = camp_bonus.get(wx.value, 0) + 4  # 三会≥三合

    # 合并天干统计 + 地支三合/三会加成
    camp_power: dict[str, float] = {}
    for wx_name, count in wx_count.items():
        camp_power[wx_name] = count + camp_bonus.get(wx_name, 0)

    # 找出最强阵营
    if camp_power:
        dominant_camp = max(camp_power, key=camp_power.get)
        dominant_power = camp_power[dominant_camp]
        dm_power = camp_power.get(dm_wx.value, 0)
        dm_camp_power = dm_power + camp_power.get(parent_wx, 0)

        # 非日主阵营碾压：日主所在阵营≤40%且另一阵营≥60%
        total_power = sum(camp_power.values())
        if total_power > 0 and dm_camp_power <= total_power * 0.4:
            # 识别从势格/专旺格
            if dominant_camp != dm_wx.value and dominant_power >= total_power * 0.5:
                # 非日主五行成为全局主导 → 从势格
                result_type = f"从势({dominant_camp}旺)"
                fav_wx = _get_following_favorable(dominant_camp, dm_wx)
                return {
                    "type": result_type,
                    "description": f"全局{dominant_camp}气势成局（三合/三会/聚众），"
                                   f"日主{dm_wx.value}无力抗衡→以从{dominant_camp}之势为用。",
                    "favorable": fav_wx["favorable"],
                    "harmful": fav_wx["harmful"],
                }

    # 从旺：生扶者≥75%
    if strength == "强" and score >= 6.0 and support_count >= total_count * 0.75:
        return {
            "type": "从旺",
            "description": CONG_GE_CHECKS["从旺"]["description"],
            "favorable": CONG_GE_CHECKS["从旺"]["favorable"],
            "harmful": CONG_GE_CHECKS["从旺"]["harmful"],
        }

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


def _get_following_favorable(dominant_wx: str, dm_wx: Wuxing) -> dict:
    """计算从势格的喜忌：顺应主导五行阵营。

    原则：既然打不过，就加入。顺主导阵营之势为喜。
    """
    # 生主导五行者 = 喜（护持主导阵营）
    # 克主导五行者 = 忌（威胁主导阵营）
    _sheng_map = {"木": "水", "火": "木", "土": "火", "金": "土", "水": "金"}
    _ke_map = {"木": "金", "火": "水", "土": "木", "金": "火", "水": "土"}

    mom = _sheng_map.get(dominant_wx, "")
    enemy = _ke_map.get(dominant_wx, "")

    # 喜：主导五行 + 生主导者 + 食伤泄秀（主导五行的子）
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}

    return {
        "favorable": [dominant_wx, mom, sheng.get(dominant_wx, "")],
        "harmful": [enemy],
    }


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
    for stem in all_stems:
        if stem == day_master:
            continue
        ss = get_ten_god(day_master, stem)
        if ss in (Shishen.比肩, Shishen.劫财):
            score += 1.0
        elif ss in (Shishen.正印, Shishen.偏印):
            score += 1.0
        elif ss in (Shishen.正官, Shishen.偏官):
            score -= 1.0

    # 3. 天干合化修正
    he_adj = _check_tiangan_he_impact(all_stems)
    he_total = sum(he_adj.values())
    score += he_total * 0.5  # 合化影响权重0.5

    # 4. 地支藏干（优化权重）
    for branch in all_branches:
        for hs in DIZHI_CANGGAN.get(branch, []):
            cs = _canggan_score(hs.stem, day_master, hs.level)
            if abs(cs) > 0:
                score += cs

    # 5. 印多减子: 印星≥3时生扶作用打折（陆致极"母多减子"）
    yin_count = 0
    for stem in all_stems:
        ss = get_ten_god(day_master, stem)
        if ss in (Shishen.正印, Shishen.偏印):
            yin_count += 1
    if yin_count >= 3:
        # 印太旺反成负担 — 计分中印星的贡献减半
        score -= yin_count * 0.5

    # 6. 假生陷阱修正（v0.8.0: 水冷木冻/燥土脆金/湿木不生火）
    from .tiaohou import detect_false_generation
    false_gens = detect_false_generation(day_master, all_stems, all_branches)
    for fg in false_gens:
        if fg.severity == 2:
            score -= 2.0  # 强假生：印星完全转化为忌神
        elif fg.severity == 1:
            score -= 1.0  # 弱假生：印星生扶打折

    # 7. 十二长生修正（v0.8.0: 日干在月支/日支的长生状态参与强弱）
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
            try:
                favorable.add(Shishen(s_name))
            except ValueError:
                pass
        harmful = set()
        for s_name in cong_ge["harmful"]:
            try:
                harmful.add(Shishen(s_name))
            except ValueError:
                pass
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

    # 调候修正：调候五行优先加入喜用
    tiaohou_wx = set(tiaohou.get("wuxing", []))
    fav_wx = _get_wuxing_set_for_shishens(favorable, day_master)
    harm_wx = _get_wuxing_set_for_shishens(harmful, day_master)

    if tiaohou_wx:
        # 调候五行如果不在喜用中，添加进去（调候优先）
        for wx in tiaohou_wx:
            if wx not in fav_wx and wx not in harm_wx:
                fav_wx.add(wx)
        # 从忌神中移除调候五行
        harm_wx = harm_wx - tiaohou_wx

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

    return result


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
