"""十神分配"""

from .enums import Shishen, Tiangan, Wuxing

# 五行动态: 生克关系
_WUXING_SHENG: dict[Wuxing, Wuxing] = {
    Wuxing.木: Wuxing.火, Wuxing.火: Wuxing.土, Wuxing.土: Wuxing.金,
    Wuxing.金: Wuxing.水, Wuxing.水: Wuxing.木,
}

_WUXING_KE: dict[Wuxing, Wuxing] = {
    Wuxing.木: Wuxing.土, Wuxing.土: Wuxing.水, Wuxing.水: Wuxing.火,
    Wuxing.火: Wuxing.金, Wuxing.金: Wuxing.木,
}




# 天干相克配对 (value-based, for string comparison)
TIANGAN_KE_PAIRS: set[tuple[str, str]] = {
    ("甲", "戊"), ("甲", "己"), ("乙", "戊"), ("乙", "己"),
    ("丙", "庚"), ("丙", "辛"), ("丁", "庚"), ("丁", "辛"),
    ("戊", "壬"), ("戊", "癸"), ("己", "壬"), ("己", "癸"),
    ("庚", "甲"), ("庚", "乙"), ("辛", "甲"), ("辛", "乙"),
    ("壬", "丙"), ("壬", "丁"), ("癸", "丙"), ("癸", "丁"),
}

def wuxing_relation(src: Wuxing, dst: Wuxing) -> str:
    """返回 src 对 dst 的生克关系字符串

    Returns: "生" | "克" | "被生" | "被克" | "比和"
    """
    if src == dst:
        return "比和"
    if _WUXING_SHENG[src] == dst:
        return "生"
    if _WUXING_KE[src] == dst:
        return "克"
    if _WUXING_SHENG[dst] == src:
        return "被生"
    if _WUXING_KE[dst] == src:
        return "被克"
    return "比和"

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
