"""精确节气计算 — 基于 ephem 天文库的太阳黄经迭代求解

24 节气由太阳黄经每 15° 定义。12 个「节」对应奇数次 15° 起点（立春=315°），
用于八字月柱分界和大运起运年龄计算。

精度：±1 秒内（ephem VSOP87 行星理论）
回退：ephem 不可用时自动回退到近似查表
"""

from datetime import datetime, timedelta
from functools import lru_cache

# ═══════════════════════════════════════════════════════════════
# 常量
# ═══════════════════════════════════════════════════════════════

_TIMEZONE_OFFSET = timedelta(hours=8)  # CST = UTC+8

# 12 节的太阳黄经（度），按序：立春 惊蛰 清明 立夏 芒种 小暑 立秋 白露 寒露 立冬 大雪 小寒
_JIE_LONGITUDE: list[float] = [
    315.0, 345.0, 15.0, 45.0, 75.0, 105.0,
    135.0, 165.0, 195.0, 225.0, 255.0, 285.0,
]

# 近似日期种子（仅用于 ephem 迭代收敛的初始猜测，非最终结果）
_JIEQI_SEED: list[tuple[int, int]] = [
    (2, 4), (3, 6), (4, 5), (5, 6), (6, 6), (7, 7),
    (8, 8), (9, 8), (10, 8), (11, 8), (12, 7), (1, 6),
]

# 节名（按 _JIE_LONGITUDE 顺序）
_JIE_NAMES: list[str] = [
    "立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
    "立秋", "白露", "寒露", "立冬", "大雪", "小寒",
]

# 警告常量（保留用于回退路径）
WARNING_APPROXIMATE = "节气日期为近似值，起运年龄可能有±1天偏差，建议提供精确节气数据"

# ═══════════════════════════════════════════════════════════════
# ephem 导入检测
# ═══════════════════════════════════════════════════════════════

try:
    import ephem
    _HAS_EPHEM = True
except ImportError:
    _HAS_EPHEM = False


# ═══════════════════════════════════════════════════════════════
# ephem 精确路径
# ═══════════════════════════════════════════════════════════════

