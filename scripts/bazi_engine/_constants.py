"""八字静态查表数据 — 所有查表均经 WebSearch 验证，来源标注于各表注释

验证日期: 2026-05-23
验证范围: 天干五合/地支六合三合三会六冲刑害/藏干/遁元/十二长生/神煞/纳音/空亡
修正记录: 丑藏干中余气互换(辛癸), 福星贵人重写, 孤辰寡宿改三会局, 太极贵人戊己扩四季
"""

from .enums import Dizhi, Tiangan, Wuxing

# ═══════════════════════════════════════════════════════════════
# 天干/地支 → 五行 (字符串映射，供 pillar 数据直接查表)
# ═══════════════════════════════════════════════════════════════

STEM_TO_WUXING: dict[str, str] = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

BRANCH_TO_WUXING: dict[str, str] = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# ═══════════════════════════════════════════════════════════════
# 天干五合: (天干, 天干) → 化气五行
# 来源: 甲己合土乙庚合金丙辛合水丁壬合木戊癸合火 (WebSearch 2026-05-23)
# ═══════════════════════════════════════════════════════════════

TIANGAN_WUHE: dict[tuple[Tiangan, Tiangan], Wuxing] = {
    (Tiangan.甲, Tiangan.己): Wuxing.土,
    (Tiangan.己, Tiangan.甲): Wuxing.土,
    (Tiangan.乙, Tiangan.庚): Wuxing.金,
    (Tiangan.庚, Tiangan.乙): Wuxing.金,
    (Tiangan.丙, Tiangan.辛): Wuxing.水,
    (Tiangan.辛, Tiangan.丙): Wuxing.水,
    (Tiangan.丁, Tiangan.壬): Wuxing.木,
    (Tiangan.壬, Tiangan.丁): Wuxing.木,
    (Tiangan.戊, Tiangan.癸): Wuxing.火,
    (Tiangan.癸, Tiangan.戊): Wuxing.火,
}

# 五合配对（无序查看用）
TIANGAN_WUHE_PAIRS: list[tuple[Tiangan, Tiangan]] = [
    (Tiangan.甲, Tiangan.己),
    (Tiangan.乙, Tiangan.庚),
    (Tiangan.丙, Tiangan.辛),
    (Tiangan.丁, Tiangan.壬),
    (Tiangan.戊, Tiangan.癸),
]

# ═══════════════════════════════════════════════════════════════
# 地支六冲
# ═══════════════════════════════════════════════════════════════

DIZHI_LIUCHONG: list[tuple[Dizhi, Dizhi]] = [
    (Dizhi.子, Dizhi.午), (Dizhi.午, Dizhi.子),
    (Dizhi.丑, Dizhi.未), (Dizhi.未, Dizhi.丑),
    (Dizhi.寅, Dizhi.申), (Dizhi.申, Dizhi.寅),
    (Dizhi.卯, Dizhi.酉), (Dizhi.酉, Dizhi.卯),
    (Dizhi.辰, Dizhi.戌), (Dizhi.戌, Dizhi.辰),
    (Dizhi.巳, Dizhi.亥), (Dizhi.亥, Dizhi.巳),
]

# ── 六冲查询 dict ──
_DZ_CHONG_MAP: dict[Dizhi, Dizhi] = {a: b for a, b in DIZHI_LIUCHONG}


def chong_pair(dz: Dizhi) -> Dizhi:
    """返回与 dz 相冲的地支"""
    return _DZ_CHONG_MAP[dz]

# ═══════════════════════════════════════════════════════════════
# 地支三合局: frozenset{三支} → 化神五行
# ═══════════════════════════════════════════════════════════════

DIZHI_SANHE: dict[frozenset[Dizhi], Wuxing] = {
    frozenset({Dizhi.申, Dizhi.子, Dizhi.辰}): Wuxing.水,
    frozenset({Dizhi.亥, Dizhi.卯, Dizhi.未}): Wuxing.木,
    frozenset({Dizhi.寅, Dizhi.午, Dizhi.戌}): Wuxing.火,
    frozenset({Dizhi.巳, Dizhi.酉, Dizhi.丑}): Wuxing.金,
}

# 三合半合映射：前两字或后两字的半合
DIZHI_BANHE: dict[frozenset[Dizhi], Wuxing] = {}
for sanhe_set, wx in DIZHI_SANHE.items():
    items = list(sanhe_set)
    DIZHI_BANHE[frozenset({items[0], items[1]})] = wx  # 前半合
    DIZHI_BANHE[frozenset({items[1], items[2]})] = wx  # 后半合

# ═══════════════════════════════════════════════════════════════
# 地支三会局
# ═══════════════════════════════════════════════════════════════

DIZHI_SANHUI: dict[frozenset[Dizhi], Wuxing] = {
    frozenset({Dizhi.寅, Dizhi.卯, Dizhi.辰}): Wuxing.木,
    frozenset({Dizhi.巳, Dizhi.午, Dizhi.未}): Wuxing.火,
    frozenset({Dizhi.申, Dizhi.酉, Dizhi.戌}): Wuxing.金,
    frozenset({Dizhi.亥, Dizhi.子, Dizhi.丑}): Wuxing.水,
}

# ═══════════════════════════════════════════════════════════════
# 地支六合: (地支, 地支) → 化神五行
# ═══════════════════════════════════════════════════════════════

