"""财运探索性时点覆盖集 — 不构成财富量级或方向准确率。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

WEALTH_CASES = [
    # ── 巨富案例 ──
    {
        "name": "W1-电商女强人",
        "gender": "女", "year": 1982, "month": 8, "day": 21, "hour": 8,
        "events": {2008: "财运", 2009: "财运", 2016: "财运", 2017: "财运"},
        "magnitude": "百万-千万",
        "notes": "2008-2009电商爆发数百万。壬戌 戊申 丙子 壬辰"
    },
    {
        "name": "W2-赌博暴富男",
        "gender": "男", "year": 1983, "month": 7, "day": 20, "hour": 12,
        "events": {2014: "财运", 2015: "财运", 2022: "财运"},
        "magnitude": "千万",
        "notes": "癸亥 己未 癸亥 戊午。2014-2015德州扑克赚千万, 2022又发财"
    },
    {
        "name": "W3-股市暴富男",
        "gender": "男", "year": 1983, "month": 7, "day": 11, "hour": 8,
        "events": {2015: "财运"},
        "magnitude": "千万",
        "notes": "癸亥 己未 庚子 庚辰。农历六月初二辰时≈1983-07-11。2015乙未股市赚几千万"
    },
    {
        "name": "W4-亿万到破产男",
        "gender": "男", "year": 1970, "month": 3, "day": 20, "hour": 8,
        "events": {2006: "财运", 2007: "财运"},
        "magnitude": "亿万→破产",
        "notes": "庚戌 己卯 己亥 戊辰。农历二月十三≈1970-03-20。壬午运亿万, 2006开始破财几千万"
    },
    {
        "name": "W5-过亿企业家",
        "gender": "男", "year": 1983, "month": 9, "day": 22, "hour": 4,
        "events": {2015: "财运", 2017: "财运", 2018: "财运", 2023: "财运"},
        "magnitude": "过亿→困境",
        "notes": "癸亥 辛酉 戊午 甲寅。2015盈利300万,2017销售1.2亿,2018过亿,2023困境"
    },

    # ── 普通财运 ──
    {
        "name": "W6-普通年入百万",
        "gender": "女", "year": 1988, "month": 7, "day": 20, "hour": 6,
        "events": {2019: "财运", 2020: "财运", 2021: "财运"},
        "magnitude": "百万级",
        "notes": "戊辰 己未 丁卯 癸卯。2019入百万,2020-2021入200-300万"
    },
    {
        "name": "W7-收入下滑",
        "gender": "女", "year": 1988, "month": 7, "day": 20, "hour": 6,
        "events": {2024: "财运"},
        "magnitude": "下滑",
        "notes": "(同W6) 2024收入下滑至百万"
    },

    # ── 破财案例 ──
    {
        "name": "W8-被骗百万男",
        "gender": "男", "year": 1990, "month": 7, "day": 15, "hour": 10,
        "events": {2024: "财运"},
        "magnitude": "破大财",
        "notes": "庚午 癸未 庚寅 辛巳。甲辰年(2024)被骗几百万"
    },
    {
        "name": "W9-负债80万起家",
        "gender": "男", "year": 1983, "month": 9, "day": 22, "hour": 4,
        "events": {2008: "财运"},
        "magnitude": "负债",
        "notes": "(同W5) 2008创业失败负债80万"
    },
]

# 名人大富豪对照
CELEB_WEALTH = [
    {
        "name": "C1-马云",
        "gender": "男", "year": 1964, "month": 9, "day": 10, "hour": 12,
        "events": {1999: "财运", 2014: "财运"},
        "magnitude": "亿万富豪",
        "notes": "甲辰 癸酉 壬申 (时辰估算)。1999创立阿里,2014阿里上市"
    },
    {
        "name": "C2-马化腾",
        "gender": "男", "year": 1971, "month": 10, "day": 29, "hour": 12,
        "events": {1998: "财运", 2004: "财运"},
        "magnitude": "亿万富豪",
        "notes": "辛亥 戊戌 丁亥 (时辰估算)。1998创立腾讯,2004上市"
    },
]

if __name__ == "__main__":
    from bazi_engine.chart import build_chart

    all_cases = WEALTH_CASES + CELEB_WEALTH
    results = []
    for case in all_cases:
        try:
            chart = build_chart(
                name=case["name"], gender=case["gender"],
                year=case["year"], month=case["month"],
                day=case["day"], hour=case["hour"],
                liunian_range=(min(case["events"])-2, max(case["events"])+2),
            )
            data = chart.to_dict()

            for year, expected_cat in case["events"].items():
                found = None
                for s in data.get("annual_scans", []):
                    if s["year"] == year:
                        for e in s["events"]:
                            if e["category"] == expected_cat and e["strength"] >= 2:
                                found = e
                                break
                if not found:
                    for s in data.get("annual_scans", []):
                        if s["year"] == year:
                            for e in s["events"]:
                                if e["category"] == expected_cat and e["strength"] == 1:
                                    found = e
                                    break

                hit = "COVER" if found and found.get("strength",0) >= 2 else ("WEAK" if found else "MISS")
                det_mag = found.get("magnitude", "") if found else ""
                detail = f"{found.get('direction','')} ★{found.get('strength','')} [{det_mag}] " if found else "-"
                if found:
                    detail += f"[{', '.join(found.get('triggers',[])[:2])}]"
                results.append({
                    "case": case["name"], "year": year,
                    "magnitude": case.get("magnitude", "?"),
                    "status": hit, "detail": detail,
                })
        except Exception as ex:
            results.append({"case": case["name"], "year": 0, "magnitude": "?", "status": "ERR", "detail": str(ex)})

    print("财运探索性时点覆盖（不校验方向、财富量级或具体事件，不能视为准确率）")
    print(f"{'Case':<18} {'Year':<6} {'Mag':<12} {'Status':<6} {'Detail'}")
    print("-" * 100)
    total_hit = sum(1 for r in results if r["status"] == "COVER")
    total_exp = len(results)
    for r in results:
        print(f"{r['case']:<18} {r['year']:<6} {r['magnitude']:<12} {r['status']:<6} {r['detail'][:60]}")
    print(f"\n财运时点覆盖: {total_hit}/{total_exp}")
