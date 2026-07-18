"""加权十神计算"""
from .._constants import BRANCH_TO_WUXING, STEM_TO_WUXING
from .constants import (
    HIDDEN_WEIGHTS,
    MONTH_MULTIPLIER,
    SAME_PILLAR_BONUS,
    SHISHEN_PERSONALITY,
    TOUGAN_WEIGHT,
)


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

_WEIGHT_COMPONENTS = (
    "tougan",
    "hidden",
    "month_bonus",
    "same_pillar_bonus",
)


def _compute_weighted_shishen_with_breakdown(
    pillars_data: list[dict],
    interactions: dict,
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    """计算十神加权强度，同时记录每类加分的贡献。

    计分规则（按优先级）：
    1. 透干 +3.0 / 藏干 本气+2.0 中气+1.5 余气+1.0
    2. 月令加成：与月支本气同五行的所有十神 ×1.5
    3. 同柱共振：天干与藏干同一十神 +1.0
    合、会关系只记录为候选；未经化局条件验证，不改变十神权重。

    Returns:
        ({十神名: 加权分数}, {十神名: 各分项贡献})
    """
    scores: dict[str, float] = {}
    breakdown: dict[str, dict[str, float]] = {}

    def _add(ten_god: str, weight: float, component: str):
        if ten_god:
            scores[ten_god] = scores.get(ten_god, 0) + weight
            entry = breakdown.setdefault(
                ten_god,
                {name: 0.0 for name in _WEIGHT_COMPONENTS},
            )
            entry[component] += weight

    # Step 1: 基础计分
    for p in pillars_data:
        tg = p.get("ten_god")
        STEM_TO_WUXING.get(p.get("stem", ""), "")
        hidden = p.get("hidden_stems", [])
        hidden_tgs = p.get("hidden_ten_gods", [])

        # 透干
        if tg:
            _add(tg, TOUGAN_WEIGHT, "tougan")

        # 藏干
        for i, hs_name in enumerate(hidden_tgs):
            level = hidden[i]["level"] if i < len(hidden) else "余气"
            w = HIDDEN_WEIGHTS.get(level, 1.0)
            _add(hs_name, w, "hidden")

    # Step 2: 月令加成
    month_wx = _get_month_branch_wuxing(pillars_data)
    if month_wx:
        for p in pillars_data:
            tg = p.get("ten_god")
            stem = p.get("stem", "")
            if tg and STEM_TO_WUXING.get(stem) == month_wx:
                _add(
                    tg,
                    TOUGAN_WEIGHT * (MONTH_MULTIPLIER - 1.0),
                    "month_bonus",
                )
            hidden = p.get("hidden_stems", [])
            hidden_tgs = p.get("hidden_ten_gods", [])
            for i, hs_name in enumerate(hidden_tgs):
                hs_stem = hidden[i]["stem"] if i < len(hidden) else ""
                if STEM_TO_WUXING.get(hs_stem) == month_wx:
                    level = hidden[i]["level"] if i < len(hidden) else "余气"
                    base_w = HIDDEN_WEIGHTS.get(level, 1.0)
                    _add(
                        hs_name,
                        base_w * (MONTH_MULTIPLIER - 1.0),
                        "month_bonus",
                    )

    # Step 3: 同柱共振
    for p in pillars_data:
        tg = p.get("ten_god")
        hidden_tgs = p.get("hidden_ten_gods", [])
        if tg and tg in hidden_tgs:
            _add(tg, SAME_PILLAR_BONUS, "same_pillar_bonus")

    for ten_god, score in scores.items():
        breakdown[ten_god]["total"] = score

    return scores, breakdown


def _compute_weighted_shishen(
    pillars_data: list[dict],
    interactions: dict,
) -> dict[str, float]:
    """计算十神加权强度，保留原有公开内部接口。"""
    scores, _breakdown = _compute_weighted_shishen_with_breakdown(
        pillars_data,
        interactions,
    )
    return scores


def _build_scale_metadata() -> dict:
    """返回当前量表口径和参数快照，避免把内部积分误作绝对量表。"""
    return {
        "aggregation": "unbounded_additive",
        "comparison_scope": "absolute_engine_heuristic",
        "ranking_scope": "within_chart_only",
        "banding_scope": "fixed_engine_thresholds",
        "provenance": "engineering_heuristic",
        "relationship_policy": "candidates_do_not_change_weight",
        "parameter_snapshot": {
            "tougan_weight": TOUGAN_WEIGHT,
            "hidden_weights": dict(HIDDEN_WEIGHTS),
            "month_multiplier": MONTH_MULTIPLIER,
            "same_pillar_bonus": SAME_PILLAR_BONUS,
        },
    }

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

    使用加权算法（透干3.0/藏干本气2.0中气1.5余气1.0/月令×1.5/同柱共振+1）。
    合、会候选未经成局条件验证，不参与加权。
    """
    scores = _compute_weighted_shishen(pillars_data, interactions or {})
    if not scores:
        return ("", True, "")

    # 按加权分数降序排列
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    dominant = sorted_items[0][0]

    is_fav = dominant not in harmful_shishen

    personality_entry = SHISHEN_PERSONALITY.get(dominant)
    desc = (personality_entry[0] if is_fav else personality_entry[1]) if personality_entry else ""

    return (dominant, is_fav, desc)

def get_weighted_shishen_report(pillars_data: list[dict],
                                 interactions: dict) -> dict:
    """返回完整的十神加权报告，供病药检测和 LLM 融合引擎使用。

    Returns:
        {
            "scores": {十神: 加权分数},
            "breakdown": {十神: 各分项贡献},
            "top3": [(十神, 分数), ...],
            "month_wuxing": 月令五行 or None,
            "heju_wuxing": {},  # 兼容旧字段；候选关系不自动加权
            "scale_metadata": 量表口径和参数快照,
        }
    """
    scores, breakdown = _compute_weighted_shishen_with_breakdown(
        pillars_data,
        interactions,
    )
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return {
        "scores": scores,
        "breakdown": breakdown,
        "top3": sorted_items[:3],
        "month_wuxing": _get_month_branch_wuxing(pillars_data),
        "heju_wuxing": {},
        "scale_metadata": _build_scale_metadata(),
    }

