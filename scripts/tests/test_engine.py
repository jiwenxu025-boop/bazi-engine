"""八字引擎验证测试 — 用已知命例对账（JDN 精确日柱 v0.4.2+）"""
import sys
sys.path.insert(0, "..")

from bazi_engine.chart import build_chart
from bazi_engine.enums import Tiangan, Dizhi


def test_xujiwen():
    """案例A: 丁亥 戊申 壬辰 庚戌  偏印格  逆排"""
    chart = build_chart(
        name="案例A", gender="男",
        year=2007, month=8, day=26, hour=20,
    )

    # 四柱
    assert chart.year.stem == Tiangan.丁, f"年干: {chart.year.stem}"
    assert chart.year.branch == Dizhi.亥, f"年支: {chart.year.branch}"
    assert chart.month.stem == Tiangan.戊, f"月干: {chart.month.stem}"
    assert chart.month.branch == Dizhi.申, f"月支: {chart.month.branch}"
    assert chart.day.stem == Tiangan.壬, f"日干: {chart.day.stem}"
    assert chart.day.branch == Dizhi.辰, f"日支: {chart.day.branch}"
    assert chart.hour.stem == Tiangan.庚, f"时干: {chart.hour.stem}"
    assert chart.hour.branch == Dizhi.戌, f"时支: {chart.hour.branch}"

    # 日主
    assert chart.day_master == Tiangan.壬
    assert chart.day_pillar_source == "formula"

    # 格局
    assert chart.pattern == "偏印格", f"格局: {chart.pattern}"

    # 大运
    assert chart.start_age == 6, f"起运年龄: {chart.start_age}"
    assert chart.dayun_direction_str == "逆排", f"大运方向: {chart.dayun_direction_str}"

    # 十神
    assert chart.year.ten_god.value == "正财", f"年柱十神: {chart.year.ten_god}"
    assert chart.month.ten_god.value == "偏官", f"月柱十神: {chart.month.ten_god}"
    assert chart.hour.ten_god.value == "偏印", f"时柱十神: {chart.hour.ten_god}"

    print("[PASS] 案例A — 四柱/格局/大运/十神 全部正确 (JDN 日柱)")


def test_fangfeixiang():
    """案例B: 丙戌 丙申 庚寅 庚辰  建禄格  顺排
    出生日期经用户确认为 2006-08-29（非 2006-08-16）。
    JDN + WebSearch 确认: 2006-08-29 → 庚寅 ✓
    """
    chart = build_chart(
        name="案例B", gender="男",
        year=2006, month=8, day=29, hour=7,
    )

    # 四柱
    assert chart.year.stem == Tiangan.丙, f"年干: {chart.year.stem}"
    assert chart.year.branch == Dizhi.戌, f"年支: {chart.year.branch}"
    assert chart.month.stem == Tiangan.丙, f"月干: {chart.month.stem}"
    assert chart.month.branch == Dizhi.申, f"月支: {chart.month.branch}"
    assert chart.day.stem == Tiangan.庚, f"日干: {chart.day.stem}"
    assert chart.day.branch == Dizhi.寅, f"日支: {chart.day.branch}"
    assert chart.hour.stem == Tiangan.庚, f"时干: {chart.hour.stem}"
    assert chart.hour.branch == Dizhi.辰, f"时支: {chart.hour.branch}"

    # 日主: 庚
    assert chart.day_master == Tiangan.庚
    assert chart.day_pillar_source == "formula"

    # 格局: 申月本气庚透于时干/月干 → 建禄格
    assert chart.pattern == "建禄格", f"格局: {chart.pattern}"

    # 大运: 阳年男顺排
    assert chart.dayun_direction_str == "顺排", f"大运方向: {chart.dayun_direction_str}"
    assert chart.start_age == 3, f"起运年龄: {chart.start_age}"

    # 十神
    assert chart.year.ten_god.value == "偏官", f"年柱十神: {chart.year.ten_god}"
    assert chart.month.ten_god.value == "偏官", f"月柱十神: {chart.month.ten_god}"
    assert chart.hour.ten_god.value == "比肩", f"时柱十神: {chart.hour.ten_god}"

    print("[PASS] 案例B — 四柱/格局/大运/十神 全部正确 (JDN 日柱)")


def test_xuanxiaoya():
    """案例C: 丁亥 辛亥 丁未 甲辰  正印格  顺排
    出生日期经用户确认为 2007-11-09（非 2007-11-14）。
    JDN + WebSearch 确认: 2007-11-09 → 丁未 ✓
    """
    chart = build_chart(
        name="案例C", gender="女",
        year=2007, month=11, day=9, hour=7,
    )

    # 四柱
    assert chart.year.stem == Tiangan.丁, f"年干: {chart.year.stem}"
    assert chart.year.branch == Dizhi.亥, f"年支: {chart.year.branch}"
    assert chart.month.stem == Tiangan.辛, f"月干: {chart.month.stem}"
    assert chart.month.branch == Dizhi.亥, f"月支: {chart.month.branch}"
    assert chart.day.stem == Tiangan.丁, f"日干: {chart.day.stem}"
    assert chart.day.branch == Dizhi.未, f"日支: {chart.day.branch}"
    assert chart.hour.stem == Tiangan.甲, f"时干: {chart.hour.stem}"
    assert chart.hour.branch == Dizhi.辰, f"时支: {chart.hour.branch}"

    # 日主: 丁
    assert chart.day_master == Tiangan.丁
    assert chart.day_pillar_source == "formula"

    # 格局: 亥月本气壬不透，中气甲透于时干 → 正印格
    assert chart.pattern == "正印格", f"格局: {chart.pattern}"

    # 大运: 阴年女顺排
    assert chart.dayun_direction_str == "顺排", f"大运方向: {chart.dayun_direction_str}"
    assert chart.start_age == 10, f"起运年龄: {chart.start_age}"

    # 十神
    assert chart.year.ten_god.value == "比肩", f"年柱十神: {chart.year.ten_god}"
    assert chart.month.ten_god.value == "偏财", f"月柱十神: {chart.month.ten_god}"
    assert chart.hour.ten_god.value == "正印", f"时柱十神: {chart.hour.ten_god}"

    print("[PASS] 案例C — 四柱/格局/大运/十神 全部正确 (JDN 日柱)")


if __name__ == "__main__":
    test_xujiwen()
    test_fangfeixiang()
    test_xuanxiaoya()
    print("\n=== 全部测试通过 (JDN 精确日柱) ===")
