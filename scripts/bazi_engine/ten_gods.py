"""十神分配"""

from .enums import Tiangan, Wuxing, Shishen

# 五行动态: 生克关系
_WUXING_SHENG: dict[Wuxing, Wuxing] = {
    Wuxing.木: Wuxing.火, Wuxing.火: Wuxing.土, Wuxing.土: Wuxing.金,
    Wuxing.金: Wuxing.水, Wuxing.水: Wuxing.木,
}

_WUXING_KE: dict[Wuxing, Wuxing] = {
    Wuxing.木: Wuxing.土, Wuxing.土: Wuxing.水, Wuxing.水: Wuxing.火,
    Wuxing.火: Wuxing.金, Wuxing.金: Wuxing.木,
}


def wuxing_sheng(wx: Wuxing) -> Wuxing:
    """返回 wx 所生的五行"""
    return _WUXING_SHENG[wx]


def wuxing_ke(wx: Wuxing) -> Wuxing:
    """返回 wx 所克的五行"""
    return _WUXING_KE[wx]


def get_ten_god(day_master: Tiangan, other_stem: Tiangan) -> Shishen:
    """返回 other_stem 相对 day_master 的十神"""
    dm_wx = day_master.wuxing
    ot_wx = other_stem.wuxing
    same_yinyang = day_master.yinyang == other_stem.yinyang

    if dm_wx == ot_wx:
        return Shishen.比肩 if same_yinyang else Shishen.劫财

    # 我生者
    if _WUXING_SHENG[dm_wx] == ot_wx:
        return Shishen.食神 if same_yinyang else Shishen.伤官

    # 我克者
    if _WUXING_KE[dm_wx] == ot_wx:
        return Shishen.偏财 if same_yinyang else Shishen.正财

    # 克我者
    if _WUXING_KE[ot_wx] == dm_wx:
        return Shishen.偏官 if same_yinyang else Shishen.正官

    # 生我者
    return Shishen.偏印 if same_yinyang else Shishen.正印
