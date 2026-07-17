"""四柱计算: 年柱 月柱 日柱 时柱"""

from datetime import datetime, timedelta

from ._constants import (
    MONTH_TO_DIZHI_APPROX,
    WUHU_DUNYUAN,
    WUSHU_DUNYUAN,
    hour_to_dizhi,
)
from .enums import Dizhi, Tiangan, dizhi_by_index, tiangan_by_index

WARNING_DAY_PILLAR = ""  # JDN 公式精确，不再需要此警告
WARNING_YEAR_BOUNDARY = "出生日期在立春前，年柱已自动使用上一年"
WARNING_MONTH_BOUNDARY = ""  # 精确节气已消除月柱边界歧义
WARNING_NIGHT_ZI = "夜子时按次日日柱计算；月柱和年柱仍按实际出生时刻判定"


def compute_year_pillar(gregorian_year: int, gregorian_month: int, gregorian_day: int,
                        birth_hour: int = 12) -> tuple[Tiangan, Dizhi, list[str]]:
    """返回 (年干, 年支, warnings) — 根据精确立春时刻判断"""
    from datetime import datetime
    warnings: list[str] = []

    # 检查出生时间是否在立春之前
    try:
        from .solar_terms import get_jie_datetime
        lichun = get_jie_datetime(gregorian_year, 0)  # 立春 = index 0
        birth_dt = datetime(gregorian_year, gregorian_month, gregorian_day, birth_hour)
        if birth_dt < lichun:
            effective_year = gregorian_year - 1
            warnings.append(WARNING_YEAR_BOUNDARY)
        else:
            effective_year = gregorian_year
    except Exception:
        effective_year = gregorian_year
        if gregorian_month <= 2 and gregorian_day <= 5:
            warnings.append("年柱边界请确认立春时刻")

    idx = (effective_year - 4) % 60
    tg = tiangan_by_index(idx)
    dz = dizhi_by_index(idx)
    return tg, dz, warnings


def compute_month_pillar(year_stem: Tiangan, gregorian_month: int, gregorian_day: int,
                         birth_hour: int = 12,
                         gregorian_year: int | None = None) -> tuple[Tiangan, Dizhi, list[str]]:
    """返回 (月干, 月支, warnings)

    用精确节气区间确定月支，五虎遁确定月干。
    """
    warnings: list[str] = []

    month_dz = month_branch_for_datetime(
        gregorian_year, gregorian_month, gregorian_day, birth_hour,
    )

    yin_stem = WUHU_DUNYUAN[year_stem]
    # 五虎遁以寅月为起点，月支在十二支中的实际月序不能先模十。
    offset = (month_dz.index - Dizhi.寅.index) % 12
    month_tg = tiangan_by_index((yin_stem.index + offset) % 10)

    return month_tg, month_dz, warnings


def month_branch_for_datetime(gregorian_year: int | None, gregorian_month: int,
                              gregorian_day: int, birth_hour: int = 12) -> Dizhi:
    """按节气返回月支；没有年份时才回退到近似月表。"""
    if gregorian_year is None:
        return MONTH_TO_DIZHI_APPROX.get(gregorian_month, Dizhi.子)
    try:
        birth_dt = datetime(gregorian_year, gregorian_month, gregorian_day, birth_hour)
        return _month_branch_from_jieqi(birth_dt, gregorian_year)
    except Exception:
        return MONTH_TO_DIZHI_APPROX.get(gregorian_month, Dizhi.子)


