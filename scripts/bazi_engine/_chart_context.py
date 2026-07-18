"""共享命盘上下文提取 — 为所有 LLM 模块提供统一的 chart_data → dict 转换。

用法:
    from ._chart_context import extract_base_context
    ctx = extract_base_context(chart_data)
    # ctx 包含: natal_summary, four_pillars, yongshen, pattern, tiaohou, spirits, personality, family
"""
import re
from datetime import date, datetime
from typing import Any

_AGE_RE = re.compile(r"(\d+)\D+(\d+)")


def _format_age_range(age: Any) -> str:
    age_text = str(age or "").strip()
    if not age_text:
        return ""
    return age_text if age_text.endswith("岁") else f"{age_text}岁"


def _parse_birth_date(chart_data: dict) -> date | None:
    birth = str(chart_data.get("birth") or "").strip()
    if birth:
        date_part = birth[:10]
        try:
            return date.fromisoformat(date_part)
        except ValueError:
            pass

        for fmt in ("%Y/%m/%d", "%Y年%m月%d日"):
            try:
                return datetime.strptime(date_part, fmt).date()
            except ValueError:
                pass

    year = chart_data.get("year")
    month = chart_data.get("month")
    day = chart_data.get("day")
    if year and month and day:
        try:
            return date(int(year), int(month), int(day))
        except (TypeError, ValueError):
            pass
    return None


def _age_on(birth_date: date, today: date) -> int:
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def _parse_age_range(age: Any) -> tuple[int, int] | None:
    match = _AGE_RE.search(str(age or ""))
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2))
    return (start, end) if start <= end else (end, start)


def _find_dayun_for_age(periods: list[dict], current_age: int | None) -> dict | None:
    if current_age is None:
        return None
    for period in periods:
        parsed = _parse_age_range(period.get("age"))
        if parsed and parsed[0] <= current_age <= parsed[1]:
            return period
    return None


def _find_dayun_for_value(periods: list[dict], dayun_value: str) -> dict | None:
    value = dayun_value.strip()
    if not value:
        return None
    for period in periods:
        if f"{period.get('stem', '')}{period.get('branch', '')}" == value:
            return period
    return None


def _event_strength_marks(strength: Any) -> str:
    try:
        stars = max(0, min(3, int(strength)))
    except (TypeError, ValueError):
        return ""
    return "★" * stars


def _summarize_annual_scans(chart_data: dict) -> list[str]:
    summaries: list[str] = []
    for scan in chart_data.get("annual_scans", [])[:8]:
        year = scan.get("year")
        liunian = scan.get("liunian")
        dayun = scan.get("dayun")
        if not year or not liunian or not dayun:
            continue

        age = scan.get("age")
        age_text = f" {age}岁" if age is not None else ""
        line = f"{year}年{age_text} {liunian}流年，{dayun}大运"

        event_parts = []
        for event in scan.get("events", [])[:4]:
            category = event.get("category")
            marks = _event_strength_marks(event.get("strength"))
            if category and marks:
                event_parts.append(f"{category}{marks}")
        if event_parts:
            line += f"，重点：{'、'.join(event_parts)}"

        summaries.append(line)
    return summaries


def _find_current_scan(chart_data: dict, current_year: int) -> dict | None:
    for scan in chart_data.get("annual_scans", []):
        if scan.get("year") == current_year:
            return scan
    return None


def _summarize_key_events(scan: dict) -> list[dict]:
    events = []
    for event in scan.get("events", [])[:4]:
        category = event.get("category")
        if not category:
            continue
        events.append({
            "category": category,
            "direction": event.get("direction", ""),
            "strength": event.get("strength", 0),
            "marks": _event_strength_marks(event.get("strength")),
            "prediction": event.get("prediction", ""),
        })
    return events


def _scan_context(scan: dict) -> dict:
    return {
        "year": scan.get("year"),
        "age": scan.get("age"),
        "ganzhi": scan.get("liunian", ""),
        "dayun": scan.get("dayun", ""),
        "key_events": _summarize_key_events(scan),
    }


