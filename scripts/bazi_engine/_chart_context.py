"""共享命盘上下文提取 — 为所有 LLM 模块提供统一的 chart_data → dict 转换。

用法:
    from ._chart_context import extract_base_context
    ctx = extract_base_context(chart_data)
    # ctx 包含: natal_summary, pillars, yongshen, pattern, tiaohou, spirits, personality, family
"""
from typing import Any


def extract_base_context(chart_data: dict) -> dict[str, Any]:
    """从 chart_data 提取标准化的基础上下文。

    各 LLM 模块在此之上添加自己的特定字段。
    """
    ctx: dict[str, Any] = {}

    # ── 日主 ──
    dm = chart_data.get("day_master", {})
    ctx["day_master"] = f"{dm.get('stem','')}({dm.get('wuxing','')}·{dm.get('yinyang','')})"
    ctx["day_master_stem"] = dm.get("stem", "")

    # ── 格局 ──
    ctx["pattern"] = chart_data.get("pattern", "")

    # ── 用神 ──
    yongshen = chart_data.get("yongshen", {})
    ctx["strength"] = yongshen.get("strength", "中和")
    ctx["score"] = yongshen.get("score", 0)
    ctx["favorable"] = yongshen.get("favorable", [])
    ctx["harmful"] = yongshen.get("harmful", [])
    ctx["favorable_wuxing"] = yongshen.get("favorable_wuxing", [])
    ctx["harmful_wuxing"] = yongshen.get("harmful_wuxing", [])
    ctx["cong_ge"] = yongshen.get("cong_ge")

    # ── 调候 ──
    tiaohou = chart_data.get("tiaohou", {})
    if tiaohou:
        ctx["tiaohou"] = {
            "climate": tiaohou.get("climate", "中和"),
            "is_fei_ju": tiaohou.get("is_fei_ju", False),
            "tiaohou_wuxing": tiaohou.get("tiaohou_wuxing", []),
            "label": tiaohou.get("label", ""),
        }

    # ── 四柱 ──
    pillars = chart_data.get("pillars", {})
    pillar_parts = []
    for key in ["year", "month", "day", "hour"]:
        p = pillars.get(key, {})
        if p:
            pillar_parts.append(f"{p.get('stem','')}{p.get('branch','')}")
    ctx["pillars_str"] = " ".join(pillar_parts)
    ctx["day_branch"] = pillars.get("day", {}).get("branch", "")

    # ── 干支关系 ──
    interactions = chart_data.get("interactions", {})
    key_rels = []
    for inter_type in ["tiangan"]:
        for it in interactions.get(inter_type, []):
            key_rels.append(f"{it.get('type','')}: {it}")
    for inter_type in ["dizhi"]:
        for it in interactions.get(inter_type, []):
            key_rels.append(f"{it.get('type','')}({'&'.join(it.get('pillars',[]))})")
    ctx["key_interactions"] = key_rels[:12]

    # ── 大运 ──
    dayun = chart_data.get("dayun", {})
    ctx["dayun_direction"] = dayun.get("direction", "")
    ctx["dayun_start_age"] = dayun.get("start_age", 0)
    ctx["dayun_periods"] = [
        {"order": dp.get("order", 0), "age": dp.get("age", ""),
         "stem": dp.get("stem", ""), "branch": dp.get("branch", "")}
        for dp in dayun.get("periods", [])[:8]
    ]

    # ── 神煞 ──
    spirits = chart_data.get("spirits", [])
    ctx["spirit_names"] = [s.get("name", "") for s in spirits[:10] if s.get("name")]

    # ── 性格 ──
    personality = chart_data.get("personality", {})
    ctx["personality_profile"] = personality.get("profile", "")
    ctx["personality_traits"] = personality.get("traits", {})

    # ── 家境 ──
    family = chart_data.get("family", {})
    if family.get("profile"):
        ctx["family"] = {
            "level": family.get("level_label", ""),
            "father": family.get("father", ""),
            "mother": family.get("mother", ""),
        }

    # ── 已知事件 ──
    known = chart_data.get("known_events", {})
    if known:
        ctx["known_events"] = known

    return ctx
