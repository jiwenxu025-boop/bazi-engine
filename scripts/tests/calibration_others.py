"""人际/状态/搬迁探索性时点覆盖集 — 不构成具体事件或方向准确率。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CASES = {
    "人际": [
        # 来自校准库
        {"name": "案例C-人际摩擦", "gender": "男", "year": 2007, "month": 10, "day": 22, "hour": 6,
         "events": {2024: "人际"}, "notes": "2024人际摩擦(校准库验证)"},
        # 来自搜索: 被骗100万坤造
        {"name": "被骗女-朋友背叛", "gender": "女", "year": 1980, "month": 7, "day": 15, "hour": 14,
         "events": {2018: "人际"}, "notes": "庚申 癸未 辛卯 乙未。2018被邻居骗100万"},
        # 比劫犯小人案例
        {"name": "案例B-人际困扰", "gender": "女", "year": 2007, "month": 11, "day": 9, "hour": 7,
         "events": {2023: "人际"}, "notes": "2023人际困扰(校准库: 原标记为桃花负面,实为人际)"},
        # 刑冲案例
        {"name": "S9-被辞退男", "gender": "男", "year": 1997, "month": 3, "day": 10, "hour": 14,
         "events": {2020: "人际", 2021: "人际"}, "notes": "被辞职+合作被骗"},
    ],
    "状态": [
        {"name": "案例C-备考状态", "gender": "男", "year": 2007, "month": 10, "day": 22, "hour": 6,
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
}

if __name__ == "__main__":
    from bazi_engine.chart import build_chart

    for module, cases in CASES.items():
        print(f'\n=== {module} ===')
        results = []
        print("  仅检查类别在该时点是否出现；不校验方向或具体事件。")
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
                                    found = e
                                    break
                    hit = "COVER" if found and found["strength"] >= 2 else ("WEAK" if found else "MISS")
                    d = f'{found["direction"]} *{found["strength"]} [{", ".join(found["triggers"][:2])}]' if found else "-"
                    results.append((hit, d))
                    print(f'  {case["name"]:<16} {year} {hit:<5} {d[:70]}')
            except Exception as e:
                print(f'  {case["name"]:<16} ERR: {e}')
        hits = sum(1 for r in results if r[0] == "COVER")
        weak = sum(1 for r in results if r[0] == "WEAK")
        total = len(results)
        print(f'  --- {module}时点覆盖: {hits}C + {weak}W / {total} ---')
