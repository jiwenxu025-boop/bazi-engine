"""搬迁/远行信号检测"""
from ..._constants import YIMA, chong_pair
from ...enums import Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal
from ..utils import (
    _has_branch_interaction,
    _make_prediction,
)


def detect_banqian_signals(ln_branch: Dizhi,
                           year_branch: Dizhi, day_branch: Dizhi,
                           month_branch: Dizhi,
                           hour_branch: Dizhi | None = None,
                           dayun_branch: Dizhi | None = None,
                           dayun_stem: Tiangan | None = None,
                           ln_stem: Tiangan | None = None,
                           day_master: Tiangan | None = None,
                           favorable: set[str] | None = None) -> list[EventSignal]:
    """检测搬迁/远行信号 — v0.3.0 增强版"""
    signals: list[EventSignal] = []
    yima = YIMA.get(year_branch)

    strength = 0
    triggers = []
    notes = []

    is_yima_yr = ln_branch == yima
    ln_shishen = get_ten_god(day_master, ln_stem) if day_master and ln_stem else None

    # ═══ ★★★ 级别 ═══

    # 大运流年双驿马
    if is_yima_yr and dayun_branch and dayun_branch == yima:
        strength = 3
        triggers.append("大运流年双驿马")
        notes.append("双驿马只表示出行或环境调整信号较集中，不代表必然搬迁。")

    # ═══ ★★ 级别 ═══

    # 驒马逢冲（流年驿马与原局/大运相冲）
    if is_yima_yr:
        chong_dz = chong_pair(ln_branch)
        chong_yuanju = chong_dz in (year_branch, day_branch, month_branch, hour_branch)
        chong_dayun = dayun_branch == chong_dz
        if chong_yuanju or chong_dayun:
            strength = max(strength, 2)
            triggers.append("流年驿马逢冲")
            notes.append("驿马受冲可作为出行、环境调整的文化参考，不作必然事件断言。")

    # 驿马年
    if is_yima_yr:
        strength = max(strength, 2)
        triggers.append("流年驿马")

    # 大运驿马+流年合驿马
    if dayun_branch and dayun_branch == yima and _has_branch_interaction(ln_branch, yima, "六合"):
        strength = max(strength, 2)
        triggers.append("大运驿马+流年合动")
        notes.append("大运驿马被流年合动→出行或环境调整候选")

    # 驿马+财星/官星 → 因工作/求财远行
    if is_yima_yr and ln_shishen:
        if ln_shishen in (Shishen.正财, Shishen.偏财):
            strength = max(strength, 2)
            triggers.append("驿马+财星→出行或资源安排候选")
        elif ln_shishen in (Shishen.正官, Shishen.偏官):
            strength = max(strength, 2)
            triggers.append("驿马+官星→工作地点调整候选")

    # 冲月柱（环境宫）
    if _has_branch_interaction(month_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲月柱(环境宫)")
        notes.append("冲月柱→环境或居住安排变化候选，不单独判断搬迁")

    # 冲年柱（祖基宫）
    if _has_branch_interaction(year_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲年柱(祖基宫)")

    # 冲时柱（门户）
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲时柱(门户)")
        notes.append("冲时柱→出行或居住安排变化候选")

    # 合月柱（环境宫被合动）
    if _has_branch_interaction(month_branch, ln_branch, "六合") or _has_branch_interaction(month_branch, ln_branch, "三合"):
        strength = max(strength, 2)
        triggers.append("流年合月柱(环境宫)")
        notes.append("合动月柱→环境变化候选，不单独判断搬迁")

    # 驿马+印星 → 因学业/工作调动搬迁
    if is_yima_yr and ln_shishen in (Shishen.正印, Shishen.偏印):
        strength = max(strength, 2)
        triggers.append("驿马+印星→学习或工作环境调整候选")
        notes.append("可结合入学、入职或文书安排核对是否存在现实变动。")

    # ═══ ★ 级别 ═══

    if is_yima_yr and strength < 2:
        strength = 1
        triggers.append("流年驿马")

    if triggers:
        signals.append(EventSignal(
            category="搬迁",
            direction="中性",
            strength=min(strength, 3),
            prediction=_make_prediction("搬迁", "中性", min(strength,3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals

