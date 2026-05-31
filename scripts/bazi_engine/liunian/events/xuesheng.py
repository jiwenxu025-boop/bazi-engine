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
                            favorable: set[str] | None = None) -> list[EventSignal]:
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
    fav = is_favorable(ln_shishen, favorable)

    # ═══ ★★★ 级别 ═══

    # 官印相生+文昌（完整版：官星+印星+文昌三要素）
    if is_yin and ln_branch == wenchang:
        strength = 3
        triggers.append(f"流年印星透干+文昌{wenchang.value}")
        if fav is True:
            notes.append("印星为喜→考试运强")
        elif fav is False:
            notes.append("印星为忌→压力大但成绩未必差")

    # 官星得位+印星有力（textbook ★★★）
    if is_guan and is_yin:
        # 同柱官印相生（天干官+地支含印）
        for hs in DIZHI_CANGGAN.get(ln_branch, []):
            if get_ten_god(day_master, hs.stem) in (Shishen.正印, Shishen.偏印):
                strength = max(strength, 3)
                triggers.append("流年官印相生+文昌有力")
                notes.append("官印相生→功名最利 (textbook)")
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

    # 巳亥冲+驿马→高考远行 (calibration: 2/2)
    if ln_branch == yima and _has_branch_interaction(year_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append(f"{year_branch.value}{ln_branch.value}冲+驿马→为学业远行")
        notes.append("巳亥冲+驿马+升学年龄→高考异地 (校准 2/2: 案例A2025, 案例C2025)")

    # 文昌+驿马同现
    if ln_branch == yima and ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("文昌+驿马同现")

    # 食神吐秀（食伤年+文昌/印星伴生）
    if is_shishang and ln_branch == wenchang:
        strength = max(strength, 2)
        triggers.append("流年食伤+文昌→食神吐秀")
        notes.append("以才华考试/竞赛见长 (textbook)")

    # 冲时柱（时柱为考试/晚年学业宫）
    if hour_branch and _has_branch_interaction(hour_branch, ln_branch, "六冲"):
        strength = max(strength, 2)
        triggers.append("流年冲时柱")
        notes.append("冲时柱→考试/证书相关变动")

    # 月柱逢合（学业宫被合动）
    if month_branch and _has_branch_interaction(month_branch, ln_branch, "六合"):
        strength = max(strength, 2)
        triggers.append("流年合月柱(学业宫)")
        notes.append("合动月柱→学业环境变化")

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

