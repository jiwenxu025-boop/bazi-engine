"""API module tests."""

import importlib
import json
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


def test_chart_stream_post_returns_rules_and_done_events(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_REVIEW", "0")
    monkeypatch.setenv("BAZI_AI_ENABLED", "0")
    monkeypatch.setenv("BAZI_FUSION_ENGINE", "0")
    from bazi_engine.api import app

    client = TestClient(app)
    with client.stream(
        "POST",
        "/api/chart/stream",
        json={
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


def test_public_batch_is_disabled(monkeypatch):
    import bazi_engine.api as api_module
    from bazi_engine.api import app

    monkeypatch.setattr(api_module, "_IS_PUBLIC", True)
    response = TestClient(app).post("/api/batch", json=[])

    assert response.status_code == 403


def test_chart_stream_rejects_oversized_request_body():
    from bazi_engine.api import app

    response = TestClient(app).post(
        "/api/chart/stream",
        json={
            "name": "x" * 40000,
            "gender": "男",
            "year": 2007,
            "month": 8,
            "day": 26,
            "hour": 20,
        },
    )

    assert response.status_code == 413


def test_activation_quota_uses_post_body(monkeypatch):
    import bazi_engine.chat as chat_module
    from bazi_engine.api import app

    monkeypatch.setattr(chat_module, "validate_code", lambda code: (code == "VALID", 7, "有效"))
    client = TestClient(app)

    assert client.get("/api/chat/quota", params={"code": "VALID"}).json()["has_code"] is False
    assert client.post("/api/chat/quota", json={"code": "VALID"}).json() == {
        "has_code": True,
        "remaining": 7,
    }


def test_admin_codes_requires_a_request_header(monkeypatch):
    import bazi_engine.api as api_module
    import bazi_engine.chat as chat_module
    from bazi_engine.api import app

    monkeypatch.setattr(api_module, "_ADMIN_KEY", "admin-test")
    monkeypatch.setattr(chat_module, "_load_codes", lambda: {})
    client = TestClient(app)

    assert client.get("/api/admin/codes", params={"key": "admin-test"}).status_code == 403
    assert client.get("/api/admin/codes", headers={"X-Admin-Key": "admin-test"}).status_code == 200


def test_public_mode_ignores_persisted_demo_codes(monkeypatch, tmp_path):
    import bazi_engine.chat as chat_module

    codes_file = tmp_path / "activation_codes.json"
    codes_file.write_text(
        json.dumps({"DEMO001": {"剩余": 3}, "PAID001": {"剩余": 5}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setenv("BAZI_PUBLIC", "1")
    monkeypatch.setattr(chat_module, "_ACTIVATION_FILE", codes_file)

    assert chat_module._load_codes() == {"PAID001": {"剩余": 5}}


def test_fusion_stream_sends_cleaned_full_report(monkeypatch):
    """独立融合流结束时应发送清洗后的全文供前端覆盖原始 token。"""
    import bazi_engine.personality_fusion as fusion_module
    from bazi_engine.api import app

    monkeypatch.setenv("BAZI_FUSION_ENGINE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    def fake_generate(_data_package, on_chunk=None, result_metadata=None):
        if on_chunk:
            on_chunk("原始藏干内容")
        if result_metadata is not None:
            result_metadata.update({
                "prompt_version": "test-v1",
                "model": "test-model",
                "temperature": 0.3,
                "repaired": True,
            })
        return "清洗后的完整报告。"

    monkeypatch.setattr(fusion_module, "generate_fusion_report", fake_generate)
    client = TestClient(app)
    with client.stream(
        "POST",
        "/api/personality/fusion/stream",
        json={"personality": {"traits": {"社交": "内敛"}}},
    ) as response:
        body = "".join(response.iter_text())

    events = [
        json.loads(line[6:])
        for line in body.splitlines()
        if line.startswith("data: {")
    ]
    done = next(event for event in events if event.get("done"))
    assert response.status_code == 200
    assert done["full"] == "清洗后的完整报告。"
    assert done["length"] == len(done["full"])
    assert done["meta"]["prompt_version"] == "test-v1"
    assert done["meta"]["repaired"] is True


def test_fusion_feedback_saves_metadata_without_report_or_birth_data(monkeypatch, tmp_path):
    """融合反馈只保存分析元数据和报告哈希，不落报告正文或出生资料。"""
    import bazi_engine.api as api_module
    from bazi_engine.api import app

    monkeypatch.setattr(api_module, "_FEEDBACK_DIR", tmp_path)
    client = TestClient(app)
    response = client.post(
        "/api/personality/fusion/feedback",
        json={
            "rating": "partial",
            "inaccurate_section": "analysis",
            "report_text": "这是一份用于测试的融合报告。",
            "birth": {"year": 2001, "month": 5, "day": 16},
            "generation": {
                "prompt_version": "test-v1",
                "model": "deepseek-chat",
                "temperature": 0.3,
                "repaired": False,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["saved"] is True
    feedback_files = list(tmp_path.glob("fusion_feedback_*.jsonl"))
    assert len(feedback_files) == 1
    saved_text = feedback_files[0].read_text(encoding="utf-8")
    record = json.loads(saved_text)
    assert record["rating"] == "partial"
    assert record["inaccurate_section"] == "analysis"
    assert record["prompt_version"] == "test-v1"
    assert record["report_length"] == len("这是一份用于测试的融合报告。")
    assert len(record["report_hash"]) == 64
    assert "report_text" not in record
    assert "birth" not in record
    assert "2001" not in saved_text


def test_fusion_feedback_rejects_invalid_rating(monkeypatch, tmp_path):
    import bazi_engine.api as api_module
    from bazi_engine.api import app

    monkeypatch.setattr(api_module, "_FEEDBACK_DIR", tmp_path)
    client = TestClient(app)
    response = client.post(
        "/api/personality/fusion/feedback",
        json={"rating": "unknown", "report_text": "报告正文。"},
    )

    assert response.status_code == 400
    assert not list(tmp_path.iterdir())


def test_admin_fusion_feedback_returns_privacy_safe_summary(monkeypatch, tmp_path):
    import bazi_engine.api as api_module
    from bazi_engine.api import app

    monkeypatch.setattr(api_module, "_FEEDBACK_DIR", tmp_path)
    monkeypatch.setattr(api_module, "_ADMIN_KEY", "admin-test")
    feedback_file = tmp_path / f"fusion_feedback_{date.today().isoformat()}.jsonl"
    feedback_file.write_text(
        json.dumps({
            "timestamp": "2026-07-16T12:00:00",
            "rating": "partial",
            "inaccurate_section": "analysis",
            "report_hash": "secret-hash",
            "report_length": 800,
            "prompt_version": "test-v1",
            "model": "deepseek-chat",
            "temperature": 0.3,
            "repaired": True,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    client = TestClient(app)
    response = client.get(
        "/api/admin/fusion-feedback",
        params={"days": 0},
        headers={"X-Admin-Key": "admin-test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 1
    assert data["rating_distribution"] == {"partial": 1}
    assert data["section_distribution"] == {"analysis": 1}
    assert data["prompt_versions"] == {"test-v1": 1}
    assert data["model_distribution"] == {"deepseek-chat": 1}
    assert data["temperature_distribution"] == {"0.3": 1}
    assert data["repaired_rate"] == "100.0%"
    assert "report_hash" not in data["recent"][0]


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
            "engine_level": "宽裕",
            "family_level": "普通",
        },
    )

    assert response.status_code == 200
    assert response.json()["discrepancy"] == "引擎推断: 宽裕, 用户反馈: 普通"

    feedback_files = list(tmp_path.glob("feedback_*.jsonl"))
    assert len(feedback_files) == 1
    record = json.loads(feedback_files[0].read_text(encoding="utf-8"))
    assert record == {
        "timestamp": record["timestamp"],
        "engine_level": "宽裕",
        "user_level": "普通",
        "discrepancy": True,
        "discrepancy_detail": "引擎推断: 宽裕, 用户反馈: 普通",
    }


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
