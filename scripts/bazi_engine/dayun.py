"""大运计算: 方向 序列 起运年龄"""

from dataclasses import dataclass
from datetime import datetime

from .enums import Dizhi, Tiangan, dizhi_by_index, tiangan_by_index
from .gender_rules import is_forward_luck
from .solar_terms import distance_to_next_jie, distance_to_prev_jie


def yang_nian(year_stem: Tiangan) -> bool:
    """阳年: 年干为甲丙戊庚壬"""
    return year_stem.yinyang == "阳"


def dayun_direction(year_stem: Tiangan, gender: str) -> str:
    """返回 "顺排" 或 "逆排"

    阳男阴女顺排，阴男阳女逆排
    """
    if is_forward_luck(year_stem, gender):
        return "顺排"
    return "逆排"


def generate_luck_pillars(month_stem: Tiangan, month_branch: Dizhi,
                          direction: str, count: int = 8) -> list[tuple[Tiangan, Dizhi]]:
    """生成大运干支序列"""
    result: list[tuple[Tiangan, Dizhi]] = []
    delta = 1 if direction == "顺排" else -1
    for i in range(1, count + 1):
        next_tg = tiangan_by_index((month_stem.index + i * delta) % 10)
        next_dz = dizhi_by_index((month_branch.index + i * delta) % 12)
        result.append((next_tg, next_dz))
    return result


def compute_start_age(birth_dt: datetime, direction: str,
                      solar_term_dates: dict | None = None) -> tuple[int, int, list[str]]:
    """返回 (整岁起运年龄, 余天数, warnings)

    - 顺排: 出生时间到下一个节的精确天数 ÷ 3
    - 逆排: 出生时间到上一个节的精确天数 ÷ 3
    - 取整后: 余0→4个月, 余1→4个月≈0岁, 余2→8个月≈1岁
    """
    if direction == "顺排":
        days_float, w = distance_to_next_jie(birth_dt)
    else:
        days_float, w = distance_to_prev_jie(birth_dt)
    warnings = list(w)

    # 浮点天→整数天（传统三天折一岁）
    total_days = round(days_float + 1e-9)
    age = total_days // 3
    remainder = total_days % 3
    # 余2天≈8个月，进位到下一岁
    if remainder == 2:
        age += 1
    return age, remainder, warnings


def compute_start_age_exact(birth_dt: datetime, direction: str) -> tuple[float, list[str]]:
    """返回起运精确年龄（年），用于大运边界而非仅供展示。"""
    if direction == "顺排":
        days_float, warnings = distance_to_next_jie(birth_dt)
    else:
        days_float, warnings = distance_to_prev_jie(birth_dt)
    return max(0.0, days_float / 3.0), list(warnings)


def compute_jiaoyun_detail(birth_dt: datetime, direction: str) -> tuple[dict, list[str]]:
    """Return detailed jiaoyun conversion from jieqi distance."""
    if direction == "顺排":
        days_float, warnings = distance_to_next_jie(birth_dt)
        reference = "下一节"
    else:
        days_float, warnings = distance_to_prev_jie(birth_dt)
        reference = "上一节"

    # 传统折算为三天一岁、一天四个月。将小时折入月数，避免展示和
    # 实际扫描都把交运时刻压成整岁。
    total_months = max(0, round(days_float * 4))
    years, months = divmod(total_months, 12)

    return {
        "reference": reference,
        "total_days": round(days_float, 4),
        "years": years,
        "months": months,
        "days": 0,
        "hours": 0,
        "start_age_exact": total_months / 12,
        "formula": "三天折一岁，余一天折四个月",
    }, list(warnings)


def format_luck_periods(start_age: int, luck_pillars: list[tuple[Tiangan, Dizhi]]) -> list[dict]:
    """格式化大运周期: 每步10年"""
    periods: list[dict] = []
    for i, (tg, dz) in enumerate(luck_pillars):
        begin = start_age + i * 10
        end = begin + 9
        periods.append({
            "大运": f"{tg.value}{dz.value}",
            "年龄": f"{begin}-{end}岁",
            "天干": tg,
            "地支": dz,
            "序": i + 1,
            "weight_note": "大运干支关系由引擎综合展示；不把固定百分比或前后五年划分表述为古籍定论。",
        })
    return periods


def generate_xiaoyun_pillars(hour_stem: Tiangan, hour_branch: Dizhi,
                             direction: str, count: int) -> list[tuple[Tiangan, Dizhi]]:
    """生成小运/童限干支序列，以时柱为基准，一岁一柱。"""
    result: list[tuple[Tiangan, Dizhi]] = []
    delta = 1 if direction == "顺排" else -1
    for i in range(1, max(0, count) + 1):
        tg = tiangan_by_index((hour_stem.index + i * delta) % 10)
        dz = dizhi_by_index((hour_branch.index + i * delta) % 12)
        result.append((tg, dz))
    return result


