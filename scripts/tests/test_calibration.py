"""校准数据库验证"""
from pathlib import Path
import sys
sys.path.insert(0, "..")

import pytest

from bazi_engine.calibration import CalibrationStore, get_store

CALIBRATION_STORE = Path(__file__).resolve().parents[1] / "data" / "calibration_store.json"


def require_calibration_store():
    if not CALIBRATION_STORE.exists():
        pytest.skip(f"calibration store not present: {CALIBRATION_STORE}")


def test_store_loads_known_events():
    """校准数据库应正确加载已知事件"""
    require_calibration_store()
    store = CalibrationStore()

    # 案例A
    ev = store.get_known_events("案例A")
    assert ev is not None, "案例A case not found"
    assert ev.get(2023) == "relationship", f"2023 should be relationship: {ev}"
    assert ev.get(2024) == "single", f"2024 should be single: {ev}"

    # 方飞翔
    ev2 = store.get_known_events("方飞翔")
    assert ev2 is not None
    assert ev2.get(2022) == "relationship"

    # 案例B
    ev3 = store.get_known_events("案例B")
    assert ev3 is not None

    print("[PASS] 已知事件加载 — 三案例全部正确")


def test_rule_stats():
    """规则统计应正确汇总"""
    require_calibration_store()
    store = CalibrationStore()
    stats = store.get_rule_stats("桃花")
    assert len(stats) >= 5, f"桃花 rules should be >=5: {len(stats)}"

    summary = store.get_rule_summary()
    assert summary["total_rules"] >= 8
    assert "天喜合动" in summary["verified_rules"]
    assert "卯辰穿" in summary["verified_rules"]

    print("[PASS] 规则统计 — 验证准确率")


def test_list_cases():
    """案例列表"""
    require_calibration_store()
    store = CalibrationStore()
    cases = store.list_cases()
    names = [c["name"] for c in cases]
    assert "案例A" in names
    assert "方飞翔" in names
    assert "案例B" in names
    print("[PASS] 案例列表 — 三案例全部注册")


def test_singleton_store():
    """get_store 应返回单例"""
    s1 = get_store()
    s2 = get_store()
    assert s1 is s2, "get_store should return singleton"
    print("[PASS] 单例模式")


def test_chart_integration():
    """build_chart calibrate=True 应自动加载 known_events"""
    from bazi_engine.chart import build_chart

    if not CALIBRATION_STORE.exists():
        chart = build_chart(
            name="案例A", gender="男",
            year=2007, month=8, day=26, hour=20,
            liunian_range=(2023, 2024),
            calibrate=True,
        )
        assert len(chart.annual_scans) == 2
        return

    chart = build_chart(
        name="案例A", gender="男",
        year=2007, month=8, day=26, hour=20,
        liunian_range=(2023, 2024),
        calibrate=True,
    )
    assert len(chart.annual_scans) == 2
    # 2023 桃花 信号应因 known_events(前一年无关系) 而产生适当输出
    scan_2023 = chart.annual_scans[0]
    taohua_2023 = [e for e in scan_2023.events if e.category == "桃花"]
    assert len(taohua_2023) >= 1, "2023 should have 桃花 signals"
    print("[PASS] chart 集成 — calibrate=True 正确加载")

    # 不带 calibrate 也应正常工作
    chart2 = build_chart(
        name="test", gender="男",
        year=2000, month=1, day=1, hour=12,
        liunian_range=(2023, 2024),
    )
    assert len(chart2.annual_scans) == 2
    print("[PASS] chart 集成 — 无 calibrate 正常工作")


if __name__ == "__main__":
    test_store_loads_known_events()
    test_rule_stats()
    test_list_cases()
    test_singleton_store()
    test_chart_integration()
    print("\n=== 全部校准数据库测试通过 ===")