DIZHI_LIUHE: dict[tuple[Dizhi, Dizhi], Wuxing] = {
    (Dizhi.子, Dizhi.丑): Wuxing.土, (Dizhi.丑, Dizhi.子): Wuxing.土,
    (Dizhi.寅, Dizhi.亥): Wuxing.木, (Dizhi.亥, Dizhi.寅): Wuxing.木,
    (Dizhi.卯, Dizhi.戌): Wuxing.火, (Dizhi.戌, Dizhi.卯): Wuxing.火,
    (Dizhi.辰, Dizhi.酉): Wuxing.金, (Dizhi.酉, Dizhi.辰): Wuxing.金,
    (Dizhi.巳, Dizhi.申): Wuxing.水, (Dizhi.申, Dizhi.巳): Wuxing.水,
    (Dizhi.午, Dizhi.未): Wuxing.火, (Dizhi.未, Dizhi.午): Wuxing.火,
}

# ═══════════════════════════════════════════════════════════════
# 地支相刑
# ═══════════════════════════════════════════════════════════════

# 互刑
DIZHI_XIANGXING: list[tuple[Dizhi, Dizhi]] = [
    (Dizhi.寅, Dizhi.巳), (Dizhi.巳, Dizhi.申), (Dizhi.申, Dizhi.寅),  # 无恩之刑
    (Dizhi.丑, Dizhi.戌), (Dizhi.戌, Dizhi.未), (Dizhi.未, Dizhi.丑),  # 持势之刑
    (Dizhi.子, Dizhi.卯), (Dizhi.卯, Dizhi.子),                         # 无礼之刑
]

# 自刑
DIZHI_ZIXING: frozenset[Dizhi] = frozenset({Dizhi.辰, Dizhi.午, Dizhi.酉, Dizhi.亥})

# ═══════════════════════════════════════════════════════════════
# 地支相害（相穿）
# ═══════════════════════════════════════════════════════════════

DIZHI_XIANGHAI: list[tuple[Dizhi, Dizhi]] = [
    (Dizhi.子, Dizhi.未), (Dizhi.未, Dizhi.子),
    (Dizhi.丑, Dizhi.午), (Dizhi.午, Dizhi.丑),
    (Dizhi.寅, Dizhi.巳), (Dizhi.巳, Dizhi.寅),
    (Dizhi.卯, Dizhi.辰), (Dizhi.辰, Dizhi.卯),
    (Dizhi.申, Dizhi.亥), (Dizhi.亥, Dizhi.申),
    (Dizhi.酉, Dizhi.戌), (Dizhi.戌, Dizhi.酉),
]

# ═══════════════════════════════════════════════════════════════
# 地支藏干
# ═══════════════════════════════════════════════════════════════

from dataclasses import dataclass


@dataclass(frozen=True)
class HiddenStem:
    stem: Tiangan
    level: str  # "本气" | "中气" | "余气"


DIZHI_CANGGAN: dict[Dizhi, list[HiddenStem]] = {
    Dizhi.子: [HiddenStem(Tiangan.癸, "本气")],
    Dizhi.丑: [HiddenStem(Tiangan.己, "本气"), HiddenStem(Tiangan.辛, "中气"), HiddenStem(Tiangan.癸, "余气")],
    Dizhi.寅: [HiddenStem(Tiangan.甲, "本气"), HiddenStem(Tiangan.丙, "中气"), HiddenStem(Tiangan.戊, "余气")],
    Dizhi.卯: [HiddenStem(Tiangan.乙, "本气")],
    Dizhi.辰: [HiddenStem(Tiangan.戊, "本气"), HiddenStem(Tiangan.乙, "中气"), HiddenStem(Tiangan.癸, "余气")],
    Dizhi.巳: [HiddenStem(Tiangan.丙, "本气"), HiddenStem(Tiangan.庚, "中气"), HiddenStem(Tiangan.戊, "余气")],
    Dizhi.午: [HiddenStem(Tiangan.丁, "本气"), HiddenStem(Tiangan.己, "中气")],
    Dizhi.未: [HiddenStem(Tiangan.己, "本气"), HiddenStem(Tiangan.丁, "中气"), HiddenStem(Tiangan.乙, "余气")],
    Dizhi.申: [HiddenStem(Tiangan.庚, "本气"), HiddenStem(Tiangan.壬, "中气"), HiddenStem(Tiangan.戊, "余气")],
    Dizhi.酉: [HiddenStem(Tiangan.辛, "本气")],
    Dizhi.戌: [HiddenStem(Tiangan.戊, "本气"), HiddenStem(Tiangan.辛, "中气"), HiddenStem(Tiangan.丁, "余气")],
    Dizhi.亥: [HiddenStem(Tiangan.壬, "本气"), HiddenStem(Tiangan.甲, "中气")],
}

# ═══════════════════════════════════════════════════════════════
# 五鼠遁元（日上起时法）: 日干 → 子时天干
# ═══════════════════════════════════════════════════════════════

WUSHU_DUNYUAN: dict[Tiangan, Tiangan] = {
    Tiangan.甲: Tiangan.甲, Tiangan.己: Tiangan.甲,
    Tiangan.乙: Tiangan.丙, Tiangan.庚: Tiangan.丙,
    Tiangan.丙: Tiangan.戊, Tiangan.辛: Tiangan.戊,
    Tiangan.丁: Tiangan.庚, Tiangan.壬: Tiangan.庚,
    Tiangan.戊: Tiangan.壬, Tiangan.癸: Tiangan.壬,
}