def _dayun_context(period: dict | None) -> dict | None:
    if not period:
        return None
    stem = period.get("stem", "")
    branch = period.get("branch", "")
    return {
        "order": period.get("order", 0),
        "stem": stem,
        "branch": branch,
        "ganzhi": f"{stem}{branch}",
        "age_range": _format_age_range(period.get("age")),
    }


def build_current_context(chart_data: dict) -> dict[str, Any]:
    """Build the single user-facing source for current age, dayun, and liunian facts."""
    dayun = chart_data.get("dayun", {})
    periods = [
        {"order": dp.get("order", 0), "age": _format_age_range(dp.get("age")),
         "stem": dp.get("stem", ""), "branch": dp.get("branch", "")}
        for dp in dayun.get("periods", [])[:8]
    ]

    today = date.today()
    birth_date = _parse_birth_date(chart_data)
    current_scan = _find_current_scan(chart_data, today.year)
    solar_age = _age_on(birth_date, today) if birth_date else None
    liunian_age = current_scan.get("age") if current_scan and current_scan.get("age") is not None else None
    if liunian_age is None:
        liunian_age = solar_age if solar_age is not None else chart_data.get("age")

    current_dayun = None
    if current_scan:
        current_dayun = _find_dayun_for_value(periods, str(current_scan.get("dayun", "")))
    if current_dayun is None:
        current_dayun = _find_dayun_for_age(periods, liunian_age)

    context: dict[str, Any] = {
        "current_date": today.isoformat(),
        "solar_age": solar_age,
        "liunian_age": liunian_age,
        "current_dayun": _dayun_context(current_dayun),
        "current_liunian": _scan_context(current_scan) if current_scan else None,
        "life_stage": chart_data.get("life_stage", ""),
        "annual_scan_summaries": _summarize_annual_scans(chart_data),
    }
    return context


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
    pillars = chart_data.get("four_pillars") or chart_data.get("pillars", {})
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
        {"order": dp.get("order", 0), "age": _format_age_range(dp.get("age")),
         "stem": dp.get("stem", ""), "branch": dp.get("branch", "")}
        for dp in dayun.get("periods", [])[:8]
    ]

    # The LLM receives the calculation basis, never a guessed geographic
    # precision.  It can therefore explain a changed day/hour pillar without
    # treating an unknown birthplace as a true-solar result.
    time_input = (chart_data.get("report_meta") or {}).get("input") or {}
    ctx["time_basis"] = {
        "effective_time_mode": time_input.get("effective_time_mode", "civil_input"),
        "pillar_time": time_input.get("pillar_time", chart_data.get("birth", "")),
        "city": (time_input.get("city") or {}).get("label", "未知"),
        "time_accuracy": time_input.get("time_accuracy", time_input.get("time_precision", "unknown")),
        "solar_correction_minutes": time_input.get("solar_correction_minutes", 0),
        "day_pillar_uses_next_date": time_input.get("day_pillar_uses_next_date", False),
    }

    current_context = chart_data.get("current_context") or build_current_context(chart_data)
    ctx["current_date"] = current_context.get("current_date")
    ctx["current_solar_age"] = current_context.get("solar_age")
    ctx["current_liunian_age"] = current_context.get("liunian_age")
    ctx["annual_scan_summaries"] = current_context.get("annual_scan_summaries", [])
    current_dayun = current_context.get("current_dayun")
    if current_dayun:
        ctx["current_dayun"] = {
            "order": current_dayun.get("order", 0),
            "age": current_dayun.get("age_range", ""),
            "stem": current_dayun.get("stem", ""),
            "branch": current_dayun.get("branch", ""),
        }

    # ── 神煞 ──
    spirits = chart_data.get("spirits", [])
    ctx["spirit_names"] = [s.get("name", "") for s in spirits[:10] if s.get("name")]

    # ── 性格 ──
    personality = chart_data.get("personality") or {}
    ctx["personality_profile"] = personality.get("profile", "")
    ctx["personality_traits"] = personality.get("traits", {})

    # ── 家境 ──
    family = chart_data.get("family") or {}
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
