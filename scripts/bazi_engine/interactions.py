"""合冲刑害检测

v0.8.0: +墓库相冲核爆检测（辰戌/丑未冲 → 土气激增 + 杂气损毁）
"""

from dataclasses import dataclass, field

from .ten_gods import wuxing_ke, wuxing_sheng
from ._constants import (
    DIZHI_BANHE,
    DIZHI_LIUCHONG,
    DIZHI_LIUHE,
    DIZHI_SANHE,
    DIZHI_SANHUI,
    DIZHI_XIANGHAI,
    DIZHI_XIANGXING,
    DIZHI_ZIXING,
    TIANGAN_WUHE,
)
from .enums import Dizhi, Tiangan, Wuxing


@dataclass
class Interaction:
    inter_type: str         # "天干五合" | "地支六合" | "三合" | "半合" | "三会" | "六冲" | "相刑" | "自刑" | "相害"
    participants: tuple     # 参与的天干或地支
    pillar_labels: tuple    # 参与的柱位标签
    result: str = ""        # 化神五行 / "力量减半" / ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.inter_type,
            "participants": [p.value if hasattr(p, 'value') else str(p) for p in self.participants],
            "pillars": list(self.pillar_labels),
            "result": self.result,
            "notes": self.notes,
        }


def find_tiangan_wuhe(stems_and_labels: list[tuple[Tiangan, str]]) -> list[Interaction]:
    """检测天干五合: (甲己合土 等)"""
    results: list[Interaction] = []
    n = len(stems_and_labels)
    for i in range(n):
        for j in range(i + 1, n):
            key = (stems_and_labels[i][0], stems_and_labels[j][0])
            if key in TIANGAN_WUHE:
                results.append(Interaction(
                    inter_type="天干五合",
                    participants=(key[0], key[1]),
                    pillar_labels=(stems_and_labels[i][1], stems_and_labels[j][1]),
                    result=f"化{TIANGAN_WUHE[key].value}",
                ))
    return results