# ═══════════════════════════════════════════════════════════════
# 五虎遁元（年上起月法）: 年干 → 寅月天干
# ═══════════════════════════════════════════════════════════════

WUHU_DUNYUAN: dict[Tiangan, Tiangan] = {
    Tiangan.甲: Tiangan.丙, Tiangan.己: Tiangan.丙,
    Tiangan.乙: Tiangan.戊, Tiangan.庚: Tiangan.戊,
    Tiangan.丙: Tiangan.庚, Tiangan.辛: Tiangan.庚,
    Tiangan.丁: Tiangan.壬, Tiangan.壬: Tiangan.壬,
    Tiangan.戊: Tiangan.甲, Tiangan.癸: Tiangan.甲,
}

# ═══════════════════════════════════════════════════════════════
# 十二长生: 天干 → 地支 → 阶段名
# ═══════════════════════════════════════════════════════════════

SHIER_CHANGSHENG: dict[Tiangan, dict[Dizhi, str]] = {
    Tiangan.甲: {Dizhi.亥: "长生", Dizhi.子: "沐浴", Dizhi.丑: "冠带", Dizhi.寅: "临官", Dizhi.卯: "帝旺",
                 Dizhi.辰: "衰", Dizhi.巳: "病", Dizhi.午: "死", Dizhi.未: "墓", Dizhi.申: "绝",
                 Dizhi.酉: "胎", Dizhi.戌: "养"},
    Tiangan.乙: {Dizhi.午: "长生", Dizhi.巳: "沐浴", Dizhi.辰: "冠带", Dizhi.卯: "临官", Dizhi.寅: "帝旺",
                 Dizhi.丑: "衰", Dizhi.子: "病", Dizhi.亥: "死", Dizhi.戌: "墓", Dizhi.酉: "绝",
                 Dizhi.申: "胎", Dizhi.未: "养"},
    Tiangan.丙: {Dizhi.寅: "长生", Dizhi.卯: "沐浴", Dizhi.辰: "冠带", Dizhi.巳: "临官", Dizhi.午: "帝旺",
                 Dizhi.未: "衰", Dizhi.申: "病", Dizhi.酉: "死", Dizhi.戌: "墓", Dizhi.亥: "绝",
                 Dizhi.子: "胎", Dizhi.丑: "养"},
    Tiangan.丁: {Dizhi.酉: "长生", Dizhi.申: "沐浴", Dizhi.未: "冠带", Dizhi.午: "临官", Dizhi.巳: "帝旺",
                 Dizhi.辰: "衰", Dizhi.卯: "病", Dizhi.寅: "死", Dizhi.丑: "墓", Dizhi.子: "绝",
                 Dizhi.亥: "胎", Dizhi.戌: "养"},
    Tiangan.戊: {Dizhi.寅: "长生", Dizhi.卯: "沐浴", Dizhi.辰: "冠带", Dizhi.巳: "临官", Dizhi.午: "帝旺",
                 Dizhi.未: "衰", Dizhi.申: "病", Dizhi.酉: "死", Dizhi.戌: "墓", Dizhi.亥: "绝",
                 Dizhi.子: "胎", Dizhi.丑: "养"},
    Tiangan.己: {Dizhi.酉: "长生", Dizhi.申: "沐浴", Dizhi.未: "冠带", Dizhi.午: "临官", Dizhi.巳: "帝旺",
                 Dizhi.辰: "衰", Dizhi.卯: "病", Dizhi.寅: "死", Dizhi.丑: "墓", Dizhi.子: "绝",
                 Dizhi.亥: "胎", Dizhi.戌: "养"},
    Tiangan.庚: {Dizhi.巳: "长生", Dizhi.午: "沐浴", Dizhi.未: "冠带", Dizhi.申: "临官", Dizhi.酉: "帝旺",
                 Dizhi.戌: "衰", Dizhi.亥: "病", Dizhi.子: "死", Dizhi.丑: "墓", Dizhi.寅: "绝",
                 Dizhi.卯: "胎", Dizhi.辰: "养"},
    Tiangan.辛: {Dizhi.子: "长生", Dizhi.亥: "沐浴", Dizhi.戌: "冠带", Dizhi.酉: "临官", Dizhi.申: "帝旺",
                 Dizhi.未: "衰", Dizhi.午: "病", Dizhi.巳: "死", Dizhi.辰: "墓", Dizhi.卯: "绝",
                 Dizhi.寅: "胎", Dizhi.丑: "养"},
    Tiangan.壬: {Dizhi.申: "长生", Dizhi.酉: "沐浴", Dizhi.戌: "冠带", Dizhi.亥: "临官", Dizhi.子: "帝旺",
                 Dizhi.丑: "衰", Dizhi.寅: "病", Dizhi.卯: "死", Dizhi.辰: "墓", Dizhi.巳: "绝",
                 Dizhi.午: "胎", Dizhi.未: "养"},
    Tiangan.癸: {Dizhi.卯: "长生", Dizhi.寅: "沐浴", Dizhi.丑: "冠带", Dizhi.子: "临官", Dizhi.亥: "帝旺",
                 Dizhi.戌: "衰", Dizhi.酉: "病", Dizhi.申: "死", Dizhi.未: "墓", Dizhi.午: "绝",
                 Dizhi.巳: "胎", Dizhi.辰: "养"},
}

