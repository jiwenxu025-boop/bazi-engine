"""数据构建器 — 将 BaziChart 转为分析所需的结构化数据"""


def build_pillars_data_for_analysis(chart) -> list[dict]:
    """从 BaziChart 提取分析所需的四柱数据"""
    from ..ten_gods import get_ten_god
    pillars = [chart.year, chart.month, chart.day, chart.hour]
    result = []
    for p in pillars:
        data = {
            "pillar_type": p.pillar_type,
            "stem": p.stem.value,
            "branch": p.branch.value,
            "ten_god": p.ten_god.value if p.ten_god else None,
            "source": "stem" if p.pillar_type != "日柱" else "day_master",
            "hidden_stems": [{"stem": hs.stem.value, "level": hs.level} for hs in p.hidden_stems],
            "hidden_ten_gods": [],
            "stem_wuxing": p.stem.wuxing.value,
            "branch_wuxing": p.branch.wuxing.value,
            "nayin": p.nayin,
        }
        # 藏干十神
        for hs in p.hidden_stems:
            tg = get_ten_god(chart.day_master, hs.stem)
            if tg:
                data["hidden_ten_gods"].append(tg.value)
        result.append(data)
    return result

