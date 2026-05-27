"""十二长生参断 — 日主在四柱/大运/流年地支的十二长生状态分析

规则来源: advanced-techniques.md §六 十二长生实战应用
验证: WebSearch 2026-05-26
"""

from dataclasses import dataclass, field
from .enums import Tiangan, Dizhi
from ._constants import SHIER_CHANGSHENG, DIZHI_SANHE, DIZHI_LIUHE


@dataclass
class ChangshengState:
    subject: str             # "日主" | "大运" | "流年"
    stem: Tiangan
    branch: Dizhi
    state: str               # "长生" | "沐浴" | ... | "养"
    pillar_label: str        # "年柱" | "月柱" | "日柱" | "时柱" | "大运" | "流年"
    year: int | None = None  # 流年专用
    interpretation: str = ""
    special_note: str = ""   # "绝处逢生" | "禄地（能量巅峰）" | etc.

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "stem": self.stem.value,
            "branch": self.branch.value,
            "state": self.state,
            "pillar_label": self.pillar_label,
            "year": self.year,
            "interpretation": self.interpretation,
            "special_note": self.special_note,
        }


# 十二长生状态解读
_STATE_INTERPRETATIONS: dict[str, str] = {
    "长生": "新生力量，发展起步，宜学习、开拓",
    "沐浴": "桃花沐浴，情欲萌动，需防烂桃花",
    "冠带": "成长上升期，形象提升，社交活跃",
    "临官": "禄地，能量饱满，事业有成，自信果断",
    "帝旺": "能量巅峰，物极必反，盛极而衰需警惕",
    "衰": "气势转弱，宜守不宜攻，低调行事",
    "病": "能量消耗，需休整调理，关注健康",
    "死": "能量低迷，消极被动期，耐心等待",
    "墓": "入库封存。旺者为库（资源可开发），衰者为墓（被埋没）。需冲/刑打开",
    "绝": "能量见底，旧事物终结，等待新生。绝处逢生则大吉",
    "胎": "孕育新机，暗中筹备，不宜冒进",
    "养": "滋养成长，蓄势待发，宜积累",
}

# 能量等级
_STATE_ENERGY: dict[str, int] = {
    "长生": 7, "沐浴": 5, "冠带": 6, "临官": 9, "帝旺": 10,
    "衰": 4, "病": 3, "死": 2, "墓": 3, "绝": 1, "胎": 4, "养": 5,
}


def get_state_interpretation(state: str, branch: Dizhi, day_master: Tiangan) -> str:
    """生成结合地支上下文的解读"""
    base = _STATE_INTERPRETATIONS.get(state, "")
    energy = _STATE_ENERGY.get(state, 5)

    # 特殊标注
    special = ""
    if state == "临官":
        # 禄地检查
        from .enums import TIANGAN_LU
        lu = TIANGAN_LU.get(day_master)
        if branch == lu:
            special = "【禄神到位】日主归禄，能量自我实现的高峰，自信果断"
    elif state == "帝旺":
        special = "【阳刃】能量顶峰亦最危险，物极必反，需防冲动"
    elif state == "墓":
        special = "【墓库】辰戌丑未，能量封存。旺为库（待开发资源），衰为墓（被埋没），需刑冲激发"
    elif state == "绝":
        special = "【绝地】旧事物终结，等待新生。需看有无合局解救（绝处逢生）"

    if special:
        return f"{base}。{special}"
    return base


def compute_changsheng_for_pillars(day_master: Tiangan,
                                    pillars: list[tuple[Dizhi, str]]) -> list[ChangshengState]:
    """计算日主在四柱地支的十二长生状态"""
    table = SHIER_CHANGSHENG.get(day_master)
    if table is None:
        return []

    results: list[ChangshengState] = []
    for branch, label in pillars:
        state = table.get(branch)
        if state:
            results.append(ChangshengState(
                subject="日主",
                stem=day_master,
                branch=branch,
                state=state,
                pillar_label=label,
                interpretation=get_state_interpretation(state, branch, day_master),
            ))
    return results


