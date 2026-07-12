"""事业验证集 — 晋升/跳槽/创业/离职
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CAREER_CASES = [
    # ── 跳槽/晋升 ──
    {
        "name": "S1-多次跳槽男",
        "gender": "男", "year": 1985, "month": 11, "day": 20, "hour": 2,
        "events": {2014: "事业", 2017: "事业", 2022: "事业"},
        "type": "跳槽",
        "notes": "乙丑 丁亥 丙辰 己丑。2014跳外企,2017跳槽,2022跳初创60-70万"
    },
    {
        "name": "S2-券商跳槽女",
        "gender": "女", "year": 1997, "month": 7, "day": 20, "hour": 8,
        "events": {2021: "事业", 2023: "事业", 2024: "事业"},
        "type": "入职+跳槽",
        "notes": "丁丑 丁未 庚辰 庚辰。2021入职券商,2023裁撤跳槽,2024转岗交易员"
    },
    {
        "name": "S3-频繁换工作女",
        "gender": "女", "year": 1999, "month": 9, "day": 15, "hour": 20,
        "events": {2022: "事业", 2023: "事业"},
        "type": "频繁离职",
        "notes": "己卯 壬申 甲辰 甲戌。毕业后一年换三四个工作"
    },

    # ── 创业 ──
    {
        "name": "S4-建筑创业男",
        "gender": "男", "year": 1988, "month": 10, "day": 25, "hour": 4,
        "events": {2019: "事业", 2020: "事业", 2021: "财运", 2022: "财运", 2023: "财运"},
        "type": "创业暴富",
        "notes": "戊辰 壬戌 戊申 甲寅。2019创业,2020贵人+大工程,2021-2023赚2000万"
    },
    {
        "name": "S5-建材董事长",
        "gender": "男", "year": 1963, "month": 4, "day": 15, "hour": 20,
        "events": {2016: "事业"},
        "type": "大富→入狱",
        "notes": "癸卯 丙辰 甲申 甲戌。开建材工厂董事长, 壬子/辛亥运赚钱数亿, 丙申年(2016)被捕"
    },

    # ── 名人晋升对照 ──
    {
        "name": "S6-马化腾创业",
        "gender": "男", "year": 1971, "month": 10, "day": 29, "hour": 12,
        "events": {1998: "事业", 2004: "事业"},
        "type": "创业+上市",
        "notes": "辛亥 戊戌 丁亥。1998创立腾讯,2004上市"
    },
    {
        "name": "S7-雷军创业",
        "gender": "男", "year": 1969, "month": 12, "day": 16, "hour": 12,
        "events": {2010: "事业", 2018: "事业"},
        "type": "创业+上市",
        "notes": "己酉 丙子 乙丑。2010创立小米,2018小米上市"
    },

    # ── 降薪/困境 ──
    {
        "name": "S8-2024降薪男",
        "gender": "男", "year": 1985, "month": 11, "day": 20, "hour": 2,
        "events": {2024: "事业"},
        "type": "降薪",
        "notes": "(同S1) 2024公司降薪至60多万"
    },
    {
        "name": "S9-多次被辞男",
        "gender": "男", "year": 1997, "month": 3, "day": 10, "hour": 14,
        "events": {2020: "事业", 2021: "事业"},
        "type": "被辞退",
        "notes": "丁丑 癸卯 壬戌 丁未。毕业两年多换三份工作,被辞职"
    },
]

if __name__ == "__main__":
    from bazi_engine.chart import build_chart

    results = []
    for case in CAREER_CASES:
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
                            if e["category"] == expected_cat and e["strength"] >= 1:
                                found = e
                                break
                hit = "HIT" if found and found.get("strength",0) >= 2 else ("WEAK" if found else "MISS")
                detail = f"{found.get('direction','')} *{found.get('strength','')} [{', '.join(found.get('triggers',[])[:2])}]" if found else "-"
                if expected_cat != "事业":
                    hit = "N/A"  # non-career event
                results.append({
                    "case": case["name"], "year": year,
                    "type": case.get("type", "?"),
                    "status": hit, "detail": detail,
                })
        except Exception as ex:
            results.append({"case": case["name"], "year": 0, "type": "?", "status": "ERR", "detail": str(ex)})

    print(f"{'Case':<18} {'Year':<6} {'Type':<12} {'Status':<6} {'Detail'}")
    print("-" * 100)
    total_hit = sum(1 for r in results if r["status"] == "HIT")
    total_career = sum(1 for r in results if r["status"] != "N/A")
    for r in results:
        if r["status"] == "N/A":
            continue
        print(f"{r['case']:<18} {r['year']:<6} {r['type']:<12} {r['status']:<6} {r['detail'][:60]}")
    career_hit = total_hit
    print(f"\n事业事件: {career_hit}/{total_career} ({career_hit/total_career*100:.0f}%)" if total_career > 0 else "\n无数据")
