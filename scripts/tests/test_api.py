"""API module tests."""

import importlib
from pathlib import Path
import sys

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
