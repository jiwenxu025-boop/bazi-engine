"""Token budget helper tests."""

import logging

from bazi_engine._token_budget import (
    check_token_budget,
    estimate_messages_tokens,
    estimate_tokens,
    get_application_context_window,
    get_model_context_window,
    prepare_messages_for_request,
)


def test_estimate_tokens_handles_chinese_and_english_text():
    assert estimate_tokens("甲木 test 123") > 0


def test_v4_flash_registers_one_million_token_model_window(monkeypatch):
    monkeypatch.delenv("BAZI_LLM_CONTEXT_LIMIT", raising=False)

    assert get_model_context_window("deepseek-v4-flash") == 1_000_000
    assert get_application_context_window("deepseek-v4-flash") == 1_000_000
    assert get_application_context_window("deepseek-chat") == 64_000


def test_application_context_limit_can_use_but_not_exceed_model_window(monkeypatch):
    monkeypatch.setenv("BAZI_LLM_CONTEXT_LIMIT", "1000000")
    assert get_application_context_window("deepseek-v4-flash") == 1_000_000

    monkeypatch.setenv("BAZI_LLM_CONTEXT_LIMIT", "2000000")
    assert get_application_context_window("deepseek-v4-flash") == 1_000_000


def test_prepare_messages_truncates_safely_and_logs_no_content(monkeypatch, caplog):
    monkeypatch.setenv("BAZI_LLM_CONTEXT_LIMIT", "120")
    messages = [
        {"role": "system", "content": "Keep deterministic facts authoritative."},
        {"role": "user", "content": "old-context " * 80},
        {"role": "assistant", "content": "old-answer " * 80},
        {"role": "user", "content": "private-marker " * 80},
    ]

    with caplog.at_level(logging.INFO, logger="bazi_engine._token_budget"):
        prepared = prepare_messages_for_request(
            messages,
            "deepseek-v4-flash",
            20,
            operation="test_operation",
        )

    fits, _, available = check_token_budget(prepared, "deepseek-v4-flash", 20)
    assert fits
    assert estimate_messages_tokens(prepared) <= available
    assert prepared[0]["role"] == "system"
    assert prepared[-1]["role"] == "user"
    assert messages[-1]["content"] == "private-marker " * 80
    assert "operation=test_operation" in caplog.text
    assert "model_context_window=1000000" in caplog.text
    assert "application_context_window=120" in caplog.text
    assert "truncated=True" in caplog.text
    assert "private-marker" not in caplog.text
