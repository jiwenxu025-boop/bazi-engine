"""古籍资料表与派生资料输出的回归测试。"""

from bazi_engine._constants import ZAISHA
from bazi_engine.enums import Dizhi
from bazi_engine.nayin_chain import find_all_nayin_relations


def test_zaisha_uses_the_correct_chou_mapping():
    assert ZAISHA[Dizhi.丑] == Dizhi.卯


def test_nayin_chain_does_not_emit_unverified_life_predictions():
    assert find_all_nayin_relations("海中金", "炉中火", "大林木", "路旁土") == []