def _month_branch_from_jieqi(birth_dt, gregorian_year: int) -> Dizhi:
    """根据精确节气确定出生时刻所属的月支"""
    from .solar_terms import get_jie_datetime
    # 12节顺序对应月支: 寅卯辰巳午未申酉戌亥子丑
    month_branches = [
        Dizhi.寅, Dizhi.卯, Dizhi.辰, Dizhi.巳, Dizhi.午, Dizhi.未,
        Dizhi.申, Dizhi.酉, Dizhi.戌, Dizhi.亥, Dizhi.子, Dizhi.丑,
    ]

    # 小寒属于上一年的第十二个“节”。小寒前仍是子月，小寒起才进入丑月。
    previous_xiaohan = get_jie_datetime(gregorian_year - 1, 11)
    if birth_dt < previous_xiaohan:
        return Dizhi.子

    for i in range(12):
        jie_dt = get_jie_datetime(gregorian_year, i)
        if birth_dt < jie_dt:
            # 出生在这个节之前 → 属于上一个月的月支
            prev = (i - 1) % 12
            return month_branches[prev]

    # 理论上会在次年立春前的循环分支返回；此处仅作防御性回退。
    return Dizhi.丑


def compute_day_pillar(gregorian_year: int, gregorian_month: int, gregorian_day: int) -> tuple[Tiangan, Dizhi, list[str]]:
    """返回 (日干, 日支, warnings)

    Julian Day Number 精确算法 — 对任意公历日期准确，无需 override。
    JDN offset 49 以 2000-01-01=戊午 校准。
    """
    # Julian Day Number
    a = (14 - gregorian_month) // 12
    y = gregorian_year + 4800 - a
    m = gregorian_month + 12 * a - 3
    jdn = gregorian_day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    idx = (jdn + 49) % 60  # 49 = offset for 甲戌 on 1900-01-01
    return tiangan_by_index(idx), dizhi_by_index(idx), []


def compute_hour_pillar(day_stem: Tiangan, hour: int) -> tuple[Tiangan, Dizhi, list[str], str | None]:
    """返回 (时干, 时支, warnings, 子时标记)

    用五鼠遁元: 日干 → 子时天干，再按时辰偏移
    """
    warnings: list[str] = []
    hour_dz, zi_flag = hour_to_dizhi(hour)

    # 五鼠遁: 日干 → 子时天干
    zi_stem = WUSHU_DUNYUAN[day_stem]
    # 时天干 = 子时天干 + 时辰偏移 mod 10
    offset = hour_dz.index  # 子=0, 丑=1, ...
    hour_tg = tiangan_by_index((zi_stem.index + offset) % 10)

    return hour_tg, hour_dz, warnings, zi_flag


def build_four_pillars(
    year: int, month: int, day: int, hour: int,
    day_pillar_override: tuple[str, str] | None = None,
) -> dict:
    """一站式四柱计算，返回包含所有信息的 dict。

    day_pillar_override: ("壬", "辰") 用 WebSearch 验证后的日柱覆盖公式计算值。
    """
    all_warnings: list[str] = []

    # 年柱
    y_tg, y_dz, y_w = compute_year_pillar(year, month, day, hour)
    all_warnings.extend(y_w)

    # 月柱
    m_tg, m_dz, m_w = compute_month_pillar(y_tg, month, day, hour, gregorian_year=year)
    all_warnings.extend(m_w)

    # 日柱
    civil_birth = datetime(year, month, day, hour)
    day_pillar_date = civil_birth + timedelta(days=1) if hour >= 23 else civil_birth
    if hour >= 23:
        all_warnings.append(WARNING_NIGHT_ZI)
    if day_pillar_override:
        d_tg = Tiangan(day_pillar_override[0])
        d_dz = Dizhi(day_pillar_override[1])
        d_w = []
    else:
        d_tg, d_dz, d_w = compute_day_pillar(
            day_pillar_date.year, day_pillar_date.month, day_pillar_date.day,
        )
    all_warnings.extend(d_w)

    # 时柱
    h_tg, h_dz, h_w, zi_flag = compute_hour_pillar(d_tg, hour)
    all_warnings.extend(h_w)

    return {
        "year": (y_tg, y_dz),
        "month": (m_tg, m_dz),
        "day": (d_tg, d_dz, d_tg),  # third = day_master
        "hour": (h_tg, h_dz),
        "day_master": d_tg,
        "hour_zi_flag": zi_flag,
        "warnings": all_warnings,
    }
