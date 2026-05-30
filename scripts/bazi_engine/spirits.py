"""神煞检测: 天乙贵人 文昌 红鸾 天喜 驿马 桃花 华盖 羊刃"""

from dataclasses import dataclass, field

from ._constants import (
    _TIANYI_FLAT,
    DIAOKE,
    FUXING_GUIREN,
    GUASU,
    GUCHEN,
    HONGLUAN,
    HUAGAI,
    SANGMEN,
    TAIJI_GUIREN,
    TAOHUA,
    TIANXI,
    WENCHANG,
    XUETANG,
    YIMA,
    ZAISHA,
)
from .enums import TIANGAN_LU, TIANGAN_YANGREN, Dizhi, Tiangan


@dataclass
class SpiritAgent:
    name: str            # 神煞名
    category: str        # "吉神" | "凶神"
    pillar: str          # 所在柱位
    source: str          # 查到的方式
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "pillar": self.pillar,
            "source": self.source,
            "notes": self.notes,
        }


def find_tianyi_guiren(day_stem: Tiangan, year_stem: Tiangan,
                       branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """天乙贵人: 以日干和年干查"""
    results: list[SpiritAgent] = []
    for source_stem, label in [(day_stem, "日干"), (year_stem, "年干")]:
        targets = _TIANYI_FLAT.get(source_stem)
        if targets:
            for b, pillar_label in branches_and_labels:
                if b in targets:
                    results.append(SpiritAgent(
                        name="天乙贵人",
                        category="吉神",
                        pillar=pillar_label,
                        source=f"以{label}{source_stem.value}查",
                    ))
    return results


def find_wenchang(day_stem: Tiangan,
                  branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """文昌贵人: 以日干查"""
    target = WENCHANG.get(day_stem)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="文昌贵人",
                    category="吉神",
                    pillar=pillar_label,
                    source=f"以日干{day_stem.value}查",
                ))
    return results


def find_hongluan(source_branch: Dizhi,
                  branches_and_labels: list[tuple[Dizhi, str]],
                  source_label: str = "年支") -> list[SpiritAgent]:
    """红鸾: 以年支（或日支）查"""
    target = HONGLUAN.get(source_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="红鸾",
                    category="吉神",
                    pillar=pillar_label,
                    source=f"以{source_label}{source_branch.value}查",
                ))
    return results


def find_tianxi(source_branch: Dizhi,
                branches_and_labels: list[tuple[Dizhi, str]],
                source_label: str = "年支") -> list[SpiritAgent]:
    """天喜: 红鸾对冲位"""
    target = TIANXI.get(source_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="天喜",
                    category="吉神",
                    pillar=pillar_label,
                    source=f"以{source_label}{source_branch.value}查（红鸾对冲）",
                ))
    return results


def find_yima(source_branch: Dizhi,
              branches_and_labels: list[tuple[Dizhi, str]],
              source_label: str = "年支") -> list[SpiritAgent]:
    """驿马: 以年支或日支查"""
    target = YIMA.get(source_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="驿马",
                    category="吉神",
                    pillar=pillar_label,
                    source=f"以{source_label}{source_branch.value}查",
                ))
    return results


def find_taohua(source_branch: Dizhi,
                branches_and_labels: list[tuple[Dizhi, str]],
                source_label: str = "年支") -> list[SpiritAgent]:
    """桃花（咸池）: 以年支或日支查"""
    target = TAOHUA.get(source_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="桃花",
                    category="吉神",
                    pillar=pillar_label,
                    source=f"以{source_label}{source_branch.value}查",
                ))
    return results


def find_huagai(source_branch: Dizhi,
                branches_and_labels: list[tuple[Dizhi, str]],
                source_label: str = "年支") -> list[SpiritAgent]:
    """华盖"""
    target = HUAGAI.get(source_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="华盖",
                    category="吉神",
                    pillar=pillar_label,
                    source=f"以{source_label}{source_branch.value}查",
                ))
    return results


def find_yangren(day_stem: Tiangan,
                 branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """羊刃: 以日干查"""
    target = TIANGAN_YANGREN.get(day_stem)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="羊刃",
                    category="凶神",
                    pillar=pillar_label,
                    source=f"以日干{day_stem.value}查",
                ))
    return results


def find_lu(day_stem: Tiangan,
            branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """天干禄地（临官）"""
    target = TIANGAN_LU.get(day_stem)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="禄",
                    category="吉神",
                    pillar=pillar_label,
                    source=f"以日干{day_stem.value}查",
                ))
    return results


