"""Calibration shared utilities — 多层容差匹配逻辑，供 pytest 参数化测试使用。

容差五级:
  L1: 精确匹配（年份+类别+≥2★）
  L2: 跨类别容差（同年, 姐妹类别 e.g. 婚嫁↔桃花）
  L3: ±1年容差（精确类别, 相邻年份）
  L4: ±1年+跨类别容差
  L5: 同类别弱信号（★1）
"""
import os
import sys

# 确保 bazi_engine 可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SISTER_CATEGORIES = {"婚嫁": "桃花", "桃花": "婚嫁"}
YEAR_TOLERANCE = 1


def find_signal(annual_scans, year, expected_cat, min_strength=2):
    """在指定年份查找 ≥min_strength★ 的信号。返回 (signal_dict, status)。"""
    for s in annual_scans:
        if s["year"] == year:
            for e in s["events"]:
                if e["strength"] >= min_strength and e["category"] == expected_cat:
                    return e, "HIT"
    return None, "MISS"


def check_case(annual_scans, year, expected_cat):
    """五级容差匹配。返回 (status, label, detail)。

    Returns:
        status:  "HIT" | "TOL" | "MISS"
        label:   人类可读标签
        detail:  信号详情字符串
    """

    # ── L1: 精确匹配 ──
    e, _ = find_signal(annual_scans, year, expected_cat, min_strength=2)
    if e:
        return "HIT", f"{year} {expected_cat}", f"{e['direction']} ★{e['strength']}"

    # ── L2: 跨类别容差 ──
    sister = SISTER_CATEGORIES.get(expected_cat)
    if sister:
        e, _ = find_signal(annual_scans, year, sister, min_strength=2)
        if e:
            return "TOL", (
                f"{year} {expected_cat}←{sister}",
                f"{e['direction']} ★{e['strength']} [跨界容差]"
            )

    # ── L3: ±1年容差 ──
    for adj in [year - YEAR_TOLERANCE, year + YEAR_TOLERANCE]:
        e, _ = find_signal(annual_scans, adj, expected_cat, min_strength=2)
        if e:
            return "TOL", (
                f"{year} {expected_cat}←{adj}年",
                f"{e['direction']} ★{e['strength']} [±1年容差]"
            )

    # ── L4: ±1年+跨类别容差 ──
    if sister:
        for adj in [year - YEAR_TOLERANCE, year + YEAR_TOLERANCE]:
            e, _ = find_signal(annual_scans, adj, sister, min_strength=2)
            if e:
                return "TOL", (
                    f"{year} {expected_cat}←{adj}年{sister}",
                    f"{e['direction']} ★{e['strength']} [±1年+跨界]"
                )

    # ── L5: 弱信号 ──
    e, _ = find_signal(annual_scans, year, expected_cat, min_strength=1)
    if e:
        triggers = e.get("triggers", [])[:2]
        return "MISS", f"{year} {expected_cat}", f"弱信号 ★1: {triggers}"

    return "MISS", f"{year} {expected_cat}", "完全未检测到"


def run_calibration(cases, liunian_margin=2):
    """运行校准案例集，返回结果列表和统计。

    Args:
        cases: list of {name, gender, year, month, day, hour, events: {year: category}, ...}
        liunian_margin: 流年范围前后扩展年数

    Returns:
        (results_list, stats_dict)
    """
    from bazi_engine.chart import build_chart

    results = []
    for case in cases:
        try:
            chart = build_chart(
                name=case["name"], gender=case["gender"],
                year=case["year"], month=case["month"],
                day=case["day"], hour=case["hour"],
                liunian_range=(min(case["events"]) - liunian_margin,
                               max(case["events"]) + liunian_margin),
            )
            annual_scans = chart.to_dict().get("annual_scans", [])

            matches = []
            tolerances = []
            misses = []
            for year, expected_cat in case["events"].items():
                status, label, detail = check_case(annual_scans, year, expected_cat)
                if status == "HIT":
                    matches.append(f"{label}: {detail}")
                elif status == "TOL":
                    tolerances.append(f"{label}: {detail}")
                else:
                    misses.append(f"{label}: {detail}")

            results.append({
                "name": case["name"],
                "matches": matches,
                "tolerances": tolerances,
                "misses": misses,
                "hits": len(matches),
                "tols": len(tolerances),
                "total": len(case["events"]),
            })
        except Exception as e:
            results.append({
                "name": case["name"],
                "error": str(e),
                "matches": [], "tolerances": [], "misses": [],
                "hits": 0, "tols": 0, "total": 0,
            })

    total_strict = sum(r["hits"] for r in results)
    total_tolerance = sum(r["tols"] for r in results)
    total_expected = sum(r["total"] for r in results)
    return results, {
        "strict": total_strict,
        "tolerance": total_tolerance,
        "expected": total_expected,
    }