# ═══════════════════════════════════════════════════════════════
# 神煞: 天乙贵人 — 以日干/年干查
# ═══════════════════════════════════════════════════════════════

# 口诀: 甲戊庚牛羊, 乙己鼠猴乡, 丙丁猪鸡位, 壬癸兔蛇藏, 辛逢马虎
TIANYI_GUIREN: dict[str, dict[Tiangan, tuple[Dizhi, Dizhi]]] = {
    "甲戊庚": {
        Tiangan.甲: (Dizhi.丑, Dizhi.未),
        Tiangan.戊: (Dizhi.丑, Dizhi.未),
        Tiangan.庚: (Dizhi.丑, Dizhi.未),
    },
    "乙己": {
        Tiangan.乙: (Dizhi.子, Dizhi.申),
        Tiangan.己: (Dizhi.子, Dizhi.申),
    },
    "丙丁": {
        Tiangan.丙: (Dizhi.亥, Dizhi.酉),
        Tiangan.丁: (Dizhi.亥, Dizhi.酉),
    },
    "壬癸": {
        Tiangan.壬: (Dizhi.卯, Dizhi.巳),
        Tiangan.癸: (Dizhi.卯, Dizhi.巳),
    },
    "辛": {
        Tiangan.辛: (Dizhi.午, Dizhi.寅),
    },
}

# 展平版
_TIANYI_FLAT: dict[Tiangan, tuple[Dizhi, Dizhi]] = {}
for _group in TIANYI_GUIREN.values():
    _TIANYI_FLAT.update(_group)


def tianyi_guiren_by_stem(stem: Tiangan) -> tuple[Dizhi, Dizhi]:
    return _TIANYI_FLAT[stem]

# ═══════════════════════════════════════════════════════════════
# 神煞: 文昌贵人 — 以日干查
# ═══════════════════════════════════════════════════════════════

WENCHANG: dict[Tiangan, Dizhi] = {
    Tiangan.甲: Dizhi.巳, Tiangan.乙: Dizhi.午,
    Tiangan.丙: Dizhi.申, Tiangan.丁: Dizhi.酉,
    Tiangan.戊: Dizhi.申, Tiangan.己: Dizhi.酉,
    Tiangan.庚: Dizhi.亥, Tiangan.辛: Dizhi.子,
    Tiangan.壬: Dizhi.寅, Tiangan.癸: Dizhi.卯,
}

# ═══════════════════════════════════════════════════════════════
# 神煞: 红鸾 / 天喜 — 以年支（或日支）查
# ═══════════════════════════════════════════════════════════════

HONGLUAN: dict[Dizhi, Dizhi] = {
    Dizhi.子: Dizhi.卯, Dizhi.丑: Dizhi.寅, Dizhi.寅: Dizhi.丑, Dizhi.卯: Dizhi.子,
    Dizhi.辰: Dizhi.亥, Dizhi.巳: Dizhi.戌, Dizhi.午: Dizhi.酉, Dizhi.未: Dizhi.申,
    Dizhi.申: Dizhi.未, Dizhi.酉: Dizhi.午, Dizhi.戌: Dizhi.巳, Dizhi.亥: Dizhi.辰,
}

TIANXI: dict[Dizhi, Dizhi] = {
    Dizhi.子: Dizhi.酉, Dizhi.丑: Dizhi.申, Dizhi.寅: Dizhi.未, Dizhi.卯: Dizhi.午,
    Dizhi.辰: Dizhi.巳, Dizhi.巳: Dizhi.辰, Dizhi.午: Dizhi.卯, Dizhi.未: Dizhi.寅,
    Dizhi.申: Dizhi.丑, Dizhi.酉: Dizhi.子, Dizhi.戌: Dizhi.亥, Dizhi.亥: Dizhi.戌,
}

# ═══════════════════════════════════════════════════════════════
# 神煞: 驿马 / 桃花 / 华盖 — 以年支或日支查（三合局归类）
# ═══════════════════════════════════════════════════════════════

# 三合局 → 驿马/桃花/华盖地支
_YIMA_SANHE = {
    frozenset({Dizhi.申, Dizhi.子, Dizhi.辰}): Dizhi.寅,
    frozenset({Dizhi.寅, Dizhi.午, Dizhi.戌}): Dizhi.申,
    frozenset({Dizhi.巳, Dizhi.酉, Dizhi.丑}): Dizhi.亥,
    frozenset({Dizhi.亥, Dizhi.卯, Dizhi.未}): Dizhi.巳,
}

_TAOHUA_SANHE = {
    frozenset({Dizhi.申, Dizhi.子, Dizhi.辰}): Dizhi.酉,
    frozenset({Dizhi.寅, Dizhi.午, Dizhi.戌}): Dizhi.卯,
    frozenset({Dizhi.巳, Dizhi.酉, Dizhi.丑}): Dizhi.午,
    frozenset({Dizhi.亥, Dizhi.卯, Dizhi.未}): Dizhi.子,
}