def compute_changsheng_for_dayun(day_master: Tiangan,
                                  luck_pillars: list[tuple[Tiangan, Dizhi]]) -> list[ChangshengState]:
    """计算日主在大运地支的十二长生状态"""
    table = SHIER_CHANGSHENG.get(day_master)
    if table is None:
        return []

    results: list[ChangshengState] = []
    for _, branch in luck_pillars:
        state = table.get(branch)
        if state:
            results.append(ChangshengState(
                subject="大运",
                stem=day_master,
                branch=branch,
                state=state,
                pillar_label="大运",
                interpretation=get_state_interpretation(state, branch, day_master),
            ))
    return results


def compute_changsheng_for_liunian(day_master: Tiangan,
                                    annual_scans) -> list[ChangshengState]:
    """计算日主在流年地支的十二长生状态"""
    table = SHIER_CHANGSHENG.get(day_master)
    if table is None:
        return []

    results: list[ChangshengState] = []
    # annual_scans is list[AnnualScan]
    for scan in annual_scans:
        branch = scan.liunian_branch
        state = table.get(branch)
        if state:
            results.append(ChangshengState(
                subject="流年",
                stem=day_master,
                branch=branch,
                state=state,
                pillar_label="流年",
                year=scan.year,
                interpretation=get_state_interpretation(state, branch, day_master),
            ))
    return results


def _branch_in_any_combo(branch: Dizhi, all_branches: list[Dizhi]) -> bool:
    """检查 branch 是否与 all_branches 中的任一地支形成合局"""
    for other in all_branches:
        if other == branch:
            continue
        pair = frozenset({branch, other})
        if pair in DIZHI_LIUHE:
            return True
        # 三合半合
        for sanhe_set in DIZHI_SANHE:
            if branch in sanhe_set and other in sanhe_set:
                return True
    return False


def detect_jue_chu_feng_sheng(day_master: Tiangan,
                               all_branches: list[Dizhi],
                               all_pillar_labels: list[str]) -> list[ChangshengState]:
    """检测绝处逢生：日主在某柱坐绝，但有其他柱来合/救。

    规则：日干在某个地支处于"绝"地，但该地支与其他地支形成合局，
    则有"绝处逢生"的可能。
    """
    table = SHIER_CHANGSHENG.get(day_master)
    if table is None:
        return []

    results: list[ChangshengState] = []
    for i, branch in enumerate(all_branches):
        state = table.get(branch)
        if state != "绝":
            continue
        # 检查是否有合局解救
        saved = _branch_in_any_combo(branch, all_branches)
        if saved:
            label = all_pillar_labels[i] if i < len(all_pillar_labels) else "?"
            results.append(ChangshengState(
                subject="日主",
                stem=day_master,
                branch=branch,
                state="绝",
                pillar_label=label,
                interpretation=(
                    f"日主临绝地（{branch.value}），但绝支与命局中其他地支成合局——"
                    f"绝处逢生，绝地反击之象。看似山穷水尽，实有转机暗藏。"
                ),
                special_note="绝处逢生",
            ))

    return results


def find_all_changsheng_states(day_master: Tiangan,
                                year_branch: Dizhi, month_branch: Dizhi,
                                day_branch: Dizhi, hour_branch: Dizhi,
                                luck_pillars: list[tuple[Tiangan, Dizhi]],
                                annual_scans) -> list[ChangshengState]:
    """收集器: 计算所有十二长生状态"""
    results: list[ChangshengState] = []

    # 四柱
    pillars = [
        (year_branch, "年柱"), (month_branch, "月柱"),
        (day_branch, "日柱"), (hour_branch, "时柱"),
    ]
    results.extend(compute_changsheng_for_pillars(day_master, pillars))

    # 大运
    results.extend(compute_changsheng_for_dayun(day_master, luck_pillars))

    # 流年
    if annual_scans:
        results.extend(compute_changsheng_for_liunian(day_master, annual_scans))

    # 绝处逢生
    results.extend(detect_jue_chu_feng_sheng(
        day_master,
        [b for b, _ in pillars],
        [l for _, l in pillars],
    ))

    return results