if _HAS_EPHEM:

    def _sun_ecliptic_lon(dt: datetime) -> float:
        """返回太阳在给定 UTC datetime 的黄经（度）"""
        obs = ephem.Observer()
        obs.date = dt.strftime("%Y/%m/%d %H:%M:%S")
        ecl = ephem.Ecliptic(ephem.Sun(obs))
        return float(ecl.lon) * 180.0 / ephem.pi

    def _find_jie_utc(year: int, target_lon: float, seed: tuple[int, int]) -> datetime:
        """迭代收敛到太阳黄经 == target_lon 的 UTC 时刻

        Args:
            year: 公历年
            target_lon: 目标黄经（度）
            seed: (月, 日) 近似值用于初始猜测

        Returns:
            精确 UTC datetime
        """
        m, d = seed
        real_y = year + 1 if m == 1 else year  # 小寒在 1 月，年份+1
        dt = datetime(real_y, m, d, 12, 0, 0)  # 从种子日期正午开始

        for _ in range(30):
            cur = _sun_ecliptic_lon(dt)
            # 最短有向角差
            delta = (target_lon - cur + 180.0) % 360.0 - 180.0
            if abs(delta) < 1e-5:  # ~0.3 秒精度
                break
            # 太阳平均日运动 ~0.9856°/天
            dt = dt + timedelta(days=delta / 0.9856)
        return dt

    @lru_cache(maxsize=120)
    def _compute_jie_datetime(jie_index: int, year: int) -> datetime:
        """返回第 jie_index 个节在 year 年的 CST datetime（缓存）"""
        utc_dt = _find_jie_utc(year, _JIE_LONGITUDE[jie_index], _JIEQI_SEED[jie_index])
        return utc_dt + _TIMEZONE_OFFSET

    def distance_to_next_jie(birth_dt: datetime) -> tuple[float, list[str]]:
        """出生时间到下一个节的天数（精确到秒）

        Returns:
            (天数_float, 警告列表) — ephem 路径下警告列表为空
        """
        year = birth_dt.year
        for i in range(12):
            jie_dt = _compute_jie_datetime(i, year)
            if jie_dt > birth_dt:
                delta = jie_dt - birth_dt
                return delta.total_seconds() / 86400.0, []
        # 出生在 小寒 之后 → 下一个节是次年立春
        lichun_next = _compute_jie_datetime(0, year + 1)
        delta = lichun_next - birth_dt
        return delta.total_seconds() / 86400.0, []

    def distance_to_prev_jie(birth_dt: datetime) -> tuple[float, list[str]]:
        """出生时间到上一个节的天数（精确到秒）

        Returns:
            (天数_float, 警告列表) — ephem 路径下警告列表为空
        """
        year = birth_dt.year
        for i in range(11, -1, -1):
            jie_dt = _compute_jie_datetime(i, year)
            if jie_dt < birth_dt:
                delta = birth_dt - jie_dt
                return delta.total_seconds() / 86400.0, []
        # 出生在 立春 之前 → 上一个节是前一年小寒
        xiaohan_prev = _compute_jie_datetime(11, year - 1)
        delta = birth_dt - xiaohan_prev
        return delta.total_seconds() / 86400.0, []

    def get_jie_datetime(year: int, jie_index: int) -> datetime:
        """获取指定年第 jie_index 个节的精确 CST datetime（公开 API）"""
        return _compute_jie_datetime(jie_index, year)

    def get_all_jie_datetimes(year: int) -> list[dict]:
        """获取指定年全部 12 个节的精确 CST datetime 列表"""
        return [
            {
                "index": i,
                "name": _JIE_NAMES[i],
                "longitude": _JIE_LONGITUDE[i],
                "datetime": _compute_jie_datetime(i, year).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for i in range(12)
        ]

    def get_jieqi_near_birth(birth_dt: datetime) -> dict:
        """出生时间附近的节气信息"""
        next_days, _ = distance_to_next_jie(birth_dt)
        prev_days, _ = distance_to_prev_jie(birth_dt)
        return {
            "next_jie_days": round(next_days, 4),
            "prev_jie_days": round(prev_days, 4),
            "warning": "",
        }


# ═══════════════════════════════════════════════════════════════
# 回退路径（ephem 不可用时使用近似表）
# ═══════════════════════════════════════════════════════════════

else:  # not _HAS_EPHEM

    from datetime import date

    def _jieqi_date_approx(jieqi_index: int, year: int) -> date:
        """返回第 jieqi_index 个节在 year 年的大致日期"""
        month, day = _JIEQI_SEED[jieqi_index]
        real_year = year + 1 if jieqi_index == 11 else year
        return date(real_year, month, day)

    def distance_to_next_jie(birth_dt: datetime) -> tuple[float, list[str]]:
        birth_date = birth_dt.date() if isinstance(birth_dt, datetime) else birth_dt
        year = birth_date.year
        for i in range(12):
            jie_date = _jieqi_date_approx(i, year)
            if jie_date > birth_date:
                return float((jie_date - birth_date).days), [WARNING_APPROXIMATE]
        next_lichun = _jieqi_date_approx(0, year + 1)
        return float((next_lichun - birth_date).days), [WARNING_APPROXIMATE]

    def distance_to_prev_jie(birth_dt: datetime) -> tuple[float, list[str]]:
        birth_date = birth_dt.date() if isinstance(birth_dt, datetime) else birth_dt
        year = birth_date.year
        for i in range(11, -1, -1):
            jie_date = _jieqi_date_approx(i, year)
            if jie_date < birth_date:
                return float((birth_date - jie_date).days), [WARNING_APPROXIMATE]
        prev_xiaohan = _jieqi_date_approx(11, year - 1)
        return float((birth_date - prev_xiaohan).days), [WARNING_APPROXIMATE]

    def get_jie_datetime(year: int, jie_index: int) -> datetime:
        d = _jieqi_date_approx(jie_index, year)
        return datetime(d.year, d.month, d.day, 12, 0, 0)

    def get_all_jie_datetimes(year: int) -> list[dict]:
        return [
            {
                "index": i,
                "name": _JIE_NAMES[i],
                "longitude": _JIE_LONGITUDE[i],
                "datetime": get_jie_datetime(year, i).strftime("%Y-%m-%d %H:%M:%S"),
                "approximate": True,
            }
            for i in range(12)
        ]

    def get_jieqi_near_birth(birth_dt: datetime) -> dict:
        return {
            "next_jie_days": distance_to_next_jie(birth_dt)[0],
            "prev_jie_days": distance_to_prev_jie(birth_dt)[0],
            "warning": WARNING_APPROXIMATE,
        }
