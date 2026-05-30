"""择日功能 — 在指定日期范围内筛选吉日

调用方式:
    from .date_picker import pick_good_dates
    good, avoid = pick_good_dates(chart, start_date, end_date)
"""
from datetime import date, timedelta
from .enums import Tiangan, Dizhi
from ._constants import DIZHI_LIUHE, DIZHI_LIUCHONG, DIZHI_XIANGHAI


# 黄历通用吉日（略有简化）
GENERIC_GOOD = {
    Dizhi.子: [Dizhi.丑, Dizhi.辰, Dizhi.申],
    Dizhi.丑: [Dizhi.子, Dizhi.巳, Dizhi.酉],
    Dizhi.寅: [Dizhi.午, Dizhi.戌, Dizhi.亥],
    Dizhi.卯: [Dizhi.未, Dizhi.亥, Dizhi.戌],
    Dizhi.辰: [Dizhi.子, Dizhi.申, Dizhi.酉],
    Dizhi.巳: [Dizhi.丑, Dizhi.酉, Dizhi.申],
    Dizhi.午: [Dizhi.寅, Dizhi.戌, Dizhi.未],
    Dizhi.未: [Dizhi.卯, Dizhi.亥, Dizhi.午],
    Dizhi.申: [Dizhi.辰, Dizhi.子, Dizhi.巳],
    Dizhi.酉: [Dizhi.丑, Dizhi.巳, Dizhi.辰],
    Dizhi.戌: [Dizhi.寅, Dizhi.午, Dizhi.卯],
    Dizhi.亥: [Dizhi.卯, Dizhi.未, Dizhi.寅],
}


def _liunian_dizhi(year: int) -> Dizhi:
    """快速流年地支"""
    from .enums import dizhi_by_index
    return dizhi_by_index((year - 4) % 12)


def pick_good_dates(chart, start_date: date, end_date: date) -> tuple[list[date], list[date]]:
    """选吉日：优先合日柱的日期，避开冲日柱/年柱的日期。

    Returns:
        (good_dates, avoid_dates)
    """
    good = []
    avoid = []

    for n in range((end_date - start_date).days + 1):
        d = start_date + timedelta(days=n)
        dz = _liunian_dizhi(d.year)

        # 年柱地支
        year_dz = chart.year.branch

        # 日柱地支（简化：用出生日地支近似当日地支）
        day_dz = chart.day.branch

        # 检查冲突
        conflicts = []
        reasons = []

        # 合日柱 = 吉
        he_pair = None
        for (a, b) in DIZHI_LIUHE:
            if dz == a and day_dz == b:
                he_pair = f"{a.value}{b.value}"
                break
            if day_dz == a and dz == b:
                he_pair = f"{dz.value}{day_dz.value}"
                break

        # 冲日柱 = 凶
        if (dz, day_dz) in DIZHI_LIUCHONG:
            conflicts.append("冲日柱")
            reasons.append("日柱被冲——自身状态不稳，不宜决策")

        # 冲年柱 = 凶
        if (dz, year_dz) in DIZHI_LIUCHONG:
            conflicts.append("冲年柱")
            reasons.append("年柱被冲——根基动摇，不宜重大事项")

        # 害日柱 = 小凶
        if (dz, day_dz) in DIZHI_XIANGHAI:
            conflicts.append("害日柱")
            reasons.append("日柱被害——易有人际摩擦")

        # 通用吉日
        generic_good = dz in GENERIC_GOOD and day_dz in GENERIC_GOOD.get(dz, [])

        if conflicts:
            avoid.append(d)
        elif he_pair or generic_good:
            good.append(d)

    return good, avoid