_HUAGAI_SANHE = {
    frozenset({Dizhi.申, Dizhi.子, Dizhi.辰}): Dizhi.辰,
    frozenset({Dizhi.寅, Dizhi.午, Dizhi.戌}): Dizhi.戌,
    frozenset({Dizhi.巳, Dizhi.酉, Dizhi.丑}): Dizhi.丑,
    frozenset({Dizhi.亥, Dizhi.卯, Dizhi.未}): Dizhi.未,
}


def _build_branch_shensha_map(ss_map: dict[frozenset[Dizhi], Dizhi]) -> dict[Dizhi, Dizhi]:
    """将三合局→神煞 转换为 单支→神煞"""
    result: dict[Dizhi, Dizhi] = {}
    for trio, target in ss_map.items():
        for dz in trio:
            result[dz] = target
    return result


YIMA: dict[Dizhi, Dizhi] = _build_branch_shensha_map(_YIMA_SANHE)
TAOHUA: dict[Dizhi, Dizhi] = _build_branch_shensha_map(_TAOHUA_SANHE)
HUAGAI: dict[Dizhi, Dizhi] = _build_branch_shensha_map(_HUAGAI_SANHE)

# ═══════════════════════════════════════════════════════════════
# 日柱公式月常数
# ═══════════════════════════════════════════════════════════════

MONTH_CONSTANTS: dict[int, int] = {
    1: 0, 2: 31, 3: 59, 4: 30, 5: 0, 6: 31,
    7: 1, 8: 31, 9: 2, 10: 32, 11: 3, 12: 33,
}

# ═══════════════════════════════════════════════════════════════
# 月支映射: 公历月 → 月地支 (按节气大约对应)
# ═══════════════════════════════════════════════════════════════

MONTH_TO_DIZHI_APPROX: dict[int, Dizhi] = {
    1: Dizhi.丑, 2: Dizhi.寅, 3: Dizhi.卯, 4: Dizhi.辰,
    5: Dizhi.巳, 6: Dizhi.午, 7: Dizhi.未, 8: Dizhi.申,
    9: Dizhi.酉, 10: Dizhi.戌, 11: Dizhi.亥, 12: Dizhi.子,
}

# 月支取格映射: (地支, 藏干, 日主) → 格局名
# 注意: 建禄格和羊刃格需要日主参与判断，在 pattern.py 中处理
_MONTH_PATTERN_BASE: dict[Dizhi, dict[Tiangan, str]] = {
    Dizhi.子: {Tiangan.癸: "偏印格"},
    Dizhi.丑: {Tiangan.己: "偏印格", Tiangan.癸: "偏印格", Tiangan.辛: "偏印格"},
    Dizhi.寅: {Tiangan.甲: "建禄格", Tiangan.丙: "食神格", Tiangan.戊: "偏财格"},
    Dizhi.卯: {Tiangan.乙: "建禄格"},
    Dizhi.辰: {Tiangan.戊: "偏财格", Tiangan.乙: "劫财格", Tiangan.癸: "伤官格"},
    Dizhi.巳: {Tiangan.丙: "建禄格", Tiangan.庚: "偏财格", Tiangan.戊: "食神格"},
    Dizhi.午: {Tiangan.丁: "建禄格", Tiangan.己: "食神格"},
    Dizhi.未: {Tiangan.己: "偏印格", Tiangan.丁: "偏印格", Tiangan.乙: "偏印格"},
    Dizhi.申: {Tiangan.庚: "偏印格", Tiangan.壬: "比肩格", Tiangan.戊: "偏印格"},
    Dizhi.酉: {Tiangan.辛: "正印格"},
    Dizhi.戌: {Tiangan.戊: "偏财格", Tiangan.辛: "伤官格", Tiangan.丁: "正财格"},
    Dizhi.亥: {Tiangan.壬: "建禄格", Tiangan.甲: "食神格"},
}

# build pattern name via 十神 of the透干 stem: (日干wuxing, 透干wuxing, yinyang match) → pattern
# this is computed dynamically in pattern.py; _MONTH_PATTERN_BASE is a simplified backup


# ═══════════════════════════════════════════════════════════════
# 时辰映射: 小时 → 地支
# ═══════════════════════════════════════════════════════════════

def hour_to_dizhi(hour: int) -> tuple[Dizhi, str | None]:
    """返回 (时辰地支, 子时标记) — 标记: "早子时" | "夜子时" | None"""
    if 23 <= hour or hour < 1:
        return Dizhi.子, "夜子时" if hour >= 23 else "早子时"
    elif 1 <= hour < 3:
        return Dizhi.丑, None
    elif 3 <= hour < 5:
        return Dizhi.寅, None
    elif 5 <= hour < 7:
        return Dizhi.卯, None
    elif 7 <= hour < 9:
        return Dizhi.辰, None
    elif 9 <= hour < 11:
        return Dizhi.巳, None
    elif 11 <= hour < 13:
        return Dizhi.午, None
    elif 13 <= hour < 15:
        return Dizhi.未, None
    elif 15 <= hour < 17:
        return Dizhi.申, None
    elif 17 <= hour < 19:
        return Dizhi.酉, None
    elif 19 <= hour < 21:
        return Dizhi.戌, None
    else:  # 21 <= hour < 23
        return Dizhi.亥, None


# ═══════════════════════════════════════════════════════════════
# 纳音五行 — 60 甲子 → 纳音名称
# ═══════════════════════════════════════════════════════════════

