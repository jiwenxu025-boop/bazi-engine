"""Token budget helper tests."""

from bazi_engine._token_budget import estimate_tokens


def test_estimate_tokens_handles_chinese_and_english_text():
    assert estimate_tokens("甲木 test 123") > 0
