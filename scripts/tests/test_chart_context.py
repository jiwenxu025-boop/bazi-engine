"""Shared chart context extraction tests."""

from bazi_engine._chart_context import extract_base_context


def test_extract_base_context_reads_public_four_pillars():
    chart_data = {
        "four_pillars": {
            "year": {"stem": "丁", "branch": "亥"},
            "month": {"stem": "戊", "branch": "申"},
            "day": {"stem": "壬", "branch": "辰"},
            "hour": {"stem": "庚", "branch": "戌"},
        },
    }

    ctx = extract_base_context(chart_data)

    assert ctx["pillars_str"] == "丁亥 戊申 壬辰 庚戌"
    assert ctx["day_branch"] == "辰"
