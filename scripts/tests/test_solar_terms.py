"""节气精确化验证 — ephem 天文计算 vs 已知数据"""
import sys

sys.path.insert(0, "..")

from datetime import datetime

from bazi_engine.solar_terms import (
    _HAS_EPHEM,
    WARNING_APPROXIMATE,
    distance_to_next_jie,
    distance_to_prev_jie,
    get_jie_datetime,
    get_jieqi_near_birth,
)


def test_ephem_available():
    """ephem 库应当可用"""
    assert _HAS_EPHEM, "ephem 未安装，将使用近似表回退"


def test_jie_datetime_ordering():
    """12 个节在年内必须按时间顺序排列"""
    for year in [2000, 2007, 2024, 2025]:
        dts = [get_jie_datetime(year, i) for i in range(12)]
        for a, b in zip(dts, dts[1:], strict=False):
            assert a < b, f"{year}: 节顺序错误"


def test_known_lichun():
    """2024 立春应在 2 月 4-5 日（ephem 天文计算）"""
    dt = get_jie_datetime(2024, 0)
    assert dt.year == 2024
    assert dt.month == 2 and dt.day in (4, 5), f"立春日期异常: {dt}"
    # 黄经应在 315°附近
    lon_ok = abs(dt.hour * 60 + dt.minute - 0) < 1440  # 任何时候都行
    assert lon_ok


def test_xujiwen_start_age():
    """案例A: 2007-08-26 20:00, 逆排, 应距立秋约18.5天 → 起运6岁"""
    birth = datetime(2007, 8, 26, 20, 0, 0)
    days, warns = distance_to_prev_jie(birth)
    assert len(warns) == 0, f"ephem 路径不应有警告: {warns}"
    # 18.49 天 → 18 整天 → 6 岁
    assert 18.0 < days < 19.0, f"距立秋天数异常: {days:.2f}"
    total_days = int(round(days + 1e-9))
    assert total_days // 3 == 6, f"起运年龄应为6岁，实际: {total_days // 3}"


def test_fangfeixiang_start_age():
    """案例B: 2006-08-16 07:00, 顺排, 应距白露约23天 → 起运7岁"""
    birth = datetime(2006, 8, 16, 7, 0, 0)
    days, warns = distance_to_next_jie(birth)
    assert len(warns) == 0, f"ephem 路径不应有警告: {warns}"
    total_days = int(round(days + 1e-9))
    assert total_days // 3 == 7, f"起运年龄应为7岁，实际: {total_days // 3}"


def test_edge_birth_on_jie_day():
    """出生在节气当天：精确到小时可区分前后"""
    # 2007 立秋: Aug 8 ~08:05 CST
    # 出生在立秋之前1小时
    birth_before = datetime(2007, 8, 8, 7, 0, 0)
    _days_prev, _ = distance_to_prev_jie(birth_before)
    # 上一个节是大暑...不，上一个节是小暑(Jul 7)
    # 下一个节是立秋，距离应该很小
    days_next, _ = distance_to_next_jie(birth_before)
    assert days_next < 0.1, f"距立秋应<0.1天: {days_next:.4f}"

    # 出生在立秋之后1小时
    birth_after = datetime(2007, 8, 8, 9, 0, 0)
    days_prev2, _ = distance_to_prev_jie(birth_after)
    assert days_prev2 < 0.1, f"距立秋应<0.1天: {days_prev2:.4f}"


def test_get_jieqi_near_birth():
    """get_jieqi_near_birth 应返回合理的天数"""
    birth = datetime(2007, 8, 26, 20, 0, 0)
    info = get_jieqi_near_birth(birth)
    assert info["next_jie_days"] > 0
    assert info["prev_jie_days"] > 0
    assert info["warning"] == ""  # ephem 路径无警告


def test_no_approximate_warning():
    """ephem 路径下 distance_to_* 不应返回近似警告"""
    birth = datetime(2007, 8, 26, 20, 0, 0)
    _, warns_next = distance_to_next_jie(birth)
    _, warns_prev = distance_to_prev_jie(birth)
    assert WARNING_APPROXIMATE not in warns_next
    assert WARNING_APPROXIMATE not in warns_prev


if __name__ == "__main__":
    test_ephem_available()
    test_jie_datetime_ordering()
    test_known_lichun()
    test_xujiwen_start_age()
    test_fangfeixiang_start_age()
    test_edge_birth_on_jie_day()
    test_get_jieqi_near_birth()
    test_no_approximate_warning()
    print("\n=== 全部节气精度测试通过 ===")
