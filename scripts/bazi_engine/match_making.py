"""合婚分析 — 双人八字配对评分

调用方式:
    from .match_making import match_score
    score, report = match_score(chart1, chart2)
"""
from typing import TYPE_CHECKING

from .enums import Tiangan, Dizhi, Shishen
from ._constants import (
    TIANGAN_WUHE, DIZHI_LIUHE, DIZHI_LIUCHONG, DIZHI_XIANGHAI,
    DIZHI_SANHE, DIZHI_XIANGXING,
)

if TYPE_CHECKING:
    from .chart import BaziChart


def match_score(chart1: "BaziChart", chart2: "BaziChart") -> tuple[int, str]:
    """双人合婚评分。

    评分维度（满分 100）：
    - 天干五合（40 分）：日干是否五合 / 其他柱五合加分
    - 地支关系（30 分）：日支六合 +3 分，三合 +2 分，冲 -2 分，害 -1 分
    - 日柱关系（30 分）：天合地合 30 分，天合地冲 5 分，其他 0~15 分
    - bonus/penalty：配偶星匹配、神煞呼应

    Returns:
        (score, report_text)
    """
    score = 0
    parts = []

    # ── 天干五合 ──
    tg_score = 0
    tg_matches = []
    for pillar1 in (chart1.year, chart1.month, chart1.day, chart1.hour):
        for pillar2 in (chart2.year, chart2.month, chart2.day, chart2.hour):
            pair = (pillar1.stem, pillar2.stem)
            if pair in TIANGAN_WUHE or (pair[1], pair[0]) in TIANGAN_WUHE:
                is_day = (pillar1.stem == chart1.day.stem) and (pillar2.stem == chart2.day.stem)
                if is_day:
                    tg_score += 15
                    tg_matches.append(f"日干五合({pillar1.stem.value}{pillar2.stem.value})")
                else:
                    tg_score += 8
                    tg_matches.append(f"{pillar1.stem.value}{pillar2.stem.value}五合")
    score += min(tg_score, 40)
    if tg_matches:
        parts.append(f"天干五合: {'; '.join(tg_matches)}")
    else:
        parts.append("天干: 无五合")

    # ── 地支关系 ──
    dz_score = 0
    dz_notes = []
    for pillar1 in (chart1.year, chart1.month, chart1.day, chart1.hour):
        for pillar2 in (chart2.year, chart2.month, chart2.day, chart2.hour):
            pair = (pillar1.branch, pillar2.branch)
            is_day = (pillar1.branch == chart1.day.branch) and (pillar2.branch == chart2.day.branch)
            if pair in DIZHI_LIUHE:
                pts = 10 if is_day else 5
                dz_score += pts
                dz_notes.append(f"{'日支' if is_day else ''}{pillar1.branch.value}{pillar2.branch.value}六合 +{pts}")
            elif any(pair[0] in s and pair[1] in s for s in DIZHI_SANHE if isinstance(s, tuple)):
                pts = 6 if is_day else 3
                dz_score += pts
                dz_notes.append(f"{'日支' if is_day else ''}{pillar1.branch.value}{pillar2.branch.value}三合 +{pts}")
            elif pair in DIZHI_LIUCHONG:
                pts = -8 if is_day else -3
                dz_score += pts
                dz_notes.append(f"{'日支' if is_day else ''}{pillar1.branch.value}{pillar2.branch.value}六冲 {pts}")
            elif pair in DIZHI_XIANGHAI:
                pts = -4 if is_day else -1
                dz_score += pts
                dz_notes.append(f"{'日支' if is_day else ''}{pillar1.branch.value}{pillar2.branch.value}相害 {pts}")
    dz_score = max(-15, min(dz_score, 30))
    score += dz_score
    if dz_notes:
        parts.append(f"地支: {'; '.join(dz_notes)}")

    # ── 日柱天合地合 ──
    day_pair_tg = (chart1.day.stem, chart2.day.stem)
    day_pair_dz = (chart1.day.branch, chart2.day.branch)
    tg_he = day_pair_tg in TIANGAN_WUHE or (day_pair_tg[1], day_pair_tg[0]) in TIANGAN_WUHE
    dz_he = day_pair_dz in DIZHI_LIUHE
    dz_chong = day_pair_dz in DIZHI_LIUCHONG

    if tg_he and dz_he:
        score += 30
        parts.insert(0, "日柱天合地合——最佳婚配组合")
    elif tg_he and dz_chong:
        score += 5
        parts.insert(0, "日柱天合地冲——吸引强烈但冲突大，需磨合")
    elif tg_he:
        score += 15
        parts.insert(0, "日柱天合——性格合拍，相处轻松")
    elif dz_he:
        score += 12
        parts.insert(0, "日柱地合——生活节奏契合")

    score = max(0, min(100, score))

    # ── 评语 ──
    if score >= 80:
        verdict = "上等婚配——天干地支多重合会，层次匹配"
    elif score >= 60:
        verdict = "中等婚配——有一定契合度，需经营磨合"
    elif score >= 40:
        verdict = "普通匹配——各自独立，互不干扰"
    else:
        verdict = "需要经营的组合——冲害较多，建议互补短板"

    report = f"合婚评分 {score}/100 · {verdict}\n\n" + "\n".join(parts)
    return score, report
