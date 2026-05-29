"""人际/状态/搬迁/健康 综合验证集"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CASES = {
    "人际": [
        # 来自校准库
        {"name": "案例D-人际摩擦", "gender": "男", "year": 2007, "month": 10, "day": 22, "hour": 6,
         "events": {2024: "人际"}, "notes": "2024人际摩擦(校准库验证)"},
        # 来自搜索: 被骗100万坤造
        {"name": "被骗女-朋友背叛", "gender": "女", "year": 1980, "month": 7, "day": 15, "hour": 14,
         "events": {2018: "人际"}, "notes": "庚申 癸未 辛卯 乙未。2018被邻居骗100万"},
        # 比劫犯小人案例
        {"name": "案例C-人际困扰", "gender": "女", "year": 2007, "month": 11, "day": 9, "hour": 7,
         "events": {2023: "人际"}, "notes": "2023人际困扰(校准库: 原标记为桃花负面,实为人际)"},
        # 刑冲案例
        {"name": "S9-被辞退男", "gender": "男", "year": 1997, "month": 3, "day": 10, "hour": 14,
         "events": {2020: "人际", 2021: "人际"}, "notes": "被辞职+合作被骗"},
    ],
    "状态": [
        {"name": "案例D-备考状态", "gender": "男", "year": 2007, "month": 10, "day": 22, "hour": 6,
         "events": {2026: "状态"}, "notes": "2026备考中但朋友耽误(校准库验证)"},
        {"name": "案例A-低谷", "gender": "男", "year": 2007, "month": 8, "day": 26, "hour": 20,
         "events": {2024: "状态"}, "notes": "2024分手后情绪"},
        {"name": "S4-创业男状态", "gender": "男", "year": 1988, "month": 10, "day": 25, "hour": 4,
         "events": {2020: "状态"}, "notes": "2020贵人+大工程, 状态上升"},
    ],
    "搬迁": [
        {"name": "案例A-高考异地", "gender": "男", "year": 2007, "month": 8, "day": 26, "hour": 20,
         "events": {2025: "搬迁"}, "notes": "2025高考异地入学(校准库)"},
        {"name": "山东→新疆搬家", "gender": "男", "year": 1975, "month": 9, "day": 2, "hour": 4,
         "events": {1993: "搬迁"}, "notes": "1975/09/02寅时。1993夏全家从山东搬新疆(多亮案例)"},
        {"name": "S4-创业搬迁", "gender": "男", "year": 1988, "month": 10, "day": 25, "hour": 4,
         "events": {2019: "搬迁", 2020: "搬迁"}, "notes": "2019离职+2020遇贵人,环境大变"},
        {"name": "M6-中年婚变女迁", "gender": "女", "year": 1977, "month": 11, "day": 4, "hour": 12,
         "events": {2007: "搬迁"}, "notes": "2007结婚+搬家"},
    ],
    "健康": [
        {"name": "案例A-健康", "gender": "男", "year": 2007, "month": 8, "day": 26, "hour": 20,
         "events": {2026: "健康"}, "notes": "2026暂无健康问题(校准库中性)"},
        {"name": "S5-入狱男健康", "gender": "男", "year": 1963, "month": 4, "day": 15, "hour": 20,
         "events": {2016: "健康"}, "notes": "2016被捕入狱(重大事件)"},
        {"name": "乳腺癌手术女", "gender": "女", "year": 1952, "month": 8, "day": 2, "hour": 12,
         "events": {2001: "健康"}, "notes": "1952/08/02午时。2001辛巳乳腺癌手术(羊刃聚会)"},
        {"name": "高血压中风男", "gender": "男", "year": 1947, "month": 5, "day": 8, "hour": 10,
         "events": {2002: "健康"}, "notes": "1947润三月十八巳时≈5/8。2002壬午高血压中风(五羊刃)"},
        {"name": "肺癌手术女", "gender": "女", "year": 1950, "month": 11, "day": 4, "hour": 9,
         "events": {2006: "健康", 2007: "健康"}, "notes": "1950/11/04巳时。2006丙戌肺癌,2007丁亥手术"},
        {"name": "躁狂症转抑郁男", "gender": "男", "year": 1975, "month": 12, "day": 16, "hour": 8,
         "events": {2007: "健康"}, "notes": "1975/12/16辰时。2007躁狂症,2008抑郁症"},
    ],
}

if __name__ == "__main__":
    from bazi_engine.chart import build_chart

    for module, cases in CASES.items():
        print(f'\n=== {module} ===')
        results = []
        for case in cases:
            try:
                chart = build_chart(name=case["name"], gender=case["gender"],
                                   year=case["year"], month=case["month"],
                                   day=case["day"], hour=case["hour"],
                                   liunian_range=(min(case["events"])-1, max(case["events"])+1))
                data = chart.to_dict()
                for year, expected_cat in case["events"].items():
                    found = None
                    for s in data.get("annual_scans", []):
                        if s["year"] == year:
                            for e in s["events"]:
                                if e["category"] == expected_cat:
                                    found = e; break
                    hit = "HIT" if found and found["strength"] >= 2 else ("WEAK" if found else "MISS")
                    d = f'{found["direction"]} *{found["strength"]} [{", ".join(found["triggers"][:2])}]' if found else "-"
                    results.append((hit, d))
                    print(f'  {case["name"]:<16} {year} {hit:<5} {d[:70]}')
            except Exception as e:
                print(f'  {case["name"]:<16} ERR: {e}')
        hits = sum(1 for r in results if r[0] == "HIT")
        weak = sum(1 for r in results if r[0] == "WEAK")
        total = len(results)
        pct = (hits+weak*0.5)/total*100 if total > 0 else 0
        print(f'  --- {module}: {hits}H + {weak}W / {total} ≈ {pct:.0f}% ---')
