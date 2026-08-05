"""升学/考试信号检测"""
from ..._constants import DIZHI_CANGGAN, WENCHANG, YIMA
from ...enums import Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal
from ..utils import (
    _has_branch_interaction,
    _make_prediction,
    is_favorable,
)


def detect_xuesheng_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                            day_branch: Dizhi, day_master: Tiangan,
                            year_branch: Dizhi,
                            month_branch: Dizhi | None = None,
                            hour_branch: Dizhi | None = None,
                            favorable: set[str] | None = None,
                            harmful: set[str] | None = None) -> list[EventSignal]:
    """检测升学/考试信号 — v0.3.0 增强版"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    wenchang = WENCHANG.get(day_master)
    yima = YIMA.get(year_branch)

    strength = 0
    triggers = []
    notes = []

    is_yin = ln_shishen in (Shishen.正印, Shishen.偏印)
    is_guan = ln_shishen in (Shishen.正官, Shishen.偏官)
    is_shishang = ln_shishen in (Shishen.食神, Shishen.伤官)
    fav = is_favorable(ln_shishen, favorable, harmful)

    # ═══ ★★★ 级别 ═══

    # 官印相生+文昌（完整版：官星+印星+文昌三要素）
    if is_yin and ln_branch == wenchang:
        strength = 3
        triggers.append(f"流年印星透干+文昌{wenchang.value}")
        if fav is True:
            notes.append("印星为喜→学习与准备主题偏积极，结果仍取决于实际投入")
        elif fav is False:
            notes.append("印星为忌→可留意学习节奏与压力，不据此判断成绩")

    # 官星得位+印星有力（textbook ★★★）
    if is_guan:
        # 同柱官印相生（天干官+地支含印）
        for hs in DIZHI_CANGGAN.get(ln_branch, []):
            if get_ten_god(day_master, hs.stem) in (Shishen.正印, Shishen.偏印):
                strength = max(strength, 3)
                triggers.append("流年官星透干、地支见印")
                notes.append("官印组合仅作学业环境的文化参考，仍需结合实际准备情况。")
                break

    # ═══ ★★ 级别 ═══

    # 印星透干且有根
    if is_yin:
        strength = max(strength, 2)
        triggers.append("流年印星透干")

    # 文昌贵人
    if ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("流年文昌贵人入命")

    # 文昌+驿马同现
    if ln_branch == yima and ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("文昌+驿马同现")

    # 食神吐秀（食伤年+文昌/印星伴生）
    if is_shishang and ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("流年食伤+文昌→食神吐秀")
        notes.append("食伤与文昌同现，只作表达、考试或竞赛主题参考")

    # 冲时柱（时柱为考试/晚年学业宫）
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲时柱")
        notes.append("冲时柱→可核对考试、证书或学习安排是否有变化")

    # 月柱逢合（学业宫被合动）
    if month_branch and _has_branch_interaction(month_branch, ln_branch, "六合"):
        strength = max(strength, 2)
        triggers.append("流年合月柱(学业宫)")
        notes.append("合动月柱→学习环境变化候选，需结合现实安排核对")

    # ═══ ★ 级别 ═══

    if is_yin and strength < 2:
        strength = 1
        triggers.append("流年印星透干")

    if ln_branch == wenchang and strength < 2:
        strength = 1
        triggers.append("文昌贵人")

    if triggers:
        direction = "中性" if fav is False else "正面"
        signals.append(EventSignal(
            category="升学",
            direction=direction,
            strength=min(strength, 3),
            prediction=_make_prediction("升学", direction, min(strength,3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals

