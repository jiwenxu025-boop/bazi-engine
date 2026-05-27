"""格局判定 — 月令透干优先原则"""

from .enums import Tiangan, Dizhi
from ._constants import DIZHI_CANGGAN
from .enums import TIANGAN_LU, TIANGAN_YANGREN
from .ten_gods import get_ten_god


def determine_pattern(month_branch: Dizhi, all_stems: list[Tiangan],
                      day_master: Tiangan) -> tuple[str, list[str]]:
    """返回 (格局名, 透干说明).

    all_stems: 四柱天干列表 [年干, 月干, 日干, 时干]

    优先级：
    1. 本气透干 → 取本气十神为格（建禄格/羊刃格特殊处理）
    2. 中气透干 → 取中气十神为格
    3. 余气透干 → 取余气十神为格
    4. 均不透 → 取本气十神为格
    """
    hidden_list = DIZHI_CANGGAN[month_branch]
    notes: list[str] = []

    for hs in hidden_list:
        if hs.stem in all_stems:
            # 透干！取此藏干对应的十神为格
            ss = get_ten_god(day_master, hs.stem)
            notes.append(f"月支{month_branch.value} {hs.level}{hs.stem.value}透干")

            # 特殊: 建禄格 / 羊刃格
            if hs.level == "本气":
                lu = TIANGAN_LU.get(day_master)
                yangren = TIANGAN_YANGREN.get(day_master)
                if month_branch == lu:
                    return "建禄格", notes
                if month_branch == yangren:
                    return "羊刃格", notes

            return f"{ss.value}格", notes

    # 无透干：取本气十神
    benqi = hidden_list[0]
    ss = get_ten_god(day_master, benqi.stem)
    notes.append(f"月支{month_branch.value}本气{benqi.stem.value}不透，取本气为格")
    return f"{ss.value}格", notes