def find_kongwang(day_stem: Tiangan, day_branch: Dizhi,
                  branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """空亡 — 以日柱查旬空

    旬起始地支 = (日支index - 日干index + 12) % 12
    空亡地支 = (旬起始 + 10) % 12, (旬起始 + 11) % 12
    """
    from .enums import dizhi_by_index
    results: list[SpiritAgent] = []
    xun_start = (day_branch.index - day_stem.index) % 12
    kw1 = dizhi_by_index((xun_start + 10) % 12)
    kw2 = dizhi_by_index((xun_start + 11) % 12)
    targets = (kw1, kw2)
    for b, pillar_label in branches_and_labels:
        if b in targets:
            results.append(SpiritAgent(
                name="空亡", category="凶神", pillar=pillar_label,
                source=f"以日柱{day_stem.value}{day_branch.value}查",
            ))
    return results


def find_xuetang(day_stem: Tiangan,
                 branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """学堂 — 以日干查"""
    target = XUETANG.get(day_stem)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="学堂", category="吉神", pillar=pillar_label,
                    source=f"以日干{day_stem.value}查",
                ))
    return results


def find_guchen_guasu(source_branch: Dizhi,
                      branches_and_labels: list[tuple[Dizhi, str]],
                      source_label: str = "年支") -> list[SpiritAgent]:
    """孤辰 + 寡宿"""
    results: list[SpiritAgent] = []
    gc = GUCHEN.get(source_branch)
    gs = GUASU.get(source_branch)
    for b, pillar_label in branches_and_labels:
        if b == gc:
            results.append(SpiritAgent(
                name="孤辰", category="凶神", pillar=pillar_label,
                source=f"以{source_label}{source_branch.value}查",
            ))
        if b == gs:
            results.append(SpiritAgent(
                name="寡宿", category="凶神", pillar=pillar_label,
                source=f"以{source_label}{source_branch.value}查",
            ))
    return results


