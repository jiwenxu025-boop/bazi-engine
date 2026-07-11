"""婚姻/桃花验证集 — 基于公开命例
每个案例包含: 出生日期、事件年、期望信号类别和方向
"""
import json, sys, os

# 添加 bazi_engine 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MARRIAGE_CASES = [
    # ── 案例源自: 段建业盲派命理 + 元亨利贞论坛 + 公开名人命例 ──
    {
        "name": "案例M1-早婚女",
        "gender": "女", "year": 1977, "month": 5, "day": 11, "hour": 10,
        "events": {2008: "婚嫁", 2009: "桃花"},
        "notes": "2008结婚,2009离婚,2010复婚。元亨利贞论坛"
    },
    {
        "name": "案例M2-晚婚男",
        "gender": "男", "year": 1983, "month": 1, "day": 6, "hour": 4,
        "events": {2009: "婚嫁"},
        "notes": "2009己丑年结婚。元亨利贞论坛"
    },
    {
        "name": "案例M3-婚变男",
        "gender": "男", "year": 1970, "month": 8, "day": 24, "hour": 18,
        "events": {1993: "婚嫁", 2007: "桃花"},
        "notes": "1993癸酉结婚,2007丁亥离婚。元亨利贞论坛"
    },
    {
        "name": "案例M4-张子健",
        "gender": "男", "year": 1968, "month": 10, "day": 28, "hour": 2,
        "events": {2005: "桃花"},
        "notes": "2005乙酉结束第一次婚姻。公开名人"
    },
    {
        "name": "案例M5-离婚女",
        "gender": "女", "year": 1978, "month": 2, "day": 14, "hour": 13,
        "events": {2015: "桃花"},
        "notes": "2015年离婚。搜狐案例"
    },
    {
        "name": "案例M6-中年婚变女",
        "gender": "女", "year": 1977, "month": 11, "day": 4, "hour": 12,
        "events": {2007: "婚嫁", 2009: "桃花"},
        "notes": "2007结婚,2009离婚。元亨利贞论坛"
    },
    {
        "name": "案例M7-婚恋危机男",
        "gender": "男", "year": 1986, "month": 6, "day": 25, "hour": 12,
        "events": {2011: "婚嫁"},
        "notes": "2011结婚,后长期感情不合。元亨利贞论坛"
    },
    {
        "name": "案例M8-婚变风险女",
        "gender": "女", "year": 1986, "month": 9, "day": 8, "hour": 12,
        "events": {2012: "婚嫁"},
        "notes": "2012结婚,命师断2025-2026婚变。元亨利贞论坛"
    },
    {
        "name": "案例M9-胡万林克夫案",
        "gender": "女", "year": 1966, "month": 7, "day": 15, "hour": 22,
        "events": {1988: "婚嫁", 1992: "桃花"},
        "notes": "丙午 丁酉 甲戌 乙亥。段建业案例: 第一个丈夫坐牢离婚, 第二任胡万林也坐牢"
    },
    {
        "name": "案例M10-三婚女",
        "gender": "女", "year": 1955, "month": 2, "day": 10, "hour": 4,
        "events": {1978: "婚嫁", 1999: "桃花"},
        "notes": "乙未 己丑 己丑 丙寅。段建业案例: 三婚命, 第一任己卯年病故"
    },
    # ── 第二轮补充: 360doc + 搜索精确日期案例 ──
    {
        "name": "案例M11-丙戌婚男",
        "gender": "男", "year": 1982, "month": 3, "day": 23, "hour": 12,
        "events": {2006: "婚嫁"},
        "notes": "2006丙戌结婚。360doc元亨利贞案例集 例7"
    },
    {
        "name": "案例M12-婚变离婚男",
        "gender": "男", "year": 1978, "month": 11, "day": 27, "hour": 21,
        "events": {2004: "婚嫁"},
        "notes": "2004农历正月领证,十月结婚。360doc夫妻配对案例"
    },
    {
        "name": "案例M13-张子健离婚",
        "gender": "男", "year": 1968, "month": 10, "day": 28, "hour": 2,
        "events": {2005: "桃花"},
        "notes": "张子健 戊申 壬戌 辛未 己丑。2005乙酉结束第一次婚姻。百度百家号"
    },
    {
        "name": "案例M14-王宝强离婚",
        "gender": "男", "year": 1982, "month": 5, "day": 22, "hour": 22,
        "events": {2016: "桃花"},
        "notes": "王宝强 壬戌 乙巳 乙巳 丁亥。2016丙申离婚。农历四月二十九=公历1982-05-22（非05-29）"
    },
    {
        "name": "案例M15-李玟婚",
        "gender": "女", "year": 1975, "month": 1, "day": 17, "hour": 12,
        "events": {2011: "婚嫁"},
        "notes": "李玟 乙卯 戊寅 甲辰 癸酉。2011辛卯结婚。百度百家号"
    },
    {
        "name": "案例M16-伤官克夫女",
        "gender": "女", "year": 1966, "month": 8, "day": 25, "hour": 19,
        "events": {1988: "婚嫁", 1992: "桃花"},
        "notes": "丙午 丁酉 甲戌 乙亥。段建业: 第一任坐牢离婚,第二任胡万林也坐牢。酉戌穿夫宫克夫"
    },
]

