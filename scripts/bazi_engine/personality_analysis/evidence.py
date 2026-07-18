"""Public evidence view for personality scoring and fusion inputs."""

from typing import Any

WEIGHTED_SCORE_THRESHOLDS = {
    "medium": 2.0,
    "high": 5.0,
}

_WEIGHTED_SIGNAL_FIELDS: dict[str, tuple[str, ...]] = {
    "社交": ("表达欲", "群体融入", "内敛度", "拘谨度"),
    "感情": ("责任感_官杀", "欲望_财星", "同辈竞争_比劫", "独立反叛_伤官"),
    "决策": ("果断度_七杀", "分析度_印星", "直觉度_食伤", "伤官倾向", "食神倾向"),
    "内心": ("精神世界_偏印", "自洽度_食神", "自我意识_比劫"),
    "财富观": ("欲望_财星", "散财_比劫", "创造力变现_食伤", "储蓄保守_印星"),
}

_SIGNAL_COMPONENT_COUNTS = {
    "表达欲": 2,
    "群体融入": 2,
    "内敛度": 2,
    "拘谨度": 2,
    "责任感_官杀": 2,
    "欲望_财星": 2,
    "同辈竞争_比劫": 2,
    "分析度_印星": 2,
    "直觉度_食伤": 2,
    "自我意识_比劫": 2,
    "散财_比劫": 2,
    "创造力变现_食伤": 2,
    "储蓄保守_印星": 2,
}

_CAREER_FIELDS = ("体制_管理", "商业_经营", "技术_创意", "学术_专业", "创业_独立")
_DIMENSION_ORDER = ("社交", "感情", "内心", "决策", "事业", "财富观")
_FIELD_DISPLAY_LABELS = {
    "表达欲": "主动表达",
    "群体融入": "群体融入",
    "内敛度": "观察与保留",
    "拘谨度": "规则与分寸",
    "责任感_官杀": "关系责任",
    "欲望_财星": "资源目标",
    "同辈竞争_比劫": "边界与竞争",
    "独立反叛_伤官": "自主需求",
    "果断度_七杀": "推进与决断",
    "分析度_印星": "信息分析",
    "直觉度_食伤": "直觉与表达",
    "伤官倾向": "质疑惯例",
    "食神倾向": "从容评估",
    "精神世界_偏印": "内在思考",
    "自洽度_食神": "自我调节",
    "自我意识_比劫": "自主意识",
    "散财_比劫": "资源分享",
    "创造力变现_食伤": "创意转化",
    "储蓄保守_印星": "储备倾向",
    "体制_管理": "组织管理",
    "商业_经营": "商业经营",
    "技术_创意": "技术创意",
    "学术_专业": "学术专业",
    "创业_独立": "自主开拓",
}


def weighted_score_level(value: float, component_count: int = 1) -> str:
    """Classify a score with thresholds scaled to its aggregation width."""
    scale = max(1, component_count)
    if value >= WEIGHTED_SCORE_THRESHOLDS["high"] * scale:
        return "较强"
    if value >= WEIGHTED_SCORE_THRESHOLDS["medium"] * scale:
        return "中等"
    return "较弱"


def normalize_strength_label(value: Any) -> str:
    """Keep the structural strength value and discard appended behavior claims."""
    return str(value or "").split("。", 1)[0].strip()[:40]


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value), 1)


def build_trait_signal_evidence(trait_signals: dict | None) -> dict[str, dict]:
    """Attach field semantics so unrelated numeric values are never banded together."""
    source = trait_signals or {}
    result: dict[str, dict] = {}

    for dimension in _DIMENSION_ORDER:
        raw = source.get(dimension, {})
        if not isinstance(raw, dict) or not raw:
            continue

        item: dict[str, Any] = {"signals": []}
        for field_name in _WEIGHTED_SIGNAL_FIELDS.get(dimension, ()):
            value = _number(raw.get(field_name))
            if value is None:
                continue
            component_count = _SIGNAL_COMPONENT_COUNTS.get(field_name, 1)
            item["signals"].append({
                "label": field_name,
                "display_label": _FIELD_DISPLAY_LABELS.get(field_name, field_name),
                "kind": "weighted_score",
                "value": value,
                "level": weighted_score_level(value, component_count),
                "component_count": component_count,
            })

        if dimension in ("社交", "决策") and raw.get("综合倾向"):
            item["summary"] = str(raw["综合倾向"])
        elif dimension == "事业":
            career_signals = []
            for field_name in _CAREER_FIELDS:
                value = _number(raw.get(field_name))
                if value is None:
                    continue
                career_signals.append({
                    "label": field_name,
                    "display_label": _FIELD_DISPLAY_LABELS.get(field_name, field_name),
                    "kind": "relative_score",
                    "value": value,
                })
            career_signals.sort(key=lambda signal: signal["value"], reverse=True)
            item["signals"].extend(career_signals)
            primary = raw.get("主导方向")
            secondary = raw.get("次要方向")
            if primary:
                item["summary"] = str(primary)
            if secondary:
                item["secondary"] = str(secondary)
            gap = _number(raw.get("方向差距"))
            if gap is not None:
                item["comparison"] = "差异明显" if gap > 2.0 else "方向接近"

        # These are visible for traceability but are not promoted to scored personality facts.
        if dimension == "感情" and raw.get("夫妻宫状态") not in (None, "", "平稳"):
            item["pending_review"] = [{
                "label": "夫妻宫状态",
                "value": str(raw["夫妻宫状态"]),
                "kind": "traditional_rule_candidate",
            }]

        if item["signals"] or any(key in item for key in ("summary", "secondary", "comparison", "pending_review")):
            result[dimension] = item

    return result