def find_taiji_guiren(day_stem: Tiangan, year_stem: Tiangan,
                      branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """太极贵人 — 以日干/年干查"""
    results: list[SpiritAgent] = []
    for source_stem, label in [(day_stem, "日干"), (year_stem, "年干")]:
        targets = TAIJI_GUIREN.get(source_stem, ())
        for b, pillar_label in branches_and_labels:
            if b in targets:
                results.append(SpiritAgent(
                    name="太极贵人", category="吉神", pillar=pillar_label,
                    source=f"以{label}{source_stem.value}查",
                ))
    return results


def find_fuxing_guiren(day_stem: Tiangan,
                       branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """福星贵人 — 以日干查（可命中多个）"""
    targets = FUXING_GUIREN.get(day_stem, ())
    results: list[SpiritAgent] = []
    for b, pillar_label in branches_and_labels:
        if b in targets:
            results.append(SpiritAgent(
                name="福星贵人", category="吉神", pillar=pillar_label,
                source=f"以日干{day_stem.value}查",
            ))
    return results


def find_zaisha(year_branch: Dizhi,
                branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """灾煞（白虎煞）— 冲三合局中神"""
    target = ZAISHA.get(year_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="灾煞", category="凶神", pillar=pillar_label,
                    source=f"以年支{year_branch.value}查",
                ))
    return results


def find_sangmen(year_branch: Dizhi,
                 branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """丧门 — 年支顺数两位"""
    target = SANGMEN.get(year_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="丧门", category="凶神", pillar=pillar_label,
                    source=f"以年支{year_branch.value}查",
                ))
    return results


def find_diaoke(year_branch: Dizhi,
                branches_and_labels: list[tuple[Dizhi, str]]) -> list[SpiritAgent]:
    """吊客 — 年支逆数两位"""
    target = DIAOKE.get(year_branch)
    results: list[SpiritAgent] = []
    if target:
        for b, pillar_label in branches_and_labels:
            if b == target:
                results.append(SpiritAgent(
                    name="吊客", category="凶神", pillar=pillar_label,
                    source=f"以年支{year_branch.value}查",
                ))
    return results


def find_all_spirits(
    day_stem: Tiangan,
    year_stem: Tiangan,
    year_branch: Dizhi,
    day_branch: Dizhi,
    branches_and_labels: list[tuple[Dizhi, str]],
) -> list[SpiritAgent]:
    """一站式神煞检测（v0.6.1: 扩展至 15 种）

    branches_and_labels: [(地支, 柱位标签), ...] 四柱+流年+大运等
    """
    results: list[SpiritAgent] = []
    results.extend(find_tianyi_guiren(day_stem, year_stem, branches_and_labels))
    results.extend(find_wenchang(day_stem, branches_and_labels))
    results.extend(find_xuetang(day_stem, branches_and_labels))
    results.extend(find_taiji_guiren(day_stem, year_stem, branches_and_labels))
    results.extend(find_fuxing_guiren(day_stem, branches_and_labels))
    results.extend(find_hongluan(year_branch, branches_and_labels))
    results.extend(find_tianxi(year_branch, branches_and_labels))
    results.extend(find_yima(year_branch, branches_and_labels))
    results.extend(find_yima(day_branch, branches_and_labels, source_label="日支"))
    results.extend(find_taohua(year_branch, branches_and_labels))
    results.extend(find_taohua(day_branch, branches_and_labels, source_label="日支"))
    results.extend(find_huagai(year_branch, branches_and_labels))
    results.extend(find_guchen_guasu(year_branch, branches_and_labels))
    results.extend(find_guchen_guasu(day_branch, branches_and_labels, source_label="日支"))
    results.extend(find_yangren(day_stem, branches_and_labels))
    results.extend(find_lu(day_stem, branches_and_labels))
    results.extend(find_kongwang(day_stem, day_branch, branches_and_labels))
    results.extend(find_zaisha(year_branch, branches_and_labels))
    results.extend(find_sangmen(year_branch, branches_and_labels))
    results.extend(find_diaoke(year_branch, branches_and_labels))
    # 去重
    seen = set()
    unique: list[SpiritAgent] = []
    for s in results:
        key = (s.name, s.pillar)
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


# ═══════════════════════════════════════════════════════════════
# 神煞相互作用合并
# ═══════════════════════════════════════════════════════════════

# 神煞权重（用于总分评估）
SPIRIT_WEIGHTS: dict[str, int] = {
    "天乙贵人": 3, "文昌": 2, "红鸾": 2, "天喜": 2, "驿马": 1,
    "桃花": 1, "华盖": 1, "学堂": 2, "太极贵人": 2, "福星贵人": 2,
    "禄": 2, "羊刃": -2, "寡宿": -1, "孤辰": -1, "空亡": -2,
    "灾煞": -2, "丧门": -2, "吊客": -1,
}

# 同柱神煞交互规则
_SPIRIT_INTERACTIONS: dict[tuple, str] = {
    ("天乙贵人", "羊刃"): "贵人有威权——贵人带锋芒，助人时也有个性",
    ("天乙贵人", "空亡"): "贵人力减——有贵人但关键时刻可能缺席",
    ("天乙贵人", "桃花"): "贵人带桃花——帮助者可能带有感情色彩",
    ("红鸾", "寡宿"): "婚恋与独处矛盾——想恋爱又享受单身",
    ("华盖", "天乙贵人"): "贵人有慧眼——赏识你才华的贵人是真贵人",
    ("文昌", "驿马"): "学业在外地——适合异地求学或留学",
    ("禄", "空亡"): "收入不稳——稳定收入中可能有缺口或波动",
    ("福星贵人", "灾煞"): "福能挡灾——福气可缓解凶险",
    ("驿马", "桃花"): "异地情缘——感情可能与远方或旅行有关",
}


def merge_spirit_interactions(spirits: list[SpiritAgent]) -> list[dict]:
    """检测同柱神煞的相互作用，返回合并解读列表。

    Returns:
        [{"pillar": "年柱", "spirits": ["天乙贵人","羊刃"], "interaction": "贵人有威权"}, ...]
    """
    # 按柱位分组
    pillar_map: dict[str, list[SpiritAgent]] = {}
    for sp in spirits:
        pillar_map.setdefault(sp.pillar, []).append(sp)

    merged = []
    for pillar, sp_list in pillar_map.items():
        names = [sp.name for sp in sp_list]
        for (sa, sb), interp in _SPIRIT_INTERACTIONS.items():
            if sa in names and sb in names:
                merged.append({
                    "pillar": pillar,
                    "spirits": [sa, sb],
                    "interaction": interp,
                })

    return merged


def compute_spirit_score(spirits: list[SpiritAgent]) -> dict:
    """计算神煞总权重分。

    Returns:
        {"total": 5, "favorable": 8, "unfavorable": -3,
         "summary": "神煞总体偏吉，贵人运旺"}
    """
    total = 0
    fav = 0
    unfav = 0
    for sp in spirits:
        w = SPIRIT_WEIGHTS.get(sp.name, 0)
        total += w
        if w > 0:
            fav += w
        else:
            unfav += w

    if total >= 8:
        summary = "神煞总体大吉，贵人运极旺"
    elif total >= 3:
        summary = "神煞总体偏吉，有贵人相助"
    elif total >= 0:
        summary = "神煞吉凶参半，好坏互现"
    elif total >= -3:
        summary = "神煞偏凶，需后天努力化解"
    else:
        summary = "神煞不吉，多注意人际关系和健康"

    return {"total": total, "favorable": fav, "unfavorable": unfav, "summary": summary}
