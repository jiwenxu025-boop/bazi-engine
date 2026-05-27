"""八字基础枚举: 天干 地支 五行 十神"""

from enum import Enum


class Wuxing(Enum):
    木 = "木"
    火 = "火"
    土 = "土"
    金 = "金"
    水 = "水"

    def __repr__(self):
        return self.value


class Tiangan(Enum):
    甲 = "甲"
    乙 = "乙"
    丙 = "丙"
    丁 = "丁"
    戊 = "戊"
    己 = "己"
    庚 = "庚"
    辛 = "辛"
    壬 = "壬"
    癸 = "癸"

    @property
    def wuxing(self) -> Wuxing:
        return TIANGAN_WUXING[self]

    @property
    def yinyang(self) -> str:
        return "阳" if self in (Tiangan.甲, Tiangan.丙, Tiangan.戊, Tiangan.庚, Tiangan.壬) else "阴"

    @property
    def index(self) -> int:
        return _TG_INDEX[self]

    def __repr__(self):
        return self.value


class Dizhi(Enum):
    子 = "子"
    丑 = "丑"
    寅 = "寅"
    卯 = "卯"
    辰 = "辰"
    巳 = "巳"
    午 = "午"
    未 = "未"
    申 = "申"
    酉 = "酉"
    戌 = "戌"
    亥 = "亥"

    @property
    def wuxing(self) -> Wuxing:
        return DIZHI_WUXING[self]

    @property
    def yinyang(self) -> str:
        return "阴" if self in (Dizhi.丑, Dizhi.卯, Dizhi.巳, Dizhi.未, Dizhi.酉, Dizhi.亥) else "阳"

    @property
    def index(self) -> int:
        return _DZ_INDEX[self]

    def __repr__(self):
        return self.value


class Shishen(Enum):
    比肩 = "比肩"
    劫财 = "劫财"
    食神 = "食神"
    伤官 = "伤官"
    偏财 = "偏财"
    正财 = "正财"
    偏官 = "偏官"  # 七杀
    正官 = "正官"
    偏印 = "偏印"  # 枭神
    正印 = "正印"

    def __repr__(self):
        return self.value


# ── internal index tables (used by properties above) ──

_TG_INDEX = {
    Tiangan.甲: 0, Tiangan.乙: 1, Tiangan.丙: 2, Tiangan.丁: 3, Tiangan.戊: 4,
    Tiangan.己: 5, Tiangan.庚: 6, Tiangan.辛: 7, Tiangan.壬: 8, Tiangan.癸: 9,
}

_DZ_INDEX = {
    Dizhi.子: 0, Dizhi.丑: 1, Dizhi.寅: 2, Dizhi.卯: 3, Dizhi.辰: 4, Dizhi.巳: 5,
    Dizhi.午: 6, Dizhi.未: 7, Dizhi.申: 8, Dizhi.酉: 9, Dizhi.戌: 10, Dizhi.亥: 11,
}

TIANGAN_WUXING = {
    Tiangan.甲: Wuxing.木, Tiangan.乙: Wuxing.木,
    Tiangan.丙: Wuxing.火, Tiangan.丁: Wuxing.火,
    Tiangan.戊: Wuxing.土, Tiangan.己: Wuxing.土,
    Tiangan.庚: Wuxing.金, Tiangan.辛: Wuxing.金,
    Tiangan.壬: Wuxing.水, Tiangan.癸: Wuxing.水,
}

DIZHI_WUXING = {
    Dizhi.子: Wuxing.水, Dizhi.丑: Wuxing.土, Dizhi.寅: Wuxing.木, Dizhi.卯: Wuxing.木,
    Dizhi.辰: Wuxing.土, Dizhi.巳: Wuxing.火, Dizhi.午: Wuxing.火, Dizhi.未: Wuxing.土,
    Dizhi.申: Wuxing.金, Dizhi.酉: Wuxing.金, Dizhi.戌: Wuxing.土, Dizhi.亥: Wuxing.水,
}

# ── index → enum lookup ──

_TG_BY_INDEX = {v: k for k, v in _TG_INDEX.items()}
_DZ_BY_INDEX = {v: k for k, v in _DZ_INDEX.items()}


def tiangan_by_index(i: int) -> Tiangan:
    return _TG_BY_INDEX[i % 10]


def dizhi_by_index(i: int) -> Dizhi:
    return _DZ_BY_INDEX[i % 12]


# ── 天干禄地 / 羊刃 ──

TIANGAN_LU = {
    Tiangan.甲: Dizhi.寅, Tiangan.乙: Dizhi.卯,
    Tiangan.丙: Dizhi.巳, Tiangan.丁: Dizhi.午,
    Tiangan.戊: Dizhi.巳, Tiangan.己: Dizhi.午,
    Tiangan.庚: Dizhi.申, Tiangan.辛: Dizhi.酉,
    Tiangan.壬: Dizhi.亥, Tiangan.癸: Dizhi.子,
}

TIANGAN_YANGREN = {
    Tiangan.甲: Dizhi.卯, Tiangan.乙: Dizhi.寅,
    Tiangan.丙: Dizhi.午, Tiangan.丁: Dizhi.巳,
    Tiangan.戊: Dizhi.午, Tiangan.己: Dizhi.巳,
    Tiangan.庚: Dizhi.酉, Tiangan.辛: Dizhi.申,
    Tiangan.壬: Dizhi.子, Tiangan.癸: Dizhi.亥,
}