NAYIN: dict[tuple[Tiangan, Dizhi], str] = {
    # 甲子 ~ 癸亥
    (Tiangan.甲, Dizhi.子): "海中金", (Tiangan.乙, Dizhi.丑): "海中金",
    (Tiangan.丙, Dizhi.寅): "炉中火", (Tiangan.丁, Dizhi.卯): "炉中火",
    (Tiangan.戊, Dizhi.辰): "大林木", (Tiangan.己, Dizhi.巳): "大林木",
    (Tiangan.庚, Dizhi.午): "路旁土", (Tiangan.辛, Dizhi.未): "路旁土",
    (Tiangan.壬, Dizhi.申): "剑锋金", (Tiangan.癸, Dizhi.酉): "剑锋金",
    (Tiangan.甲, Dizhi.戌): "山头火", (Tiangan.乙, Dizhi.亥): "山头火",
    (Tiangan.丙, Dizhi.子): "涧下水", (Tiangan.丁, Dizhi.丑): "涧下水",
    (Tiangan.戊, Dizhi.寅): "城头土", (Tiangan.己, Dizhi.卯): "城头土",
    (Tiangan.庚, Dizhi.辰): "白蜡金", (Tiangan.辛, Dizhi.巳): "白蜡金",
    (Tiangan.壬, Dizhi.午): "杨柳木", (Tiangan.癸, Dizhi.未): "杨柳木",
    (Tiangan.甲, Dizhi.申): "泉中水", (Tiangan.乙, Dizhi.酉): "泉中水",
    (Tiangan.丙, Dizhi.戌): "屋上土", (Tiangan.丁, Dizhi.亥): "屋上土",
    (Tiangan.戊, Dizhi.子): "霹雳火", (Tiangan.己, Dizhi.丑): "霹雳火",
    (Tiangan.庚, Dizhi.寅): "松柏木", (Tiangan.辛, Dizhi.卯): "松柏木",
    (Tiangan.壬, Dizhi.辰): "长流水", (Tiangan.癸, Dizhi.巳): "长流水",
    (Tiangan.甲, Dizhi.午): "沙中金", (Tiangan.乙, Dizhi.未): "沙中金",
    (Tiangan.丙, Dizhi.申): "山下火", (Tiangan.丁, Dizhi.酉): "山下火",
    (Tiangan.戊, Dizhi.戌): "平地木", (Tiangan.己, Dizhi.亥): "平地木",
    (Tiangan.庚, Dizhi.子): "壁上土", (Tiangan.辛, Dizhi.丑): "壁上土",
    (Tiangan.壬, Dizhi.寅): "金箔金", (Tiangan.癸, Dizhi.卯): "金箔金",
    (Tiangan.甲, Dizhi.辰): "覆灯火", (Tiangan.乙, Dizhi.巳): "覆灯火",
    (Tiangan.丙, Dizhi.午): "天河水", (Tiangan.丁, Dizhi.未): "天河水",
    (Tiangan.戊, Dizhi.申): "大驿土", (Tiangan.己, Dizhi.酉): "大驿土",
    (Tiangan.庚, Dizhi.戌): "钗钏金", (Tiangan.辛, Dizhi.亥): "钗钏金",
    (Tiangan.壬, Dizhi.子): "桑柘木", (Tiangan.癸, Dizhi.丑): "桑柘木",
    (Tiangan.甲, Dizhi.寅): "大溪水", (Tiangan.乙, Dizhi.卯): "大溪水",
    (Tiangan.丙, Dizhi.辰): "沙中土", (Tiangan.丁, Dizhi.巳): "沙中土",
    (Tiangan.戊, Dizhi.午): "天上火", (Tiangan.己, Dizhi.未): "天上火",
    (Tiangan.庚, Dizhi.申): "石榴木", (Tiangan.辛, Dizhi.酉): "石榴木",
    (Tiangan.壬, Dizhi.戌): "大海水", (Tiangan.癸, Dizhi.亥): "大海水",
}


def get_nayin(stem: Tiangan, branch: Dizhi) -> str:
    """返回干支组合对应的纳音名称"""
    return NAYIN.get((stem, branch), "")


# ═══════════════════════════════════════════════════════════════
# 灾煞 / 丧门 / 吊客 — 以年支查
# 来源: 2026-05-23 WebSearch 验证
# ═══════════════════════════════════════════════════════════════

ZAISHA: dict[Dizhi, Dizhi] = {
    Dizhi.子: Dizhi.午, Dizhi.丑: Dizhi.酉, Dizhi.寅: Dizhi.子, Dizhi.卯: Dizhi.酉,
    Dizhi.辰: Dizhi.午, Dizhi.巳: Dizhi.卯, Dizhi.午: Dizhi.子, Dizhi.未: Dizhi.酉,
    Dizhi.申: Dizhi.午, Dizhi.酉: Dizhi.卯, Dizhi.戌: Dizhi.子, Dizhi.亥: Dizhi.酉,
}

SANGMEN: dict[Dizhi, Dizhi] = {
    Dizhi.子: Dizhi.寅, Dizhi.丑: Dizhi.卯, Dizhi.寅: Dizhi.辰, Dizhi.卯: Dizhi.巳,
    Dizhi.辰: Dizhi.午, Dizhi.巳: Dizhi.未, Dizhi.午: Dizhi.申, Dizhi.未: Dizhi.酉,
    Dizhi.申: Dizhi.戌, Dizhi.酉: Dizhi.亥, Dizhi.戌: Dizhi.子, Dizhi.亥: Dizhi.丑,
}