def format_xiaoyun_periods(xiaoyun_pillars: list[tuple[Tiangan, Dizhi]]) -> list[dict]:
    """格式化小运周期: 一岁一柱。"""
    return [
        {"小运": f"{tg.value}{dz.value}", "年龄": f"{i}岁", "天干": tg, "地支": dz, "序": i}
        for i, (tg, dz) in enumerate(xiaoyun_pillars, start=1)
    ]


def describe_dayun_weight(dayun_stem: Tiangan, dayun_branch: Dizhi) -> str:
    """返回大运权重说明文本。

    固定权重是项目工程启发式，不是古籍量化结论。
    """
    branch_wx = dayun_branch.wuxing.value
    stem_wx = dayun_stem.wuxing.value
    return (
        f"工程提示：大运地支{dayun_branch.value}({branch_wx})与天干{dayun_stem.value}({stem_wx})"
        "共同参与分析；不使用固定百分比或前后五年断语。"
    )


# ═══════════════════════════════════════════════════════════════
# 大运调制器（v0.8.0: 方向二核心）
# ═══════════════════════════════════════════════════════════════

@dataclass
class DayunModulation:
    """单步大运的调制结果"""
    period_index: int           # 大运序号 (0-based)
    dayun_stem: str             # 大运天干
    dayun_branch: str           # 大运地支
    age_range: str              # "25-34岁"

    # 大运与原局关系
    stem_interactions: list[str]   # 大运天干与原局天干的合冲
    branch_interactions: list[str] # 大运地支与原局地支的合冲刑害

    # 喜忌判定
    stem_is_favorable: bool | None     # 大运天干十神是否为喜用
    branch_is_favorable: bool | None   # 大运地支五行是否为喜用

    # 调制参数
    baseline_offset: int        # 流年基线偏移: +1(吉运), 0(平运), -1(凶运)
    theme: str                  # 十年主题: "财运"|"官运"|"印运"|"比劫运"|"食伤运"
    theme_weight: float         # 主题加权: 0.5~1.5

    # 全局修正
    modulation_note: str        # 调制说明文本

    def to_dict(self) -> dict:
        return {
            "period_index": self.period_index,
            "dayun_stem": self.dayun_stem,
            "dayun_branch": self.dayun_branch,
            "age_range": self.age_range,
            "stem_interactions": self.stem_interactions,
            "branch_interactions": self.branch_interactions,
            "stem_is_favorable": self.stem_is_favorable,
            "branch_is_favorable": self.branch_is_favorable,
            "baseline_offset": self.baseline_offset,
            "theme": self.theme,
            "theme_weight": self.theme_weight,
            "modulation_note": self.modulation_note,
            "rule_source": "工程启发式",
        }


