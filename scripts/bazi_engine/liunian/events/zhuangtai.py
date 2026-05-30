"""个人状态信号检测"""
from ...enums import TIANGAN_LU, Dizhi, Shishen, Tiangan
from ...ten_gods import get_ten_god
from ..signal import EventSignal
from ..utils import (
    _changsheng_status,
    _make_prediction,
    is_favorable,
)


def detect_zhuangtai_signals(ln_stem: Tiangan, ln_branch: Dizhi,
                              day_master: Tiangan, day_branch: Dizhi,
                              dayun_stem: Tiangan | None = None,
                              dayun_branch: Dizhi | None = None,
                              favorable: set[str] | None = None) -> list[EventSignal]:
    """检测个人状态信号（精力/自信/情绪）"""
    signals: list[EventSignal] = []
    ln_shishen = get_ten_god(day_master, ln_stem)
    fav = is_favorable(ln_shishen, favorable)
    lu = TIANGAN_LU.get(day_master)

    strength = 0
    triggers = []
    notes = []

    # ★★★: 禄神到位（日主临官）
    if ln_branch == lu:
        strength = 3
        triggers.append(f"流年{lu.value}为日主禄地")
        notes.append("禄神到位→精力充沛/自信高峰 (textbook)")

    # ★★★: 七杀攻身+身弱
    if ln_shishen == Shishen.偏官 and fav is False:
        strength = max(strength, 3)
        triggers.append("流年七杀攻身")
        notes.append("压力大/焦虑/身心疲惫 (textbook)")

    # ★★: 食神吐秀
    if ln_shishen == Shishen.食神:
        strength = max(strength, 2)
        triggers.append("流年食神透干")
        notes.append("心态放松/创造力强/享受生活" if fav is not False else "食神为忌→懒散贪玩")

    # ★★: 伤官透干
    if ln_shishen == Shishen.伤官:
        strength = max(strength, 2)
        triggers.append("流年伤官透干")
        notes.append("思维活跃/反叛/想改变 (textbook)")

    # ★★: 正印护身
    if ln_shishen in (Shishen.正印, Shishen.偏印) and fav is not False:
        strength = max(strength, 2)
        triggers.append("流年印星护身")
        notes.append("内心安稳/有依靠/适合学习 (textbook)")

    # 十二长生状态（独立触发，不依赖已有信号）
    cs = _changsheng_status(day_master, ln_branch)
    if cs in ("帝旺", "临官"):
        strength = max(strength, 2)
        triggers.append(f"日主{cs}")
        notes.append("自身状态佳/精力充沛")
    elif cs in ("死", "病", "绝", "墓"):
        strength = max(strength, 2)
        triggers.append(f"日主{cs}")
        notes.append("自身状态低迷/需休养")

    # 日柱伏吟（流年与日柱相同→个人重大节点）
    if ln_branch == day_branch:
        strength = max(strength, 2)
        triggers.append("流年伏吟日柱")
        notes.append("日柱伏吟→个人状态转折点/情绪波动 (textbook)")

    # 枭神夺食（偏印年+日主食神受制）
    if ln_shishen == Shishen.偏印:
        # 简化: 偏印年本身就压抑
        if fav is False:
            strength = max(strength, 2)
            triggers.append("枭神夺食→思维受限")
            notes.append("偏印为忌→思虑过度/钻牛角尖/情绪压抑")

    if triggers:
        # 方向判断
        _trig_str = str(triggers)
        if ln_branch == lu or "临官" in _trig_str or "帝旺" in _trig_str:
            direction = "正面"
        elif "死" in _trig_str or "病" in _trig_str or "绝" in _trig_str or "墓" in _trig_str:
            direction = "负面"
        elif "伏吟" in _trig_str:
            direction = "中性"
        elif "枭神" in _trig_str:
            direction = "负面"
        elif ln_shishen == Shishen.偏官 and fav is not True:
            direction = "负面"
        elif ln_shishen == Shishen.伤官:
            direction = "中性"
        elif fav is not False:
            direction = "正面"
        else:
            direction = "负面"
        # v0.10.1: 仅≥★3输出——★2模式(食神透干/十二长生/伏吟)太常见，稀释信号价值
        if strength >= 3:
            signals.append(EventSignal(
            category="状态",
            direction=direction,
            strength=min(strength, 3),
            prediction=_make_prediction("状态", direction, min(strength, 3), triggers, notes),
            triggers=triggers,
            notes=notes,
        ))
    return signals

