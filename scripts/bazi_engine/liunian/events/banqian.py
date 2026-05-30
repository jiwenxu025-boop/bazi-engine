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
        notes.append("双驿马→重大搬迁/远行 (textbook)")

    # ═══ ★★ 级别 ═══

    # 驒马逢冲（流年驿马与原局/大运相冲）
    if is_yima_yr:
        chong_dz = chong_pair(ln_branch)
        chong_yuanju = _has_branch_interaction(year_branch, chong_dz, "六冲") or \
                       _has_branch_interaction(day_branch, chong_dz, "六冲") or \
                       _has_branch_interaction(month_branch, chong_dz, "六冲")
        chong_dayun = dayun_branch and _has_branch_interaction(dayun_branch, chong_dz, "六冲")
        if chong_yuanju or chong_dayun:
            strength = max(strength, 2)
            triggers.append("流年驿马逢冲")
            notes.append("驿马逢冲→必动 (textbook)")

    # 驿马年
    if is_yima_yr:
        strength = max(strength, 2)
        triggers.append("流年驿马")

    # 大运驿马+流年合驿马
    if dayun_branch and dayun_branch == yima and _has_branch_interaction(ln_branch, yima, "六合"):
        strength = max(strength, 2)
        triggers.append("大运驿马+流年合动")
        notes.append("大运驿马被流年合动→当年搬迁 (textbook)")

    # 驿马+财星/官星 → 因工作/求财远行
    if is_yima_yr and ln_shishen:
        if ln_shishen in (Shishen.正财, Shishen.偏财):
            strength = max(strength, 2)
            triggers.append("驿马+财星→求财远行")
        elif ln_shishen in (Shishen.正官, Shishen.偏官):
            strength = max(strength, 2)
            triggers.append("驿马+官星→工作调动远行")

    # 冲月柱（环境宫）
    if _has_branch_interaction(month_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲月柱(环境宫)")
        notes.append("冲月柱→环境/居住地变动")

    # 冲年柱（祖基宫）
    if _has_branch_interaction(year_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲年柱(祖基宫)")

    # 冲时柱（门户）
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲时柱(门户)")
        notes.append("冲时柱→门户变动/搬家 (textbook)")

    # 合月柱（环境宫被合动）
    if _has_branch_interaction(month_branch, ln_branch, "六合") or _has_branch_interaction(month_branch, ln_branch, "三合"):
        strength = max(strength, 2)
        triggers.append("流年合月柱(环境宫)")
        notes.append("合动月柱→环境变化/搬迁移居")

    # 驿马+印星 → 因学业/工作调动搬迁
    if is_yima_yr and ln_shishen in (Shishen.正印, Shishen.偏印):
        strength = max(strength, 2)
        triggers.append("驿马+印星→学习/工作调动搬迁")
        notes.append("印星主文书/合同→因入学/入职/调令而搬迁 (textbook)")

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