class DayunModulator:
    """大运调制器：分析每步大运对原局的影响，生成流年基线偏移。

    三层次：
    1. 大运干支与原局合冲刑害 → 生成"修正底盘"
    2. 大运十神喜忌 → 流年 signal baseline ±1
    3. 大运十二长生 → 十年气数分层
    """

    def __init__(self, day_master, natal_stems: list, natal_branches: list,
                 luck_pillars: list[tuple], start_age: int,
                 favorable_wuxing: set[str], harmful_wuxing: set[str],
                 favorable_shishen: set[str], harmful_shishen: set[str]):
        self._dm = day_master
        self._natal_stems = natal_stems
        self._natal_branches = natal_branches
        self._luck_pillars = luck_pillars
        self._start_age = start_age
        self._fav_wx = favorable_wuxing
        self._harm_wx = harmful_wuxing
        self._fav_ss = favorable_shishen
        self._harm_ss = harmful_shishen

        from ._constants import (
            DIZHI_LIUCHONG,
            DIZHI_LIUHE,
            DIZHI_SANHE,
            DIZHI_SANHUI,
            DIZHI_XIANGHAI,
            DIZHI_XIANGXING,
            DIZHI_ZIXING,
        )
        from .ten_gods import get_ten_god
        self._get_ten_god = get_ten_god
        self._liuchong = DIZHI_LIUCHONG
        self._liuhe = DIZHI_LIUHE
        self._xianghai = DIZHI_XIANGHAI
        self._sanhe = DIZHI_SANHE
        self._sanhui = DIZHI_SANHUI
        self._xiangxing = DIZHI_XIANGXING
        self._zixing = DIZHI_ZIXING

    def modulate(self) -> list[DayunModulation]:
        """分析所有大运，返回调制结果列表"""
        results: list[DayunModulation] = []
        for i, (tg, dz) in enumerate(self._luck_pillars):
            mod = self._analyze_one_period(i, tg, dz)
            results.append(mod)
        return results

    def _analyze_one_period(self, idx: int, tg, dz) -> DayunModulation:
        """分析单步大运"""
        begin_age = self._start_age + idx * 10

        # 1. 检测大运与原局的干支互动
        stem_inters = self._check_stem_interactions(tg)
        branch_inters = self._check_branch_interactions(dz)

        # 2. 喜忌判定
        stem_fav = self._check_stem_favorability(tg)
        branch_fav = self._check_branch_favorability(dz)

        # 3. 基线偏移：工程启发式，不能视为古籍量化规则。
        branch_score = 1 if branch_fav is True else (-1 if branch_fav is False else 0)
        stem_score = 1 if stem_fav is True else (-1 if stem_fav is False else 0)
        weighted = branch_score * 0.6 + stem_score * 0.4
        if weighted >= 0.4:
            baseline_offset = 1
        elif weighted <= -0.4:
            baseline_offset = -1
        else:
            baseline_offset = 0

        # 4. 主题判定: 大运天干十神 → 十年主题
        ss = self._get_ten_god(self._dm, tg)
        theme_map = {
            "正财": "财运", "偏财": "财运",
            "正官": "官运", "偏官": "官运",
            "正印": "印运", "偏印": "印运",
            "食神": "食伤运", "伤官": "食伤运",
            "比肩": "比劫运", "劫财": "比劫运",
        }
        theme = theme_map.get(ss.value if ss else "", "平运")

        # 主题权重: 大运主题与流年十神一致时加权1.3, 冲突时减权0.7
        theme_weight = 1.0 if theme != "平运" else 0.8

        # 5. 调制说明
        parts = []
        if stem_inters:
            parts.append(f"天干: {';'.join(stem_inters)}")
        if branch_inters:
            parts.append(f"地支: {';'.join(branch_inters)}")
        parts.append(f"大运{ss.value if ss else '?'}→主题'{theme}'")
        if baseline_offset > 0:
            parts.append("十年基调偏吉")
        elif baseline_offset < 0:
            parts.append("十年基调偏凶")
        else:
            parts.append("十年基调平缓")
        modulation_note = "。".join(parts) + "。"

        return DayunModulation(
            period_index=idx,
            dayun_stem=tg.value,
            dayun_branch=dz.value,
            age_range=f"{begin_age}-{begin_age + 9}岁",
            stem_interactions=stem_inters,
            branch_interactions=branch_inters,
            stem_is_favorable=stem_fav,
            branch_is_favorable=branch_fav,
            baseline_offset=baseline_offset,
            theme=theme,
            theme_weight=theme_weight,
            modulation_note=modulation_note,
        )

    def _check_stem_interactions(self, dayun_stem) -> list[str]:
        """检查大运天干与原局天干的五合/相克"""
        inters: list[str] = []
        from ._constants import TIANGAN_WUHE
        for natal_stem in self._natal_stems:
            pair = (dayun_stem, natal_stem)
            if pair in TIANGAN_WUHE:
                hua_wx = TIANGAN_WUHE[pair]
                inters.append(f"与原局{natal_stem.value}五合{hua_wx.value}候选")
        return inters

    def _check_branch_interactions(self, dayun_branch) -> list[str]:
        """检查大运地支与原局地支的冲合刑害（含三合/三会/相刑/自刑）"""
        inters: list[str] = []
        natal_set = set(self._natal_branches)
        all_set = natal_set | {dayun_branch}

        # 1. 六冲/六合/相害/相刑 (pairwise, 优先级: 冲>合>害>刑>自刑)
        for natal_branch in self._natal_branches:
            pair = (dayun_branch, natal_branch)
            if pair in self._liuchong:
                inters.append(f"冲原局{natal_branch.value}")
            elif pair in self._liuhe:
                inters.append(f"合原局{natal_branch.value}")
            elif pair in self._xianghai:
                inters.append(f"害原局{natal_branch.value}")
            elif pair in self._xiangxing:
                inters.append(f"刑原局{natal_branch.value}")
            elif dayun_branch == natal_branch and dayun_branch in self._zixing:
                inters.append(f"与原局{natal_branch.value}自刑")

        # 2. 三合/半合: 大运参与即触发
        for trio_set, wx in self._sanhe.items():
            trio = list(trio_set)
            if dayun_branch not in trio:
                continue
            match_count = sum(1 for b in trio if b in all_set)
            if match_count == 3:
                inters.append(f"与原局三合{getattr(wx, 'value', str(wx))}局")
            elif match_count == 2:
                other = next(b for b in trio if b in all_set and b != dayun_branch)
                inters.append(f"与原局{other.value}半合{getattr(wx, 'value', str(wx))}")

        # 3. 三会: 三支齐聚方成局
        for trio_set, wx in self._sanhui.items():
            trio = list(trio_set)
            if dayun_branch not in trio:
                continue
            if sum(1 for b in trio if b in all_set) == 3:
                inters.append(f"与原局三会{getattr(wx, 'value', str(wx))}方")

        return inters

    def _check_stem_favorability(self, dayun_stem) -> bool | None:
        """大运天干十神是否为日主喜用"""
        ss = self._get_ten_god(self._dm, dayun_stem)
        if ss is None:
            return None
        if self._fav_ss and ss.value in self._fav_ss:
            return True
        if self._harm_ss and ss.value in self._harm_ss:
            return False
        return None

    def _check_branch_favorability(self, dayun_branch) -> bool | None:
        """大运地支五行是否为日主喜用"""
        wx = dayun_branch.wuxing.value
        if wx in self._fav_wx:
            return True
        if wx in self._harm_wx:
            return False
        return None
