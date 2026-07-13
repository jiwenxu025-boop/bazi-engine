"""API module tests."""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


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
