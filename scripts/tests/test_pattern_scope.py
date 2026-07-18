"""Regression coverage for pattern branches that share five-element maps."""

from bazi_engine.enums import Tiangan
from bazi_engine.pattern import validate_pattern


def test_food_god_pattern_can_check_seal_control_without_unbound_local_error():
    result = validate_pattern(
        "食神格",
        Tiangan.甲,
        [
            {"stem": "丁", "ten_god": "食神", "source": "stem"},
            {"stem": "壬", "ten_god": "偏印", "source": "stem"},
        ],
        [],
        weighted_scores={"食神": 4.0, "偏印": 4.0},
    )

    assert any("印克食" in issue or "枭神夺食" in issue for issue in result["issues"])