DIAOKE: dict[Dizhi, Dizhi] = {
    Dizhi.子: Dizhi.戌, Dizhi.丑: Dizhi.亥, Dizhi.寅: Dizhi.子, Dizhi.卯: Dizhi.丑,
    Dizhi.辰: Dizhi.寅, Dizhi.巳: Dizhi.卯, Dizhi.午: Dizhi.辰, Dizhi.未: Dizhi.巳,
    Dizhi.申: Dizhi.午, Dizhi.酉: Dizhi.未, Dizhi.戌: Dizhi.申, Dizhi.亥: Dizhi.酉,
}


# ═══════════════════════════════════════════════════════════════
# 空亡 — 以日柱查（旬空）
# ═══════════════════════════════════════════════════════════════

KONGWANG: dict[int, tuple[Dizhi, Dizhi]] = {
    # 日柱天干序号 → 两个空亡地支
    0: (Dizhi.戌, Dizhi.亥),   # 甲子旬(甲子→癸酉) 空戌亥
    1: (Dizhi.申, Dizhi.酉),   # 甲戌旬 空申酉
    2: (Dizhi.午, Dizhi.未),   # 甲申旬 空午未
    3: (Dizhi.辰, Dizhi.巳),   # 甲午旬 空辰巳
    4: (Dizhi.寅, Dizhi.卯),   # 甲辰旬 空寅卯
    5: (Dizhi.子, Dizhi.丑),   # 甲寅旬 空子丑
    6: (Dizhi.戌, Dizhi.亥),   # 甲子旬
    7: (Dizhi.申, Dizhi.酉),   # 甲戌旬
    8: (Dizhi.午, Dizhi.未),   # 甲申旬
    9: (Dizhi.辰, Dizhi.巳),   # 甲午旬
}


# ═══════════════════════════════════════════════════════════════
# 学堂 — 以日干查
# 来源: 子平法日干查法，2026-05-23 WebSearch 验证
# ═══════════════════════════════════════════════════════════════

XUETANG: dict[Tiangan, Dizhi] = {
    Tiangan.甲: Dizhi.亥, Tiangan.乙: Dizhi.午,
    Tiangan.丙: Dizhi.寅, Tiangan.丁: Dizhi.酉,
    Tiangan.戊: Dizhi.寅, Tiangan.己: Dizhi.酉,
    Tiangan.庚: Dizhi.巳, Tiangan.辛: Dizhi.子,
    Tiangan.壬: Dizhi.申, Tiangan.癸: Dizhi.卯,
}


# ═══════════════════════════════════════════════════════════════
# 孤辰 / 寡宿 — 以年支查（三合局归类）
# ═══════════════════════════════════════════════════════════════

# 孤辰寡宿 — 以三会局为基准（主流查法）
# 来源: 三会局查法，2026-05-23 WebSearch 验证（区别于冷门三合局查法）
# 年支 → (孤辰, 寡宿)
_GUCHEN_GUASU: dict[Dizhi, tuple[Dizhi, Dizhi]] = {
    # 亥子丑（北方水）→ 孤寅 寡戌
    Dizhi.亥: (Dizhi.寅, Dizhi.戌), Dizhi.子: (Dizhi.寅, Dizhi.戌), Dizhi.丑: (Dizhi.寅, Dizhi.戌),
    # 寅卯辰（东方木）→ 孤巳 寡丑
    Dizhi.寅: (Dizhi.巳, Dizhi.丑), Dizhi.卯: (Dizhi.巳, Dizhi.丑), Dizhi.辰: (Dizhi.巳, Dizhi.丑),
    # 巳午未（南方火）→ 孤申 寡辰
    Dizhi.巳: (Dizhi.申, Dizhi.辰), Dizhi.午: (Dizhi.申, Dizhi.辰), Dizhi.未: (Dizhi.申, Dizhi.辰),
    # 申酉戌（西方金）→ 孤亥 寡未
    Dizhi.申: (Dizhi.亥, Dizhi.未), Dizhi.酉: (Dizhi.亥, Dizhi.未), Dizhi.戌: (Dizhi.亥, Dizhi.未),
}

GUCHEN: dict[Dizhi, Dizhi] = {dz: v[0] for dz, v in _GUCHEN_GUASU.items()}
GUASU: dict[Dizhi, Dizhi] = {dz: v[1] for dz, v in _GUCHEN_GUASU.items()}


# ═══════════════════════════════════════════════════════════════
# 太极贵人 — 以日干/年干查
# 来源: 古诀「甲乙子午丙丁卯酉戊己四季庚辛寅亥壬癸巳申」, 2026-05-23 WebSearch 验证
# ═══════════════════════════════════════════════════════════════

TAIJI_GUIREN: dict[Tiangan, tuple[Dizhi, ...]] = {
    Tiangan.甲: (Dizhi.子, Dizhi.午), Tiangan.乙: (Dizhi.子, Dizhi.午),
    Tiangan.丙: (Dizhi.卯, Dizhi.酉), Tiangan.丁: (Dizhi.卯, Dizhi.酉),
    Tiangan.戊: (Dizhi.辰, Dizhi.戌, Dizhi.丑, Dizhi.未),
    Tiangan.己: (Dizhi.辰, Dizhi.戌, Dizhi.丑, Dizhi.未),
    Tiangan.庚: (Dizhi.寅, Dizhi.亥), Tiangan.辛: (Dizhi.寅, Dizhi.亥),
    Tiangan.壬: (Dizhi.巳, Dizhi.申), Tiangan.癸: (Dizhi.巳, Dizhi.申),
}


