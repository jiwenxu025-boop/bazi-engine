"""官非/法律风险信号检测"""
from ..._constants import DIZHI_LIUHE, DIZHI_SANHE, chong_pair
from ...enums import Dizhi, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal


def detect_guanfei_signals(
    ln_tg: Tiangan, ln_dz: Dizhi,
    day_master: Tiangan, day_branch: Dizhi,
    year_branch: Dizhi, month_branch: Dizhi,
    hour_branch: Dizhi,
    dn_tg: Tiangan | None, dn_dz: Dizhi | None,
    natal_shang_guan: bool = False,
    pillars_tengan: list[Tiangan] | None = None,
) -> list[EventSignal]:
    """官非/法律风险检测——伤官见官+流年触发。

    古籍来源：《渊海子平》「伤官见官，为祸百端」；
    《三命通会》「伤官见官，仕途多阻，轻则口舌，重则官非牢狱」

    触发条件（需同时满足）：
    1. 命局有伤官见官（天干透出或地支构成）
    2. 流年天干/大运天干透出正官或伤官
    3. 有冲克激化（流年冲大运/大运冲月柱等）
    """
    if not natal_shang_guan:
        return []

    events: list[EventSignal] = []
    strength = 0
    triggers: list[str] = []
    notes: list[str] = []

    # 大运天干是否透正官/伤官
    dn_shishen = None
    if dn_tg:
        dn_shishen = get_ten_god(day_master, dn_tg)
    dn_is_guan = dn_shishen and dn_shishen.value in ("正官", "偏官")
    dn_is_shang = dn_shishen and dn_shishen.value == "伤官"

    # 流年天干
    ln_shishen = get_ten_god(day_master, ln_tg)
    ln_is_guan = ln_shishen and ln_shishen.value in ("正官", "偏官")
    ln_is_shang = ln_shishen and ln_shishen.value == "伤官"

    # 流年透伤官 → +1
    if ln_is_shang:
        strength += 1
        triggers.append("流年伤官透干")
        notes.append("流年伤官→才华锋芒外露，注意言行不要触碰规则红线")

    # 流年透正官 → +1（伤官见官直接触发）
    if ln_is_guan:
        strength += 1
        triggers.append("流年正官出现→伤官见官触发")
        notes.append("正官到位+伤官冲撞→官非口舌风险升高")

    # 大运透伤官/正官 → +1
    if dn_is_shang or dn_is_guan:
        strength += 1
        triggers.append(f"大运透{dn_shishen.value if dn_shishen else '?'}")
        notes.append(f"大运{dn_shishen.value if dn_shishen else ''}持续施加影响")

    # 流年冲大运 → +1（环境冲击）
    if dn_dz and ln_dz == chong_pair(dn_dz):
        strength += 1
        triggers.append("流年冲大运→环境激变")
        notes.append("流年冲大运→人生阶段被迫改变")

    # 流年合官星 → +1
    if ln_dz and day_branch:
        pair = frozenset({ln_dz, day_branch})
        if pair in DIZHI_LIUHE or pair in DIZHI_SANHE or any(
            pair.issubset(s) for s in DIZHI_SANHE
        ):
            strength += 1
            triggers.append("流年合动日支→牵动自身")

    if strength >= 2:
        direction = "负面"
        if strength == 2:
            pred = "注意法律风险或与权威的冲突，遵守规则，避免冲动行事"
        else:
            pred = "高风险年份——注意法律纠纷、官非诉讼或与权威机构的冲突，切忌触犯规则底线"

        events.append(EventSignal(
            category="官非",
            direction=direction,
            strength=min(strength, 3),
            prediction=pred,
            triggers=triggers,
            notes=notes,
        ))

    return events

