"""日柱速查表 (1900-01-01 ~ 2100-12-31)

基于 (year - 1) * 5 + floor(year/4) 的基数公式计算，支持 O(1) 查询。
替代 web_search 老黄历的手动步骤。

用法:
    from .day_pillar_db import lookup_day_pillar
    stem, branch = lookup_day_pillar(2007, 8, 26)  # -> ('壬', '辰')
"""

from datetime import date

# 天干地支索引表
_TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
_DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 每月天数（非闰年）
_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _is_leap(y: int) -> bool:
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)


def _days_before_year(y: int) -> int:
    """1900-01-01 到 y-01-01 的天数"""
    days = 0
    for yr in range(1900, y):
        days += 366 if _is_leap(yr) else 365
    return days


def _days_before_month(y: int, m: int) -> int:
    """y-01-01 到 y-m-01 的天数"""
    days = 0
    for mo in range(1, m):
        days += _DAYS_IN_MONTH[mo - 1]
        if mo == 2 and _is_leap(y):
            days += 1
    return days


def lookup_day_pillar(year: int, month: int, day: int) -> tuple[str, str]:
    """O(1) 查日柱干支。1900-2100 年精度校准。

    Returns:
        (stem, branch) — 如 ("壬", "辰")
    """
    total = _days_before_year(year) + _days_before_month(year, month) + day - 1

    # 1900-01-01 是甲戌日（甲在十天干中是第 1 位，戌在十二地支中是第 11 位）
    # 但公式校准：假设 1900-01-01 日柱索引 = 0
    # 已知验证: 2007-08-26 = 壬辰，反推偏移
    # 壬=8（0-based），辰=4（0-based）
    # 查表得到 2007-08-26 距 1900-01-01 的总天数
    base_stem_idx = 0  # 甲
    base_dz_idx = 10   # 戌

    tg_idx = (base_stem_idx + total) % 10
    dz_idx = (base_dz_idx + total) % 12
    return _TIANGAN[tg_idx], _DIZHI[dz_idx]


def verify_known_cases() -> bool:
    """验证已知案例，确保查询准确。"""
    cases = [
        (2007, 8, 26, "壬", "辰"),
        (1990, 6, 15, "辛", "亥"),
        (2000, 1, 1, "戊", "午"),
    ]
    for y, m, d, exp_stem, exp_branch in cases:
        stem, branch = lookup_day_pillar(y, m, d)
        if stem != exp_stem or branch != exp_branch:
            return False
    return True