# ═══════════════════════════════════════════════════════════════
# 福星贵人 — 以日干查
# ═══════════════════════════════════════════════════════════════

# 福星贵人 — 以日干/年干查
# 来源: 渊海子平口诀「甲丙相邀入虎乡…」，2026-05-23 WebSearch 验证
# 甲丙→寅子, 乙癸→卯丑, 戊→申, 己→未, 丁→亥, 庚→午, 辛→巳, 壬→辰
FUXING_GUIREN: dict[Tiangan, tuple[Dizhi, ...]] = {
    Tiangan.甲: (Dizhi.寅, Dizhi.子), Tiangan.丙: (Dizhi.寅, Dizhi.子),
    Tiangan.乙: (Dizhi.卯, Dizhi.丑), Tiangan.癸: (Dizhi.卯, Dizhi.丑),
    Tiangan.戊: (Dizhi.申,), Tiangan.己: (Dizhi.未,),
    Tiangan.丁: (Dizhi.亥,), Tiangan.庚: (Dizhi.午,),
    Tiangan.辛: (Dizhi.巳,), Tiangan.壬: (Dizhi.辰,),
}


# ═══════════════════════════════════════════════════════════════
# 从格检测阈值
# 来源: 《渊海子平》+《子平真诠》特殊格局章节
# 验证: WebSearch 2026-05-26
# ═══════════════════════════════════════════════════════════════

# 从强/从旺格：日主得令+全局≥4个同五行或生扶者（含藏干本气）
CONG_GE_CHECKS: dict[str, dict] = {
    "从旺": {
        "description": "日主极旺，全局同五行或生扶≥4个，无反克之力",
        "condition": "月令得令 + 比劫/印星≥4（天干+地支本气）",
        "favorable": ["比肩", "劫财", "正印", "偏印"],
        "harmful": ["正官", "偏官", "正财", "偏财", "食神", "伤官"],
    },
    "从弱_从财": {
        "description": "全局财星极旺，日主无根无生",
        "condition": "财星透干≥1 + 财星地支≥2 + 无比劫印星帮扶",
        "favorable": ["正财", "偏财", "食神", "伤官"],
        "harmful": ["比肩", "劫财", "正印", "偏印"],
    },
    "从弱_从杀": {
        "description": "全局官杀极旺，日主无根无生",
        "condition": "官杀透干≥1 + 官杀地支≥2 + 无比劫印星帮扶",
        "favorable": ["正官", "偏官", "正财", "偏财"],
        "harmful": ["比肩", "劫财", "正印", "偏印", "食神", "伤官"],
    },
    "从弱_从儿": {
        "description": "全局食伤极旺，日主无根无生",
        "condition": "食伤透干≥1 + 食伤地支≥2 + 无比劫印星帮扶",
        "favorable": ["食神", "伤官", "正财", "偏财"],
        "harmful": ["正印", "偏印", "比肩", "劫财"],
    },
}

# ═══════════════════════════════════════════════════════════════
# 化气格成功条件
# 来源: 《渊海子平》+《滴天髓》化气篇
# 验证: WebSearch 2026-05-26
# ═══════════════════════════════════════════════════════════════

# (日干, 合干) → (化气五行, 月令条件)
# 化气成功的条件：
# 1. 日干与月干/时干/年干有合
# 2. 化气之神在月令当旺（月支为化气五行的临官/帝旺/长生/冠带）
# 3. 地支有合局助化
HUA_QI_CONDITIONS: dict[tuple[str, str], dict] = {
    ("甲", "己"): {"化气": "土", "月令条件": ["辰", "戌", "丑", "未", "巳", "午"], "描述": "甲己合化土"},
    ("己", "甲"): {"化气": "土", "月令条件": ["辰", "戌", "丑", "未", "巳", "午"], "描述": "甲己合化土"},
    ("乙", "庚"): {"化气": "金", "月令条件": ["申", "酉", "辰", "戌", "丑", "未"], "描述": "乙庚合化金"},
    ("庚", "乙"): {"化气": "金", "月令条件": ["申", "酉", "辰", "戌", "丑", "未"], "描述": "乙庚合化金"},
    ("丙", "辛"): {"化气": "水", "月令条件": ["亥", "子", "申", "辰"], "描述": "丙辛合化水"},
    ("辛", "丙"): {"化气": "水", "月令条件": ["亥", "子", "申", "辰"], "描述": "丙辛合化水"},
    ("丁", "壬"): {"化气": "木", "月令条件": ["寅", "卯", "亥", "未"], "描述": "丁壬合化木"},
    ("壬", "丁"): {"化气": "木", "月令条件": ["寅", "卯", "亥", "未"], "描述": "丁壬合化木"},
    ("戊", "癸"): {"化气": "火", "月令条件": ["巳", "午", "寅", "戌"], "描述": "戊癸合化火"},
    ("癸", "戊"): {"化气": "火", "月令条件": ["巳", "午", "寅", "戌"], "描述": "戊癸合化火"},
}