def build_fusion_signals_from_evidence(evidence: dict | None) -> dict[str, dict]:
    """Remove raw values and pending rules from a public evidence view."""
    result: dict[str, dict] = {}

    for dimension, item in (evidence or {}).items():
        clean: dict[str, Any] = {}
        if item.get("summary"):
            clean["综合倾向"] = item["summary"]
        if item.get("secondary"):
            clean["次要方向"] = item["secondary"]
        if item.get("comparison"):
            clean["方向关系"] = item["comparison"]

        weighted = {
            signal.get("display_label", signal["label"]): signal["level"]
            for signal in item.get("signals", [])
            if signal.get("kind") == "weighted_score"
        }
        if weighted:
            clean["强度信号"] = weighted

        relative = [
            signal.get("display_label", signal["label"])
            for signal in item.get("signals", [])
            if signal.get("kind") == "relative_score"
        ]
        if relative:
            clean["候选方向排序"] = relative

        if clean:
            result[dimension] = clean

    return result


def build_fusion_trait_signals(trait_signals: dict | None) -> dict[str, dict]:
    """Return qualitative, field-aware signals for the LLM prompt."""
    return build_fusion_signals_from_evidence(build_trait_signal_evidence(trait_signals))


def build_personality_evidence_view(personality: dict | None, pattern: str = "") -> dict:
    """Build the stable, user-facing evidence contract used by the raw-data panel."""
    personality = personality or {}
    weighted = personality.get("weighted_shishen", {}) or {}
    scores = weighted.get("scores", {}) or {}
    breakdown = weighted.get("breakdown", {}) or {}
    raw_scale = weighted.get("scale_metadata") or weighted.get("scoring") or {}
    score_scale = {
        "kind": raw_scale.get("kind", raw_scale.get("aggregation", "unbounded_additive")),
        "comparison_scope": raw_scale.get("comparison_scope", "absolute_engine_heuristic"),
        "ranking_scope": raw_scale.get("ranking_scope", "within_chart_only"),
        "banding_scope": raw_scale.get("banding_scope", "fixed_engine_thresholds"),
        "source_status": raw_scale.get("source_status", raw_scale.get("provenance", "engineering_heuristic")),
        "thresholds": dict(WEIGHTED_SCORE_THRESHOLDS),
    }
    if raw_scale.get("relationship_policy"):
        score_scale["relationship_policy"] = raw_scale["relationship_policy"]
    if raw_scale.get("parameter_snapshot"):
        score_scale["parameter_snapshot"] = raw_scale["parameter_snapshot"]

    ranking = []
    for name, raw_score in sorted(scores.items(), key=lambda pair: pair[1], reverse=True):
        score = round(float(raw_score), 1)
        components = {
            key: round(float(value), 1)
            for key, value in (breakdown.get(name, {}) or {}).items()
            if key != "total" and isinstance(value, (int, float)) and value
        }
        ranking.append({
            "name": name,
            "score": score,
            "level": weighted_score_level(score),
            "breakdown": components,
        })

    pattern_validation = personality.get("pattern_validation", {}) or {}
    return {
        "version": "2026-07-18-v3",
        "score_scale": score_scale,
        "dimension_scale": {
            "aggregation": "sum_of_ten_god_components",
            "threshold_policy": "base_thresholds_scaled_by_component_count",
            "base_thresholds": dict(WEIGHTED_SCORE_THRESHOLDS),
        },
        "status": {
            "strength": normalize_strength_label(personality.get("strength_label", "")),
            "pattern": pattern,
            "pattern_status": pattern_validation.get("status", ""),
        },
        "weighted_scores": ranking,
        "dimensions": build_trait_signal_evidence(personality.get("trait_signals", {})),
        "fusion_boundaries": [
            "病药说明仅作规则候选，不作为心理诊断或行动指令",
            "地支心理映射、特殊组合与家境规则待完成来源复核后再进入融合结论",
            "固定档位是未经验证的工程阈值；排序和条形仅用于本盘内比较",
            "分值不是概率、准确率、人群常模或临床测量结果",
        ],
    }
