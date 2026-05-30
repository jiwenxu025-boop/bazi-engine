"""加权十神计算"""
from ..enums import Tiangan, Dizhi, Wuxing, Shishen
from .._constants import DIZHI_CANGGAN, DIZHI_LIUHE, DIZHI_SANHE, STEM_TO_WUXING, BRANCH_TO_WUXING
from .constants import (
    TOUGAN_WEIGHT, HIDDEN_WEIGHTS, MONTH_MULTIPLIER,
    SAME_PILLAR_BONUS, HEJU_WEIGHTS,
)


def _extract_heju_wuxing(interactions: dict) -> dict[str, float]:
    """从 interactions 中提取合局化神五行 → 加成权重。

    三合/半合/三会/六合的 result 字段格式为 "化X"（X=五行）。
    返回 {五行: 累计加成}。
    """
    wuxing_bonus = {}
    dizhi_list = interactions.get("dizhi", [])
    for inter in dizhi_list:
        itype = inter.get("type", "")
        weight = HEJU_WEIGHTS.get(itype, 0)
        if weight <= 0:
            continue
        result = inter.get("result", "")
        if result.startswith("化"):
            wx = result[1:]  # "化火" → "火"
            wuxing_bonus[wx] = wuxing_bonus.get(wx, 0) + weight
    return wuxing_bonus

def _get_month_branch_wuxing(pillars_data: list[dict]) -> str | None:
    """获取月支本气五行（月令当权之气）"""
    month_pillar = pillars_data[1] if len(pillars_data) > 1 else None
    if not month_pillar:
        return None
    hidden = month_pillar.get("hidden_stems", [])
    if hidden:
        first = hidden[0]  # 本气
        return STEM_TO_WUXING.get(first["stem"])
    return BRANCH_TO_WUXING.get(month_pillar.get("branch", ""))

def _compute_weighted_shishen(
    pillars_data: list[dict],
    interactions: dict,
) -> dict[str, float]:
    """计算十神加权强度。

    计分规则（按优先级）：
    1. 透干 +3.0 / 藏干 本气+2.0 中气+1.5 余气+1.0
    2. 月令加成：与月支本气同五行的所有十神 ×1.5
    3. 同柱共振：天干与藏干同一十神 +1.0
    4. 合局化神：三合/三会/六合的化神五行对应的十神 +2.0~3.0

    Returns:
        {十神名: 加权分数}
    """
    scores = {}

    def _add(ten_god: str, weight: float):
        if ten_god:
            scores[ten_god] = scores.get(ten_god, 0) + weight

    # Step 1: 基础计分
    for p in pillars_data:
        tg = p.get("ten_god")
        stem_wx = STEM_TO_WUXING.get(p.get("stem", ""), "")
        hidden = p.get("hidden_stems", [])
        hidden_tgs = p.get("hidden_ten_gods", [])

        # 透干
        if tg:
            _add(tg, TOUGAN_WEIGHT)

        # 藏干
        for i, hs_name in enumerate(hidden_tgs):
            level = hidden[i]["level"] if i < len(hidden) else "余气"
            w = HIDDEN_WEIGHTS.get(level, 1.0)
            _add(hs_name, w)

    # Step 2: 月令加成
    month_wx = _get_month_branch_wuxing(pillars_data)
    if month_wx:
        for p in pillars_data:
            tg = p.get("ten_god")
            stem = p.get("stem", "")
            if tg and STEM_TO_WUXING.get(stem) == month_wx:
                _add(tg, TOUGAN_WEIGHT * (MONTH_MULTIPLIER - 1.0))
            hidden = p.get("hidden_stems", [])
            hidden_tgs = p.get("hidden_ten_gods", [])
            for i, hs_name in enumerate(hidden_tgs):
                hs_stem = hidden[i]["stem"] if i < len(hidden) else ""
                if STEM_TO_WUXING.get(hs_stem) == month_wx:
                    level = hidden[i]["level"] if i < len(hidden) else "余气"
                    base_w = HIDDEN_WEIGHTS.get(level, 1.0)
                    _add(hs_name, base_w * (MONTH_MULTIPLIER - 1.0))

    # Step 3: 同柱共振
    for p in pillars_data:
        tg = p.get("ten_god")
        hidden_tgs = p.get("hidden_ten_gods", [])
        if tg and tg in hidden_tgs:
            _add(tg, SAME_PILLAR_BONUS)

    # Step 4: 合局化神加成
    heju_bonus = _extract_heju_wuxing(interactions)
    for wx, bonus in heju_bonus.items():
        for p in pillars_data:
            tg = p.get("ten_god")
            stem = p.get("stem", "")
            if tg and STEM_TO_WUXING.get(stem) == wx:
                _add(tg, bonus)
            hidden = p.get("hidden_stems", [])
            hidden_tgs = p.get("hidden_ten_gods", [])
            for i, hs_name in enumerate(hidden_tgs):
                hs_stem = hidden[i]["stem"] if i < len(hidden) else ""
                if STEM_TO_WUXING.get(hs_stem) == wx:
                    _add(hs_name, bonus)

    return scores

def _count_ten_gods(pillars_data: list[dict]) -> dict[str, dict]:
    """统计每个十神出现次数、是否透干、宫位分布"""
    counts: dict[str, dict] = {}
    for p in pillars_data:
        tg_name = p.get("ten_god")
        if tg_name is None:
            continue
        if tg_name not in counts:
            counts[tg_name] = {"count": 0, "tougan": False, "pillars": []}
        counts[tg_name]["count"] += 1
        counts[tg_name]["pillars"].append(p["pillar_type"])
        if p.get("source") == "stem":
            counts[tg_name]["tougan"] = True
    return counts

def _get_hidden_ten_gods_flat(pillars_data: list[dict]) -> list[str]:
    """提取所有藏干十神（扁平列表）"""
    result = []
    for p in pillars_data:
        for hs_name in p.get("hidden_ten_gods", []):
            result.append(hs_name)
    return result

def _find_dominant_shishen(pillars_data: list[dict],
                           harmful_shishen: list[str],
                           interactions: dict | None = None) -> tuple[str, bool, str]:
    """找出最旺十神，返回 (十神名, 是否喜用, 性格描述)

    v0.11.0: 使用加权算法（透干3.0/藏干本气2.0中气1.5余气1.0/月令×1.5/同柱共振+1/合局加成）
    """
    scores = _compute_weighted_shishen(pillars_data, interactions or {})
    if not scores:
        return ("", True, "")

    # 按加权分数降序排列
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_items[0][0]
    dominant_score = sorted_items[0][1]

    is_fav = dominant not in harmful_shishen

    personality_entry = SHISHEN_PERSONALITY.get(dominant)
    if personality_entry:
        desc = personality_entry[0] if is_fav else personality_entry[1]
    else:
        desc = ""

    return (dominant, is_fav, desc)

def get_weighted_shishen_report(pillars_data: list[dict],
                                 interactions: dict) -> dict:
    """返回完整的十神加权报告，供病药检测和 LLM 融合引擎使用。

    Returns:
        {
            "scores": {十神: 加权分数},
            "top3": [(十神, 分数), ...],
            "month_wuxing": 月令五行 or None,
            "heju_wuxing": {五行: 加成},
        }
    """
    scores = _compute_weighted_shishen(pillars_data, interactions)
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {
        "scores": scores,
        "top3": sorted_items[:3],
        "month_wuxing": _get_month_branch_wuxing(pillars_data),
        "heju_wuxing": _extract_heju_wuxing(interactions),
    }

