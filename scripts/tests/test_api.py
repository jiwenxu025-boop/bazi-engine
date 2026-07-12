"""API module tests."""

import importlib
from pathlib import Path
import sys

import pytest


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
