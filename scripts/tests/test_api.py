"""API module tests."""

import importlib
import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import bazi_engine._chart_context as chart_context
from tests._chat_fixtures import chart_data_with_current_dayun


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 14)


def test_api_import_does_not_create_feedback_directory():
    feedback_dir = Path(__file__).resolve().parents[2] / "data" / "feedback"
    data_dir = feedback_dir.parent
    if feedback_dir.exists():
        if any(feedback_dir.iterdir()):
            pytest.skip(f"feedback directory is not empty: {feedback_dir}")
        feedback_dir.rmdir()
    if data_dir.exists() and not any(data_dir.iterdir()):
        data_dir.rmdir()

    sys.modules.pop("bazi_engine.api", None)
    importlib.import_module("bazi_engine.api")

    assert not feedback_dir.exists()


def test_api_module_imports_app():
    from bazi_engine.api import app

    assert app.title


def test_chart_stream_returns_rules_and_done_events(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    monkeypatch.setenv("BAZI_AI_ENABLED", "0")
    monkeypatch.setenv("BAZI_FUSION_ENGINE", "0")
    from bazi_engine.api import app

    client = TestClient(app)
    with client.stream(
        "GET",
        "/api/chart/stream",
        params={
            "name": "test",
            "gender": "男",
            "year": 2007,
            "month": 8,
            "day": 26,
            "hour": 20,
            "liunian_from": 2023,
            "liunian_to": 2024,
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"phase": "rules_done"' in body or '"phase":"rules_done"' in body
    assert "data: [DONE]" in body


def test_chart_api_returns_public_contract_shape(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    monkeypatch.setenv("BAZI_AI_ENABLED", "0")
    monkeypatch.setenv("BAZI_FUSION_ENGINE", "0")
    monkeypatch.setattr(chart_context, "date", FixedDate, raising=False)
    from bazi_engine.api import app

    client = TestClient(app)
    response = client.get(
        "/api/chart",
        params={
            "name": "test",
            "gender": "男",
            "year": 2007,
            "month": 8,
            "day": 26,
            "hour": 20,
            "liunian_from": 2023,
            "liunian_to": 2026,
        },
    )

    assert response.status_code == 200
    data = response.json()
    expected_top_level_keys = {
        "name",
        "gender",
        "birth",
        "day_pillar_source",
        "four_pillars",
        "minggong",
        "shengong",
        "taiyuan",
        "day_master",
        "pattern",
        "pattern_notes",
        "favorable",
        "yongshen",
        "dayun",
        "interactions",
        "spirits",
        "annual_scans",
        "warnings",
        "personality",
        "family",
        "life_stage",
        "void_gods",
        "nayin_relations",
        "changsheng",
        "palace_star",
        "tiaohou",
        "health_profile",
        "body_use",
        "current_context",
    }
    assert expected_top_level_keys <= data.keys()
    assert "pillars" not in data
    assert "family_result" not in data
    assert "personality_result" not in data

    assert set(data["four_pillars"]) == {"year", "month", "day", "hour"}
    assert {"stem", "branch", "nayin", "hidden_stems", "ten_god", "ten_gods_map"} <= data["four_pillars"]["day"].keys()
    assert {"direction", "start_age", "periods", "modulations", "interpretations"} <= data["dayun"].keys()
    assert {"tiangan", "dizhi"} <= data["interactions"].keys()
    assert len(data["annual_scans"]) == 4
    assert data["personality"]
    assert data["family"]
    assert data["palace_star"]
    assert data["body_use"]
    assert data["current_context"]["current_date"] == "2026-07-14"
    assert data["current_context"]["solar_age"] == 18
    assert data["current_context"]["liunian_age"] == 19
    assert data["current_context"]["current_dayun"]["ganzhi"] == "丙午"
    assert data["current_context"]["current_dayun"]["age_range"] == "16-25岁"
    assert data["current_context"]["current_liunian"]["year"] == 2026
    assert data["current_context"]["current_liunian"]["ganzhi"] == "丙午"
    assert data["current_context"]["current_liunian"]["dayun"] == "丙午"
    assert data["current_context"]["life_stage"] == data["life_stage"]


def test_feedback_reads_public_family_output(monkeypatch, tmp_path):
    import bazi_engine.api as api_module
    from bazi_engine.api import app

    monkeypatch.setattr(api_module, "_FEEDBACK_DIR", tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/feedback",
        json={
            "chart_data": {
                "name": "case",
                "family": {"level": "宽裕"},
            },
            "family_level": "普通",
        },
    )

    assert response.status_code == 200
    assert response.json()["discrepancy"] == "引擎推断: 宽裕, 用户反馈: 普通"

    feedback_files = list(tmp_path.glob("feedback_*.jsonl"))
    assert len(feedback_files) == 1
    assert '"engine_level": "宽裕"' in feedback_files[0].read_text(encoding="utf-8")


def test_chat_api_sends_corrected_current_context_to_model(monkeypatch):
    import bazi_engine.api as api_module
    import bazi_engine.chat as chat_module
    from bazi_engine.api import app

    captured = {}

    async def fake_stream(messages):
        captured["messages"] = messages
        yield 'data: {"token":"ok"}\n\n'
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(chart_context, "date", FixedDate, raising=False)
    monkeypatch.setattr(api_module, "_AI_ENABLED", True)
    monkeypatch.setattr(chat_module, "call_deepseek_stream", fake_stream)
    monkeypatch.setattr(chat_module, "validate_code", lambda _code: (True, 99, "ok"))
    monkeypatch.setattr(chat_module, "consume_code", lambda _code: (True, 98))

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
    client = TestClient(app)
    with client.stream(
        "POST",
        "/api/chat",
        json={
            "question": "【关于流年】我现在走什么大运？",
            "chart_data": chart,
            "activation_code": "TEST",
            "history": [
                {"role": "assistant", "content": "你走甲辰大运，30几岁到40几岁。"},
            ],
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "ok" in body
    messages = captured["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["content"] == "你走甲辰大运，30几岁到40几岁。"
    assert messages[-1]["content"] == "【关于流年】我现在走什么大运？"

    system_prompt = messages[0]["content"]
    assert "【当前事实快照】当前大运=丙午（16-25岁）" in system_prompt
    assert "current_context.current_dayun：丙午（16-25岁）" in system_prompt
    assert "2026年 19岁 丙午流年，丙午大运" in system_prompt
    assert "2026年 19岁 丙午流年，甲辰大运" not in system_prompt
    assert system_prompt.rfind("【最终事实约束】") > system_prompt.rfind("classical-texts.md")