if __name__ == "__main__":
    from bazi_engine.chart import build_chart

    # ── 容差配置 ──
    SISTER_CATEGORIES = {"婚嫁": "桃花", "桃花": "婚嫁"}
    YEAR_TOLERANCE = 1  # ±1年

    def _find_in_year(annual_scans, year, expected_cat):
        """在指定年份查找 ≥2★ 的信号"""
        for s in annual_scans:
            if s["year"] == year:
                for e in s["events"]:
                    if e["strength"] >= 2 and e["category"] == expected_cat:
                        return e
        return None

    def _find_weak_in_year(annual_scans, year, expected_cat):
        """在指定年份查找 ★1 的信号"""
        for s in annual_scans:
            if s["year"] == year:
                for e in s["events"]:
                    if e["category"] == expected_cat and e["strength"] == 1:
                        return e
        return None

    results = []
    for case in MARRIAGE_CASES:
        try:
            chart = build_chart(
                name=case["name"], gender=case["gender"],
                year=case["year"], month=case["month"],
                day=case["day"], hour=case["hour"],
                liunian_range=(min(case["events"])-2, max(case["events"])+2),
            )
            data = chart.to_dict()
            annual_scans = data.get("annual_scans", [])

            matches = []
            tolerances = []
            misses = []
            for year, expected_cat in case["events"].items():
                # Level 1: 精确匹配 (年份 + 类别)
                e = _find_in_year(annual_scans, year, expected_cat)
                if e:
                    matches.append(f"{year} {expected_cat}: {e['direction']} ★{e['strength']}")
                    continue

                # Level 2: 跨类别容差 (同年, 姐妹类别≥2★)
                sister_cat = SISTER_CATEGORIES.get(expected_cat)
                if sister_cat:
                    e = _find_in_year(annual_scans, year, sister_cat)
                    if e:
                        tolerances.append(f"{year} {expected_cat}←{sister_cat}: {e['direction']} ★{e['strength']} [跨界容差]")
                        continue

                # Level 3: ±1年容差 (精确类别, 相邻年份≥2★)
                for adj_year in [year - YEAR_TOLERANCE, year + YEAR_TOLERANCE]:
                    e = _find_in_year(annual_scans, adj_year, expected_cat)
                    if e:
                        tolerances.append(f"{year} {expected_cat}←{adj_year}年: {e['direction']} ★{e['strength']} [±1年容差]")
                        break
                else:
                    # Level 4: ±1年+跨类别容差
                    if sister_cat:
                        for adj_year in [year - YEAR_TOLERANCE, year + YEAR_TOLERANCE]:
                            e = _find_in_year(annual_scans, adj_year, sister_cat)
                            if e:
                                tolerances.append(f"{year} {expected_cat}←{adj_year}年{sister_cat}: {e['direction']} ★{e['strength']} [±1年+跨界]")
                                break
                        else:
                            # Level 5: 同类别弱信号 (★1)
                            e = _find_weak_in_year(annual_scans, year, expected_cat)
                            if e:
                                misses.append(f"{year} {expected_cat}: 仅有弱信号 ★1 '{e['triggers'][:50] if e['triggers'] else '()'}' ")
                            else:
                                misses.append(f"{year} {expected_cat}: 完全未检测到")
                    else:
                        e = _find_weak_in_year(annual_scans, year, expected_cat)
                        if e:
                            misses.append(f"{year} {expected_cat}: 仅有弱信号 ★1 '{e['triggers'][:50] if e['triggers'] else '()'}' ")
                        else:
                            misses.append(f"{year} {expected_cat}: 完全未检测到")

            results.append({
                "name": case["name"],
                "matches": matches,
                "tolerances": tolerances,
                "misses": misses,
                "score": f"{len(matches)}+{len(tolerances)}/{len(case['events'])}"
            })
        except Exception as e:
            results.append({"name": case["name"], "error": str(e), "matches": [], "tolerances": [], "misses": [], "score": "0/0"})

    print("=" * 60)
    print("婚姻/桃花 验证结果")
    print("=" * 60)
    total_strict = 0
    total_tolerance = 0
    total_expected = 0
    for r in results:
        hits = len(r["matches"])
        tol = len(r.get("tolerances", []))
        mis = len(r["misses"])
        exp = hits + tol + mis
        total_strict += hits
        total_tolerance += tol
        total_expected += exp

        if hits == exp:
            status = "OK"
        elif hits + tol == exp:
            status = f"~ {hits}+{tol}/{exp} (容差)"
        else:
            status = f"X {hits}+{tol}/{exp}"
        print(f"\n{status} {r['name']}")
        for m in r["matches"]:
            print(f"  [HIT] {m}")
        for t in r.get("tolerances", []):
            print(f"  [TOL] {t}")
        for m in r["misses"]:
            print(f"  [MISS] {m}")

    print(f"\n{'=' * 60}")
    if total_expected > 0:
        print(f"严格命中: {total_strict}/{total_expected} ({total_strict/total_expected*100:.0f}%)")
        print(f"容差命中: {total_strict+total_tolerance}/{total_expected} ({(total_strict+total_tolerance)/total_expected*100:.0f}%)")
    else:
        print("无预期事件，跳过命中率计算")
