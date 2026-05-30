"""藏干虚神检测 — 月令藏干中未透出天干者为虚神

规则来源: advanced-techniques.md
验证: WebSearch 2026-05-26
"""

from dataclasses import dataclass

from ._constants import DIZHI_CANGGAN
from .enums import Dizhi, Shishen, Tiangan
from .ten_gods import get_ten_god


@dataclass
class VoidGod:
    """月令藏干中未透出天干者"""
    hidden_stem: Tiangan       # 虚神天干
    source_branch: Dizhi       # 来源地支（月支）
    level: str                 # "本气" | "中气" | "余气"
    ten_god: Shishen           # 相对于日主的十神
    is_favorable: bool | None  # 是否为喜用（None=未判断）
    interpretation: str        # 解释文本

    def to_dict(self) -> dict:
        return {
            "hidden_stem": self.hidden_stem.value,
            "source_branch": self.source_branch.value,
            "level": self.level,
            "ten_god": self.ten_god.value,
            "is_favorable": self.is_favorable,
            "interpretation": self.interpretation,
        }


def detect_void_gods(day_master: Tiangan, month_branch: Dizhi,
                     all_stems: list[Tiangan],
                     favorable_shishen: set[str] | None = None) -> list[VoidGod]:
    """检测月支藏干中未出现在四柱天干者 = 虚神。

    月令藏多透少，不透者为虚神。虚神得用者多名气/财富。

    Args:
        day_master: 日主天干
        month_branch: 月支
        all_stems: 四柱天干列表 [年干, 月干, 日干, 时干]
        favorable_shishen: 喜用十神集合（十神.value）

    Returns:
        List of VoidGod objects, one per non-revealed hidden stem
    """
    hidden_list = DIZHI_CANGGAN.get(month_branch, [])
    if not hidden_list:
        return []

    stem_values = {s.value for s in all_stems}
    results: list[VoidGod] = []

    for hs in hidden_list:
        if hs.stem.value not in stem_values:
            # 未透出 → 虚神
            ten_god = get_ten_god(day_master, hs.stem)
            is_fav = None
            if favorable_shishen is not None:
                is_fav = ten_god.value in favorable_shishen

            # 生成解释
            level_label = {"本气": "最深层隐性力量", "中气": "中层隐性力量", "余气": "浅层隐性力量"}
            depth = level_label.get(hs.level, "隐性力量")

            fav_note = ""
            if is_fav is True:
                fav_note = "，为喜用，虚神得用——主名气/财富/隐形贵人"
            elif is_fav is False:
                fav_note = "，为忌神，虚神不得用——主隐性压力/暗中小人"

            interpretation = (
                f"月支{month_branch.value}藏{hs.stem.value}（{hs.level}）不透于天干，"
                f"为虚神（{depth}）。"
                f"十神：{ten_god.value}{fav_note}。"
                f"大运/流年透出{hs.stem.value}或冲合{month_branch.value}时，虚神\"变现\"，"
                f"有关键事件发生。"
            )

            results.append(VoidGod(
                hidden_stem=hs.stem,
                source_branch=month_branch,
                level=hs.level,
                ten_god=ten_god,
                is_favorable=is_fav,
                interpretation=interpretation,
            ))

    return results


def find_all_void_gods(day_master: Tiangan, month_branch: Dizhi,
                       all_stems: list[Tiangan],
                       favorable_shishen: set[str] | None = None) -> list[VoidGod]:
    """收集器: 检测所有虚神"""
    return detect_void_gods(day_master, month_branch, all_stems, favorable_shishen)