def find_dizhi_liuhe(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测地支六合"""
    results: list[Interaction] = []
    n = len(branches_and_labels)
    for i in range(n):
        for j in range(i + 1, n):
            key = (branches_and_labels[i][0], branches_and_labels[j][0])
            if key in DIZHI_LIUHE:
                results.append(Interaction(
                    inter_type="地支六合",
                    participants=(key[0], key[1]),
                    pillar_labels=(branches_and_labels[i][1], branches_and_labels[j][1]),
                    result=f"化{DIZHI_LIUHE[key].value}",
                ))
    return results


def find_dizhi_sanhe(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测三合局（含半合）"""
    results: list[Interaction] = []
    b_set = {b for b, _ in branches_and_labels}
    all_branches = [b for b, _ in branches_and_labels]
    labels_by_b = {b: lb for b, lb in branches_and_labels}

    for trio_set, wx in DIZHI_SANHE.items():
        trio = list(trio_set)
        match_count = sum(1 for b in trio if b in b_set)
        if match_count == 3:
            results.append(Interaction(
                inter_type="三合",
                participants=tuple(trio),
                pillar_labels=tuple(labels_by_b[b] for b in trio if b in labels_by_b),
                result=f"合{getattr(wx, 'value', str(wx))}",
            ))
        elif match_count == 2:
            # 检查是否为半合（前后半合）
            matched = [b for b in trio if b in b_set]
            pair = frozenset(matched)
            if pair in DIZHI_BANHE:
                results.append(Interaction(
                    inter_type="半合",
                    participants=tuple(matched),
                    pillar_labels=tuple(labels_by_b[b] for b in matched),
                    result=f"合{getattr(wx, 'value', str(wx))}",
                    notes=["半合力量减半"],
                ))
    return results


def find_dizhi_sanhui(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测三会方局"""
    results: list[Interaction] = []
    b_set = {b for b, _ in branches_and_labels}
    labels_by_b = {b: lb for b, lb in branches_and_labels}

    for trio_set, wx in DIZHI_SANHUI.items():
        trio = list(trio_set)
        match_count = sum(1 for b in trio if b in b_set)
        if match_count == 3:
            results.append(Interaction(
                inter_type="三会",
                participants=tuple(trio),
                pillar_labels=tuple(labels_by_b[b] for b in trio),
                result=f"会{getattr(wx, 'value', str(wx))}",
                notes=["三会局力量大于三合局"],
            ))
    return results


def find_liuchong(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测六冲"""
    results: list[Interaction] = []
    n = len(branches_and_labels)
    for i in range(n):
        for j in range(i + 1, n):
            bi, bj = branches_and_labels[i][0], branches_and_labels[j][0]
            if (bi, bj) in DIZHI_LIUCHONG:
                results.append(Interaction(
                    inter_type="六冲",
                    participants=(bi, bj),
                    pillar_labels=(branches_and_labels[i][1], branches_and_labels[j][1]),
                ))
    return results


def find_xiangxing(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测相刑（互刑 + 自刑）"""
    results: list[Interaction] = []
    n = len(branches_and_labels)

    # 互刑
    xt_set = {(a, b) for a, b in DIZHI_XIANGXING}
    for i in range(n):
        for j in range(i + 1, n):
            bi, bj = branches_and_labels[i][0], branches_and_labels[j][0]
            if (bi, bj) in xt_set:
                results.append(Interaction(
                    inter_type="相刑",
                    participants=(bi, bj),
                    pillar_labels=(branches_and_labels[i][1], branches_and_labels[j][1]),
                ))

    # 自刑: 同一地支出现 ≥2 次
    b_counts: dict[Dizhi, list[str]] = {}
    for b, lb in branches_and_labels:
        if b not in b_counts:
            b_counts[b] = []
        b_counts[b].append(lb)
    for b, labels in b_counts.items():
        if b in DIZHI_ZIXING and len(labels) >= 2:
            results.append(Interaction(
                inter_type="自刑",
                participants=(b,),
                pillar_labels=tuple(labels),
            ))

    return results


def find_xianghai(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测相害（相穿）"""
    results: list[Interaction] = []
    n = len(branches_and_labels)
    for i in range(n):
        for j in range(i + 1, n):
            bi, bj = branches_and_labels[i][0], branches_and_labels[j][0]
            if (bi, bj) in DIZHI_XIANGHAI:
                results.append(Interaction(
                    inter_type="相害",
                    participants=(bi, bj),
                    pillar_labels=(branches_and_labels[i][1], branches_and_labels[j][1]),
                ))
    return results


def find_all_dizhi_interactions(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测所有地支关系"""
    results: list[Interaction] = []
    results.extend(find_dizhi_liuhe(branches_and_labels))
    results.extend(find_dizhi_sanhe(branches_and_labels))
    results.extend(find_dizhi_sanhui(branches_and_labels))
    results.extend(find_liuchong(branches_and_labels))
    results.extend(find_xiangxing(branches_and_labels))
    results.extend(find_xianghai(branches_and_labels))
    results.extend(find_muku_chong(branches_and_labels))
    return results


# ═══════════════════════════════════════════════════════════════
# 墓库相冲「核爆」检测（v0.8.0）
# ═══════════════════════════════════════════════════════════════

# 墓库冲配对: 辰戌 / 丑未
_MUKU_CHONG_PAIRS: dict[frozenset[Dizhi], dict] = {
    frozenset({Dizhi.辰, Dizhi.戌}): {
        "name": "辰戌冲",
        "tu_boost": 3,     # 土气指数级放大 (3倍)
        "zaqi_damaged": {  # 杂气损毁明细
            Dizhi.辰: ["乙木", "癸水"],   # 辰藏乙木+癸水被挤出
            Dizhi.戌: ["丁火", "辛金"],   # 戌藏丁火+辛金被损毁
        },
        "note": "辰为湿土(水库)，戌为燥土(火库)，两库相冲→土气暴增+杂气挤出。越冲越旺。",
    },
    frozenset({Dizhi.丑, Dizhi.未}): {
        "name": "丑未冲",
        "tu_boost": 3,
        "zaqi_damaged": {
            Dizhi.丑: ["癸水", "辛金"],   # 丑藏癸水+辛金被挤出
            Dizhi.未: ["丁火", "乙木"],   # 未藏丁火+乙木被损毁
        },
        "note": "丑为寒土(金库)，未为热土(木库)，两库相冲→土气暴增+杂气挤出。越冲越旺。",
    },
}

# 土五行对应的健康/财运影响（杂气受伤的后果）
_ZAQI_DAMAGE_CONSEQUENCES: dict[str, str] = {
    "乙木": "肝胆/筋骨受损",
    "癸水": "肾/泌尿系统受损",
    "丁火": "心血管/眼睛受损",
    "辛金": "肺/呼吸系统受损",
}


@dataclass
class MukuChongResult:
    """墓库相冲分析结果"""
    pair: tuple[Dizhi, Dizhi]
    name: str
    tu_boost: int          # 土气放大倍数
    zaqi_damaged: list[str]  # 被损毁的杂气五行
    health_note: str        # 健康影响
    wealth_note: str        # 财运影响（墓库为财库时冲开=财变）
    note: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pair": [p.value for p in self.pair],
            "tu_boost": self.tu_boost,
            "zaqi_damaged": self.zaqi_damaged,
            "health_note": self.health_note,
            "wealth_note": self.wealth_note,
            "note": self.note,
        }


def find_muku_chong(branches_and_labels: list[tuple[Dizhi, str]]) -> list[Interaction]:
    """检测墓库相冲，标记为六冲的升级版。

    规则: 辰戌冲、丑未冲不是普通冲——土气不散反聚，指数级放大。
    同时对杂气（藏干中的非土五行）产生挤出/损毁效果。
    """
    results: list[Interaction] = []
    n = len(branches_and_labels)
    for i in range(n):
        for j in range(i + 1, n):
            bi, bj = branches_and_labels[i][0], branches_and_labels[j][0]
            pair = frozenset({bi, bj})
            if pair in _MUKU_CHONG_PAIRS:
                info = _MUKU_CHONG_PAIRS[pair]
                results.append(Interaction(
                    inter_type="墓库相冲",
                    participants=(bi, bj),
                    pillar_labels=(branches_and_labels[i][1], branches_and_labels[j][1]),
                    result=f"土气×{info['tu_boost']}+杂气损毁",
                    notes=[info["note"]] + [
                        f"{dz.value}藏{'/'.join(zaqi)}被挤出/损毁"
                        for dz, zaqi in info["zaqi_damaged"].items()
                    ],
                ))
    return results


def analyze_muku_chong(all_branches: list[Dizhi],
                       day_master: Tiangan,
                       caiku_branch: Dizhi | None = None) -> list[MukuChongResult]:
    """分析墓库相冲的完整影响（健康+财运+体质）。

    用于 liunian.py 和健康模块消费。

    Args:
        all_branches: 所有需要检查的地支列表（原局+大运+流年）
        day_master: 日主天干
        caiku_branch: 日主的财库地支（可选，用于财运分析）

    Returns:
        MukuChongResult 列表
    """
    results: list[MukuChongResult] = []
    for i, bi in enumerate(all_branches):
        for j, bj in enumerate(all_branches):
            if i >= j:
                continue
            pair = frozenset({bi, bj})
            if pair not in _MUKU_CHONG_PAIRS:
                continue

            info = _MUKU_CHONG_PAIRS[pair]
            # 收集被损杂气五行
            damaged_wx: set[str] = set()
            health_notes: list[str] = []
            for dz, zaqi_list in info["zaqi_damaged"].items():
                for zaqi in zaqi_list:
                    damaged_wx.add(zaqi)
                    cons = _ZAQI_DAMAGE_CONSEQUENCES.get(zaqi, "")
                    if cons:
                        health_notes.append(f"{dz.value}藏{zaqi}被挤出→{cons}")

            # 财运分析：墓库冲是否涉及财库
            wealth_note = ""
            if caiku_branch and caiku_branch in pair:
                wealth_note = (
                    f"墓库相冲涉及财库{caiku_branch.value}→"
                    f"财库被冲开，财运重大变动。"
                    f"喜土则暴富，忌土则大破。"
                )
            elif caiku_branch:
                wealth_note = (
                    f"墓库相冲虽不直冲财库，但土气暴增{info['tu_boost']}倍，"
                    f"全局五行失衡→间接影响财运分布"
                )

            results.append(MukuChongResult(
                pair=(bi, bj),
                name=info["name"],
                tu_boost=info["tu_boost"],
                zaqi_damaged=list(damaged_wx),
                health_note="; ".join(health_notes) if health_notes else "土气暴增，脾胃负担加重",
                wealth_note=wealth_note,
                note=info["note"],
            ))

    return results


# ═══════════════════════════════════════════════════════════════
# 贪生忘克机制（v0.8.0: P7—天干相邻路径化解）
# ═══════════════════════════════════════════════════════════════

@dataclass
class GreedyGeneration:
    """贪生忘克结果：连环相生化解了原本的克制关系"""
    path: tuple[str, str, str]  # (A, B, C): A→生→B→生→C
    cancelled_ke: tuple[str, str]  # (A, C): A 原本克 C，被 B 化解
    bridge: str                    # B 的五行 — 通关之神
    note: str


def detect_tansheng_wangke(stems_and_labels: list[tuple[Tiangan, str]],
                           day_master: Tiangan) -> list[GreedyGeneration]:
    """检测贪生忘克：天干相邻三柱形成连环相生，化解克制。

    规则: A, B, C 为相邻天干（年→月→日→时），
    当 A→生→B→生→C，且 A 五行克 C 五行时，
    A 不再克 C（B 通关），称为"贪生忘克"。

    经典用例:
    - 杀印相生: 戊(土杀)→辛(金印)→壬(水日) → 土不克水
    - 财官印流通: 丙(火财)→戊(土官)→庚(金日) → 火不克金
    """
    results: list[GreedyGeneration] = []

    _SHENG = {
        Wuxing.木: Wuxing.火, Wuxing.火: Wuxing.土,
        Wuxing.土: Wuxing.金, Wuxing.金: Wuxing.水, Wuxing.水: Wuxing.木,
    }
    _KE = {
        Wuxing.木: Wuxing.土, Wuxing.土: Wuxing.水,
        Wuxing.水: Wuxing.火, Wuxing.火: Wuxing.金, Wuxing.金: Wuxing.木,
    }

    n = len(stems_and_labels)
    for i in range(n - 2):
        a_stem, a_label = stems_and_labels[i]
        b_stem, b_label = stems_and_labels[i + 1]
        c_stem, c_label = stems_and_labels[i + 2]

        a_wx = a_stem.wuxing
        b_wx = b_stem.wuxing
        c_wx = c_stem.wuxing

        # 检查 A→生→B 且 B→生→C
        a_sheng_b = _SHENG.get(a_wx) == b_wx
        b_sheng_c = _SHENG.get(b_wx) == c_wx

        if not (a_sheng_b and b_sheng_c):
            continue

        # 检查 A 原本克 C
        a_ke_c = wuxing_ke(a_wx) == c_wx
        if not a_ke_c:
            continue

        # 贪生忘克！
        bridge_wx = b_wx.value

        dm_involved = c_stem == day_master or a_stem == day_master
        dm_note = ""
        if dm_involved and c_stem == day_master:
            dm_note = f"【通关保护日主】中间{b_stem.value}({bridge_wx})化解了{a_stem.value}对日主的克制"
        elif dm_involved:
            dm_note = f"【日主出力通关】日主{a_stem.value}通过{b_stem.value}({bridge_wx})化解了对{c_stem.value}的克制"

        results.append(GreedyGeneration(
            path=(a_stem.value, b_stem.value, c_stem.value),
            cancelled_ke=(a_stem.value, c_stem.value),
            bridge=bridge_wx,
            note=f"{a_label}→生→{b_label}→生→{c_label}: "
                 f"{a_stem.value}({a_wx.value})本克{c_stem.value}({c_wx.value})，"
                 f"因{b_stem.value}({bridge_wx})通关而化解。{'★' + dm_note if dm_involved else ''}",
        ))

    return results


def detect_jiagong(gans: list, zhis: list) -> list[dict]:
    """检测夹/拱（v0.16: 盲派暗拱关系）

    天干相同时，地支间隔2位的两柱 → 中间地支为"拱"
    如: 甲寅 甲辰 → 拱卯（寅辰之间为卯）
    """
    results = []
    labels = ["年柱", "月柱", "日柱", "时柱"]
    dz_list = list(Dizhi)

    for i in range(3):
        for j in range(i + 1, 4):
            if gans[i] != gans[j]:
                continue
            idx1 = dz_list.index(zhis[i])
            idx2 = dz_list.index(zhis[j])
            diff = abs(idx2 - idx1)
            if diff == 2 or diff == 10:
                if diff == 2:
                    mid_idx = (idx1 + idx2) // 2
                else:
                    mid_idx = (idx1 + idx2 + 12) // 2 % 12
                mid_dz = dz_list[mid_idx % 12]
                if mid_dz not in zhis:
                    results.append({
                        "type": "拱",
                        "pillars": [labels[i], labels[j]],
                        "gan": gans[i].value,
                        "zhi": mid_dz.value,
                        "note": f"{labels[i]}{gans[i].value}{zhis[i].value}与{labels[j]}{gans[j].value}{zhis[j].value}暗拱{mid_dz.value}"
                    })
    return results
