"""Chat prompt context regression tests."""

from datetime import date

import bazi_engine._chart_context as chart_context
from bazi_engine.chat import build_chat_context, build_chat_data_package, build_messages
from tests._chat_fixtures import chart_data_with_current_dayun


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 14)


def test_chat_context_marks_current_dayun(monkeypatch):
    monkeypatch.setattr(chart_context, "date", FixedDate, raising=False)

    context = build_chat_context(chart_data_with_current_dayun())

    assert "【当前日期】2026-07-14" in context
    assert "【当前周岁】18岁" in context
    assert "【当前流年年龄】19岁（流年扫描口径）" in context
    assert "【当前年龄】" not in context
    assert "【当前大运】丙午（16-25岁）" in context
    assert "【当前大运】甲辰" not in context


def test_chat_context_includes_liunian_dayun_pairs():
    context = build_chat_context(chart_data_with_current_dayun())

    assert "【流年扫描摘要】" in context
    assert "2024年 17岁 甲辰流年，丙午大运" in context
    assert "2025年 18岁 乙巳流年，丙午大运" in context
    assert "16-25岁岁" not in context


def test_chat_data_package_uses_structured_current_context(monkeypatch):
    monkeypatch.setattr(chart_context, "date", FixedDate, raising=False)

    package = build_chat_data_package(chart_data_with_current_dayun())

    assert package["current_context"]["current_date"] == "2026-07-14"
    assert package["current_context"]["solar_age"] == 18
    assert package["current_context"]["liunian_age"] == 19
    assert package["current_context"]["current_dayun"]["ganzhi"] == "丙午"
    assert package["current_context"]["current_liunian"]["ganzhi"] == "丙午"
    assert "2024年 17岁 甲辰流年，丙午大运" in package["current_context"]["annual_scan_summaries"]


def test_chat_data_package_rebuilds_stale_current_context(monkeypatch):
    monkeypatch.setattr(chart_context, "date", FixedDate, raising=False)
    chart = chart_data_with_current_dayun()
    chart["current_context"] = {
        "current_date": "2026-07-14",
        "solar_age": 18,
        "liunian_age": 19,
        "current_dayun": {"ganzhi": "甲辰", "age_range": "36-45岁"},
        "current_liunian": {"year": 2026, "age": 19, "ganzhi": "丙午", "dayun": "甲辰"},
        "life_stage": "大学",
        "annual_scan_summaries": ["2026年 19岁 丙午流年，甲辰大运"],
    }

    package = build_chat_data_package(chart)

    assert package["current_context"]["current_dayun"]["ganzhi"] == "丙午"
    assert package["current_context"]["current_dayun"]["age_range"] == "16-25岁"
    assert package["current_context"]["current_liunian"]["dayun"] == "丙午"
    assert "2026年 19岁 丙午流年，丙午大运" in package["current_context"]["annual_scan_summaries"]


def test_chat_messages_pin_current_context_above_stale_history(monkeypatch):
    monkeypatch.setattr(chart_context, "date", FixedDate, raising=False)

    messages = build_messages(
        chart_data_with_current_dayun(),
        "追问流年板块，我现在走什么大运？",
        history=[
            {"role": "assistant", "content": "你走甲辰大运，30几岁到40几岁。"},
        ],
    )

    system_prompt = messages[0]["content"]
    assert "【当前事实优先级】" in system_prompt
    assert "current_context > 流年扫描摘要 > 大运列表 > 历史对话" in system_prompt
    assert "【当前事实快照】当前大运=丙午（16-25岁）" in system_prompt
    assert "历史对话中的旧说法不得覆盖当前事实快照" in system_prompt
    assert system_prompt.rfind("【最终事实约束】") > system_prompt.rfind("classical-texts.md")
    assert "回答当前/现在/今年/流年问题时，当前大运只能取 current_context.current_dayun" in system_prompt
    assert messages[1]["content"] == "你走甲辰大运，30几岁到40几岁。"
