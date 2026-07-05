"""BaziChart 数据类 + build_chart() 工厂函数 — 一站式八字排盘"""

import os
from dataclasses import dataclass, field
from datetime import date, datetime

from ._constants import DIZHI_CANGGAN, get_nayin
from ._constants import HiddenStem as HStem
from .dayun import compute_start_age, dayun_direction, format_luck_periods, generate_luck_pillars
from .enums import Dizhi, Shishen, Tiangan
from .interactions import (
    Interaction,
    find_all_dizhi_interactions,
    find_tiangan_wuhe,
)
from .liunian import AnnualScan, scan_years
from .pattern import determine_pattern
from .pillars import compute_day_pillar, compute_hour_pillar, compute_month_pillar, compute_year_pillar
from .spirits import SpiritAgent, find_all_spirits
from .ten_gods import get_ten_god


@dataclass
class PillarData:
    pillar_type: str            # "年柱" | "月柱" | "日柱" | "时柱"
    stem: Tiangan
    branch: Dizhi
    hidden_stems: list[HStem] = field(default_factory=list)
    ten_god: Shishen | None = None
    ten_gods_map: dict = field(default_factory=dict)  # {stem: Shishen} for hidden stems too
    nayin: str = ""            # 纳音五行

    def to_dict(self) -> dict:
        return {
            "pillar_type": self.pillar_type,
            "stem": self.stem.value,
            "branch": self.branch.value,
            "nayin": self.nayin,
            "hidden_stems": [{"stem": hs.stem.value, "level": hs.level} for hs in self.hidden_stems],
            "ten_god": self.ten_god.value if self.ten_god else None,
            "ten_gods_map": {k.value: v.value for k, v in self.ten_gods_map.items()},
        }


@dataclass
class BaziChart:
    # 输入
    name: str
    gender: str                # "男" | "女"
    birth_dt: datetime
    day_pillar_source: str     # "formula" | "override"

    # 四柱
    year: PillarData = field(init=False)
    month: PillarData = field(init=False)
    day: PillarData = field(init=False)
    hour: PillarData = field(init=False)
    day_master: Tiangan = field(init=False)

    # 命宫 / 身宫 / 胎元
    minggong_stem: Tiangan | None = None
    minggong_branch: Dizhi | None = None
    minggong_nayin: str = ""
    shengong_stem: Tiangan | None = None
    shengong_branch: Dizhi | None = None
    shengong_nayin: str = ""
    taiyuan_stem: Tiangan | None = None
    taiyuan_branch: Dizhi | None = None
    taiyuan_nayin: str = ""

    # 格局
    pattern: str = ""
    pattern_notes: list[str] = field(default_factory=list)

    # 大运
    luck_pillars: list[tuple[Tiangan, Dizhi]] = field(default_factory=list)
    luck_periods: list[dict] = field(default_factory=list)
    start_age: int = 0
    dayun_direction_str: str = ""

    # 干支关系
    tiangan_interactions: list[Interaction] = field(default_factory=list)
    dizhi_interactions: list[Interaction] = field(default_factory=list)

    # 神煞
    spirits: list[SpiritAgent] = field(default_factory=list)

    # 流年扫描
    annual_scans: list[AnnualScan] = field(default_factory=list)

    # 喜用
    favorable_tags: set[str] = field(default_factory=set)

    # 诊断
    warnings: list[str] = field(default_factory=list)

    # 人生阶段
    life_stage: str = ""          # 智能判定的人生阶段
    life_stage_override: str = ""  # 用户手动覆盖

    # 用户输入（校准用）
    family_context: dict | None = None  # {economic_level, father_occupation, mother_occupation}

    # 性格与家境分析
    personality_result: dict | None = None
    family_result: dict | None = None

    # 高级技法
    void_gods: list = field(default_factory=list)                # 藏干虚神
    nayin_relations: list = field(default_factory=list)          # 纳音生克链
    changsheng_states: list = field(default_factory=list)        # 十二长生状态
    palace_star_result: dict | None = None                       # 宫位叠象
    tiaohou_result: dict | None = None                           # 调候独立分析
    dayun_modulations: list[dict] | None = None                  # 大运调制结果 (v0.8.0)
    tansheng_wangke: list[dict] | None = None                    # 贪生忘克结果 (v0.8.0)
    false_generations: list[dict] | None = None                  # 假生陷阱结果 (v0.13.0)
    dayun_interpretations: list[dict] | None = None              # 大运 LLM 解读 (v0.14.0)
    body_use_result: dict | None = None                          # 宾主体用 + 墓库应期
    health_profile: dict | None = None                           # 健康体质画像 (v0.10.0: 调候+五行脏腑)

    # 用神推荐（内部缓存，由 build_chart() 填充）
    _yongshen_result: dict | None = field(default=None, repr=False)

    # 辅助
    hour_zi_flag: str | None = None
    hour_confirmed: bool = True  # 时辰是否经用户确认

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gender": self.gender,
            "birth": self.birth_dt.strftime("%Y-%m-%d %H:%M"),
            "day_pillar_source": self.day_pillar_source,
            "four_pillars": {
                "year": self.year.to_dict(),
                "month": self.month.to_dict(),
                "day": self.day.to_dict(),
                "hour": self.hour.to_dict(),
            },
            "minggong": {
                "stem": self.minggong_stem.value if self.minggong_stem else None,
                "branch": self.minggong_branch.value if self.minggong_branch else None,
                "nayin": self.minggong_nayin,
            },
            "shengong": {
                "stem": self.shengong_stem.value if self.shengong_stem else None,
                "branch": self.shengong_branch.value if self.shengong_branch else None,
                "nayin": self.shengong_nayin,
            },
            "taiyuan": {
                "stem": self.taiyuan_stem.value if self.taiyuan_stem else None,
                "branch": self.taiyuan_branch.value if self.taiyuan_branch else None,
                "nayin": self.taiyuan_nayin,
            },
            "day_master": {
                "stem": self.day_master.value,
                "wuxing": self.day_master.wuxing.value,
                "yinyang": self.day_master.yinyang,
            },
            "pattern": self.pattern,
            "pattern_notes": self.pattern_notes,
            "favorable": sorted(self.favorable_tags) if self.favorable_tags else [],
            "yongshen": self._yongshen_result,
            "dayun": {
                "direction": self.dayun_direction_str,
                "start_age": self.start_age,
                "periods": [
                    {"stem": tg.value, "branch": dz.value, "age": lp["年龄"], "order": i + 1}
                    for i, ((tg, dz), lp) in enumerate(zip(self.luck_pillars, self.luck_periods))
                ],
                "modulations": self.dayun_modulations,
                "interpretations": self.dayun_interpretations,
            },
            "interactions": {
                "tiangan": [i.to_dict() for i in self.tiangan_interactions],
                "dizhi": [i.to_dict() for i in self.dizhi_interactions],
            },
            "spirits": [s.to_dict() for s in self.spirits],
            "annual_scans": [a.to_dict() for a in self.annual_scans] if hasattr(self, "annual_scans") and self.annual_scans else [],
            "warnings": self.warnings,
            "personality": self.personality_result,
            "family": self.family_result,
            "life_stage": self.life_stage,
            "void_gods": [v.to_dict() for v in self.void_gods],
            "nayin_relations": [nr.to_dict() for nr in self.nayin_relations],
            "changsheng": [cs.to_dict() for cs in self.changsheng_states] if hasattr(self, "changsheng_states") and self.changsheng_states else [],
            "palace_star": self.palace_star_result,
            "tiaohou": self.tiaohou_result,
            "health_profile": self.health_profile,
            "body_use": self.body_use_result,
        }


def compute_minggong_full(year_stem: Tiangan, month_branch: Dizhi,
                          hour_branch: Dizhi) -> tuple[Tiangan, Dizhi, str]:
    """计算命宫（完整版，含天干和纳音）

    命宫支: (月数 + 时数 - 6) 调整到 [1,12]
    月数: 寅=1,...,丑=12; 时数: 子=1,...,亥=12
    结果: 1=子,...,12=亥
    """
    from ._constants import WUHU_DUNYUAN, get_nayin
    from .enums import dizhi_by_index, tiangan_by_index

    m_num = (month_branch.index - 2) % 12 + 1  # 寅=1,...,丑=12
    h_num = hour_branch.index + 1               # 子=1,...,亥=12

    # 命宫地支: (m + h - 6) → [1,12]
    mg_num = (m_num + h_num - 6 - 1) % 12 + 1
    mg_branch = dizhi_by_index(mg_num - 1)

    # 命宫天干：以年干用五虎遁推算至命宫支位
    yin_stem = WUHU_DUNYUAN[year_stem]
    offset = (mg_branch.index - Dizhi.寅.index) % 10
    mg_stem = tiangan_by_index((yin_stem.index + offset) % 10)

    nayin = get_nayin(mg_stem, mg_branch)
    return mg_stem, mg_branch, nayin


def compute_shengong_full(year_stem: Tiangan, month_branch: Dizhi,
                          hour_branch: Dizhi) -> tuple[Tiangan, Dizhi, str]:
    """计算身宫

    身宫支: (26 - 月数 - 时数) % 12
    身宫干: 以年干用五虎遁推算至身宫支位
    """
    from ._constants import WUHU_DUNYUAN, get_nayin
    from .enums import dizhi_by_index, tiangan_by_index

    m_num = (month_branch.index - 2) % 12 + 1
    h_num = hour_branch.index + 1

    sg_num = (26 - m_num - h_num) % 12
    if sg_num == 0:
        sg_num = 12
    sg_branch = dizhi_by_index(sg_num - 1)

    yin_stem = WUHU_DUNYUAN[year_stem]
    offset = (sg_branch.index - Dizhi.寅.index) % 10
    sg_stem = tiangan_by_index((yin_stem.index + offset) % 10)

    nayin = get_nayin(sg_stem, sg_branch)
    return sg_stem, sg_branch, nayin


def compute_taiyuan(month_stem: Tiangan, month_branch: Dizhi) -> tuple[Tiangan, Dizhi, str]:
    """计算胎元

    胎元干 = 月干前推一位
    胎元支 = 月支前推三位
    """
    from ._constants import get_nayin
    from .enums import dizhi_by_index, tiangan_by_index

    ty_stem = tiangan_by_index((month_stem.index + 1) % 10)
    ty_branch = dizhi_by_index((month_branch.index + 3) % 12)
    nayin = get_nayin(ty_stem, ty_branch)

    return ty_stem, ty_branch, nayin


def _build_llm_interactions(chart) -> dict:
    """构建 LLM 审查用的干支交互数据（天干五合 + 地支六合/三合/六冲/相刑/相害）。"""
    result = {
        "天干五合": [it.to_dict() for it in chart.tiangan_interactions],
        "地支六合": [], "三合": [], "六冲": [], "相刑": [], "相害": [],
    }
    type_map = {
        "地支六合": "地支六合", "三合": "三合", "半合": "三合", "三会": "三合",
        "六冲": "六冲", "相刑": "相刑", "自刑": "相刑", "相害": "相害",
    }
    for it in chart.dizhi_interactions:
        bucket = type_map.get(it.inter_type)
        if bucket:
            result[bucket].append(it.to_dict())
    return result


def _build_llm_context(chart) -> dict:
    """为 LLM review 构建精简上下文（不包含 annual_scans，因为尚未生成）"""
    return {
        "name": chart.name,
        "gender": chart.gender,
        "day_master": {
            "stem": chart.day_master.value,
            "wuxing": chart.day_master.wuxing.value,
            "yinyang": chart.day_master.yinyang,
        },
        "pattern": chart.pattern,
        "pillars": {
            "year": {"stem": chart.year.stem.value, "branch": chart.year.branch.value},
            "month": {"stem": chart.month.stem.value, "branch": chart.month.branch.value},
            "day": {"stem": chart.day.stem.value, "branch": chart.day.branch.value},
            "hour": {"stem": chart.hour.stem.value, "branch": chart.hour.branch.value},
        },
        "yongshen": chart._yongshen_result or {},
        "tiaohou": chart.tiaohou_result or {},
        "interactions": _build_llm_interactions(chart),
        "known_events": {},
    }


def build_chart(
    name: str,
    gender: str,
    year: int,
    month: int,
    day: int,
    hour: int,
    day_pillar_override: tuple[str, str] | None = None,
    liunian_range: tuple[int, int] | None = None,
    known_events: dict[int, str] | None = None,
    favorable: set[str] | None = None,
    calibrate: bool = False,
    life_stage_override: str = "",
    family_context: dict | None = None,
    hour_confirmed: bool = True,
    on_llm_result=None,  # v0.11.1: 流式回调 callable(year, signals)
    on_llm_token=None,   # v0.11.2: token级回调 callable(year, token)
) -> BaziChart:
    """一站式八字排盘

    Args:
        name, gender: 命主信息
        year, month, day, hour: 公历出生年月日时
        day_pillar_override: ("壬", "辰") 用 WebSearch 验证值覆盖公式值
        liunian_range: (2023, 2030) 流年扫描范围
        known_events: {年份: "relationship"/"single"/...} 已知事件供校准
        favorable: {"正印","比肩",...} 喜用十神
        calibrate: True=从校准数据库自动加载 known_events

    Returns:
        BaziChart: 完整命盘
    """
    chart = BaziChart.__new__(BaziChart)
    chart.name = name
    chart.gender = gender
    chart.birth_dt = datetime(year, month, day, hour)
    chart.day_pillar_source = "override" if day_pillar_override else "formula"
    chart.favorable_tags = favorable or set()
    chart.warnings = []
    chart.life_stage_override = life_stage_override
    chart._life_stage_override = life_stage_override  # 供 scan_years 内部使用
    chart.family_context = family_context
    chart.hour_confirmed = hour_confirmed

    if not hour_confirmed:
        chart.warnings.append(
            "⚠ 出生时辰未确认（使用默认值）→ 格局判定、大运起运年龄、时柱神煞仅供参考，"
            "可能因时辰偏差而不准。年柱/月柱/日柱及家境分析不受影响。"
        )

    # 校准数据库自动加载
    if calibrate:
        try:
            from .calibration import get_store
            store = get_store()
            if known_events is None:
                known_events = store.get_known_events(name)
            if family_context is None:
                family_context = store.get_family_context(name)
                chart.family_context = family_context
        except Exception:
            chart.warnings.append("校准数据加载失败，跳过已知事件注入")

    # ── 1. 年柱 ──
    y_tg, y_dz, y_w = compute_year_pillar(year, month, day, hour)
    chart.warnings.extend(y_w)
    chart.year = PillarData("年柱", y_tg, y_dz)

    # ── 2. 月柱 ──
    m_tg, m_dz, m_w = compute_month_pillar(y_tg, month, day, hour, gregorian_year=year)
    chart.warnings.extend(m_w)
    chart.month = PillarData("月柱", m_tg, m_dz)

    # ── 3. 日柱 ──
    if day_pillar_override:
        d_tg = Tiangan(day_pillar_override[0])
        d_dz = Dizhi(day_pillar_override[1])
    else:
        d_tg, d_dz, d_w = compute_day_pillar(year, month, day)
        chart.warnings.extend(d_w)
    chart.day = PillarData("日柱", d_tg, d_dz)
    chart.day_master = d_tg

    # ── 4. 时柱 ──
    h_tg, h_dz, h_w, zi_flag = compute_hour_pillar(d_tg, hour)
    chart.warnings.extend(h_w)
    chart.hour = PillarData("时柱", h_tg, h_dz)
    chart.hour_zi_flag = zi_flag

    # ── 5. 藏干 + 纳音 ──
    for pillar in [chart.year, chart.month, chart.day, chart.hour]:
        pillar.hidden_stems = DIZHI_CANGGAN.get(pillar.branch, [])
        pillar.nayin = get_nayin(pillar.stem, pillar.branch)

    # ── 5b. 命宫 + 身宫 + 胎元 ──
    mg_s, mg_b, mg_n = compute_minggong_full(y_tg, m_dz, h_dz)
    chart.minggong_stem = mg_s
    chart.minggong_branch = mg_b
    chart.minggong_nayin = mg_n

    sg_s, sg_b, sg_n = compute_shengong_full(y_tg, m_dz, h_dz)
    chart.shengong_stem = sg_s
    chart.shengong_branch = sg_b
    chart.shengong_nayin = sg_n

    ty_s, ty_b, ty_n = compute_taiyuan(m_tg, m_dz)
    chart.taiyuan_stem = ty_s
    chart.taiyuan_branch = ty_b
    chart.taiyuan_nayin = ty_n

    # ── 5d. 纳音生克链 ──
    try:
        from .nayin_chain import find_all_nayin_relations
        chart.nayin_relations = find_all_nayin_relations(
            chart.year.nayin, chart.month.nayin, chart.day.nayin, chart.hour.nayin,
        )
    except Exception as e:
        chart.warnings.append(f"纳音生克链分析失败: {e}")

    # ── 5c. 用神自动推荐（始终运行以获取强弱数据，用户喜用可补充）──
    try:
        from .yongshen import recommend_yongshen
        all_stems = [chart.year.stem, chart.month.stem, chart.day.stem, chart.hour.stem]
        all_branches = [chart.year.branch, chart.month.branch, chart.day.branch, chart.hour.branch]
        chart._yongshen_result = recommend_yongshen(
            chart.day_master, chart.month.branch, all_stems, all_branches
        )
        # 若用户提供了喜用神，合并覆盖自动推荐
        if favorable:
            chart._yongshen_result["favorable"] = sorted(favorable)
    except Exception as e:
        chart.warnings.append(f"用神推荐失败: {e}")

    # ── 5e. 调候独立分析（陆致极"调候为先"）──
    try:
        from .tiaohou import analyze_tiaohou
        chart.tiaohou_result = analyze_tiaohou(
            chart.day_master, chart.month.branch, chart.day.branch, all_branches,
            all_stems=all_stems,
        ).to_dict()
    except Exception as e:
        chart.warnings.append(f"调候分析失败: {e}")

    # ── 5e. 健康体质画像（v0.10.0: 调候×五行脏腑交叉筛查）──
    chart.health_profile = None
    try:
        from .tiaohou import get_tiaohou_health_profile, get_wuxing_balance_health
        tiaohou_health = get_tiaohou_health_profile(chart.tiaohou_result)
        all_branches_list = list(all_branches) if not isinstance(all_branches, list) else all_branches
        wuxing_risks = get_wuxing_balance_health(all_branches_list, chart.day_master)
        chart.health_profile = {
            "tiaohou_label": tiaohou_health["label"],
            "tiaohou_risks": tiaohou_health["risks"],
            "tiaohou_advice": tiaohou_health["advice"],
            "wuxing_risks": wuxing_risks,
        }
    except Exception as e:
        chart.warnings.append(f"健康画像生成失败: {e}")

    # ── 6. 十神 ──
    for pillar in [chart.year, chart.month, chart.day, chart.hour]:
        if pillar.pillar_type == "日柱":
            pillar.ten_god = None
        else:
            pillar.ten_god = get_ten_god(chart.day_master, pillar.stem)
        pillar.ten_gods_map = {}
        for hs in pillar.hidden_stems:
            pillar.ten_gods_map[hs.stem] = get_ten_god(chart.day_master, hs.stem)

    # ── 7. 格局 ──
    all_stems = [chart.year.stem, chart.month.stem, chart.day.stem, chart.hour.stem]
    cong_ge = (chart._yongshen_result or {}).get("cong_ge")
    chart.pattern, chart.pattern_notes = determine_pattern(
        chart.month.branch, all_stems, chart.day_master, cong_ge=cong_ge
    )

    # 格局用神（陆致极: 格局用神 ≠ 有用之神）
    if chart._yongshen_result:
        try:
            from .yongshen import _get_pattern_yongshen
            pys = _get_pattern_yongshen(chart.pattern, chart.day_master)
            if pys:
                chart._yongshen_result["pattern_yongshen"] = pys
        except Exception:
            pass

    # ── 7b. 藏干虚神 ──
    try:
        from .void_god import find_all_void_gods
        fav = set(chart._yongshen_result.get("favorable", [])) if chart._yongshen_result else None
        chart.void_gods = find_all_void_gods(
            chart.day_master, chart.month.branch, all_stems,
            favorable_shishen=fav,
        )
    except Exception as e:
        chart.warnings.append(f"虚神检测失败: {e}")

    # ── 8. 大运 ──
    chart.dayun_direction_str = dayun_direction(chart.year.stem, gender)
    chart.luck_pillars = generate_luck_pillars(
        chart.month.stem, chart.month.branch, chart.dayun_direction_str
    )
    start_age, remainder, age_w = compute_start_age(
        chart.birth_dt, chart.dayun_direction_str
    )
    chart.warnings.extend(age_w)
    chart.start_age = start_age
    chart.luck_periods = format_luck_periods(start_age, chart.luck_pillars)

    # ── 8b. 大运调制（v0.8.0: 方向二核心，放在luck_pillars赋值之后）──
    chart.dayun_modulations = None
    try:
        from .dayun import DayunModulator
        yongshen_data = chart._yongshen_result or {}
        modulator = DayunModulator(
            day_master=chart.day_master,
            natal_stems=[chart.year.stem, chart.month.stem, chart.day.stem, chart.hour.stem],
            natal_branches=[chart.year.branch, chart.month.branch, chart.day.branch, chart.hour.branch],
            luck_pillars=chart.luck_pillars,
            start_age=start_age,
            favorable_wuxing=set(yongshen_data.get("favorable_wuxing", [])),
            harmful_wuxing=set(yongshen_data.get("harmful_wuxing", [])),
            favorable_shishen=set(yongshen_data.get("favorable", [])),
            harmful_shishen=set(yongshen_data.get("harmful", [])),
        )
        chart.dayun_modulations = [m.to_dict() for m in modulator.modulate()]
    except Exception as e:
        chart.warnings.append(f"大运调制失败: {e}")

    # ── 9. 干支关系 ──
    stem_labels = [
        (chart.year.stem, "年柱"), (chart.month.stem, "月柱"),
        (chart.day.stem, "日柱"), (chart.hour.stem, "时柱"),
    ]
    branch_labels = [
        (chart.year.branch, "年柱"), (chart.month.branch, "月柱"),
        (chart.day.branch, "日柱"), (chart.hour.branch, "时柱"),
    ]
    chart.tiangan_interactions = find_tiangan_wuhe(stem_labels)
    chart.dizhi_interactions = find_all_dizhi_interactions(branch_labels)

    # ── 9b. 贪生忘克（v0.8.0）──
    from .interactions import detect_tansheng_wangke
    chart.tansheng_wangke = [
        {"path": list(gg.path), "cancelled_ke": list(gg.cancelled_ke),
         "bridge": gg.bridge, "note": gg.note}
        for gg in detect_tansheng_wangke(stem_labels, chart.day_master)
    ]

    # ── 9c. 假生陷阱（v0.13.0: 火炎土焦/金多水浊/土重金埋+原3条）──
    try:
        from .tiaohou import detect_false_generation
        false_gens = detect_false_generation(
            chart.day_master,
            [chart.year.stem, chart.month.stem, chart.day.stem, chart.hour.stem],
            all_branches,
        )
        if false_gens:
            chart.false_generations = [
                {"subject": fg.subject, "source": fg.source,
                 "condition": fg.condition, "effect": fg.effect,
                 "severity": fg.severity, "fix_wuxing": fg.fix_wuxing}
                for fg in false_gens
            ]
    except Exception:
        pass

    # ── 10. 神煞 ──
    chart.spirits = find_all_spirits(
        chart.day_master, chart.year.stem,
        chart.year.branch, chart.day.branch,
        branch_labels,
    )

    # ── 11. 流年 ──
    if liunian_range:
        # 构建性格上下文供流年个性化
        p_ctx = None
        try:
            from .liunian import build_personality_context
            yongshen_data = chart._yongshen_result or {}
            p_ctx = build_personality_context(
                day_master=chart.day_master,
                strength=yongshen_data.get("strength", "中和"),
                favorable_shishen=yongshen_data.get("favorable", []),
                harmful_shishen=yongshen_data.get("harmful", []),
                pillars_tengan=[chart.year.stem, chart.month.stem,
                                chart.day.stem, chart.hour.stem],
                gender=gender,
            )
        except Exception:
            chart.warnings.append("性格上下文构建失败，流年将无个性化备注")

        chart.annual_scans = scan_years(
            chart.day_master,
            chart.year.branch,
            chart.day.branch,
            chart.month.branch,
            chart.hour.branch,
            gender,
            start_age,
            chart.luck_pillars,
            chart.birth_dt.date(),
            liunian_range[0],
            liunian_range[1],
            known_events,
            favorable or (set(chart._yongshen_result.get("favorable", [])) if chart._yongshen_result else None),
            personality_ctx=p_ctx,
            life_stage_override=getattr(chart, '_life_stage_override', ''),
            chart_pattern=chart.pattern,
            pillars_tengan=[chart.year.stem, chart.month.stem,
                            chart.day.stem, chart.hour.stem],
            is_fei_ju=chart.tiaohou_result.get("is_fei_ju", False) if chart.tiaohou_result else False,
            tiaohou_climate=chart.tiaohou_result.get("climate", "中和") if chart.tiaohou_result else "中和",
            dayun_modulations=chart.dayun_modulations,
            tansheng_wangke=chart.tansheng_wangke,
            false_generations=chart.false_generations,
            health_profile=chart.health_profile,
            chart_data=_build_llm_context(chart) if os.getenv("BAZI_LLM_REVIEW", "0") == "1" else None,
            on_llm_result=on_llm_result,
            on_llm_token=on_llm_token,
        )

    # ── 11b. 十二长生参断 ──
    if getattr(chart, 'annual_scans', None):
        try:
            from .changsheng_analysis import find_all_changsheng_states
            chart.changsheng_states = find_all_changsheng_states(
                chart.day_master,
                chart.year.branch, chart.month.branch,
                chart.day.branch, chart.hour.branch,
                chart.luck_pillars,
                chart.annual_scans,
            )
        except Exception as e:
            chart.warnings.append(f"十二长生分析失败: {e}")

    # ── 12. 人生阶段判定 ──
    if life_stage_override:
        chart.life_stage = life_stage_override
    else:
        try:
            from .liunian import _life_stage
            today = date.today()
            current_age = today.year - chart.birth_dt.year
            if (today.month, today.day) < (chart.birth_dt.month, chart.birth_dt.day):
                current_age -= 1
            # 当前大运十神
            dayun_idx = max(0, min((current_age - start_age) // 10, len(chart.luck_pillars) - 1))
            current_dn = chart.luck_pillars[dayun_idx] if chart.luck_pillars else (None, None)
            dn_tg_name = get_ten_god(chart.day_master, current_dn[0]).value if current_dn[0] else None
            # 是否有升学信号（仅检查当前年份 ± 1，避免跨年干扰）
            has_xs = False
            if chart.annual_scans:
                for a in chart.annual_scans:
                    if abs(a.year - today.year) <= 1:
                        for e in a.events:
                            if e.category == "升学":
                                has_xs = True
                                break
            chart.life_stage = _life_stage(
                current_age, dayun_ten_god=dn_tg_name,
                pattern=chart.pattern, has_xuesheng_signal=has_xs,
            )
        except Exception:
            # fallback: 纯年龄判断
            chart.warnings.append("智能人生阶段判定失败，降级为纯年龄判断")
            today = date.today()
            current_age = today.year - chart.birth_dt.year
            if (today.month, today.day) < (chart.birth_dt.month, chart.birth_dt.day):
                current_age -= 1
            if current_age < 18:
                chart.life_stage = "中学"
            elif current_age < 22:
                chart.life_stage = "大学"
            elif current_age < 29:
                chart.life_stage = "深造"
            elif current_age < 56:
                chart.life_stage = "职场"
            else:
                chart.life_stage = "晚年"

    # ── 13. 性格与家境分析 ──
    pd = None
    try:
        from .personality_analysis import analyze_family, analyze_personality, build_pillars_data_for_analysis
        pd = build_pillars_data_for_analysis(chart)

        yongshen_data = chart._yongshen_result or {}
        fav_shishen = yongshen_data.get("favorable", [])
        harm_shishen = yongshen_data.get("harmful", [])

        # Compute interactions directly (avoid circular to_dict call)
        _sl = [(chart.year.stem, "年柱"), (chart.month.stem, "月柱"),
               (chart.day.stem, "日柱"), (chart.hour.stem, "时柱")]
        _bl = [(chart.year.branch, "年柱"), (chart.month.branch, "月柱"),
               (chart.day.branch, "日柱"), (chart.hour.branch, "时柱")]
        interactions_dict = {
            "tiangan_wuhe": [w.to_dict() for w in find_tiangan_wuhe(_sl)],
            "dizhi": [d.to_dict() for d in find_all_dizhi_interactions(_bl)],
        }

        # 性格分析
        pr = analyze_personality(
            day_master_stem=chart.day_master.value,
            day_master_wuxing=chart.day_master.wuxing.value,
            day_master_yinyang=chart.day_master.yinyang,
            pattern=chart.pattern,
            strength=yongshen_data.get("strength", "中和"),
            score=yongshen_data.get("score", 0),
            favorable_shishen=fav_shishen,
            harmful_shishen=harm_shishen,
            pillars_data=pd,
            interactions=interactions_dict,
            gender=gender,
        )
        chart.personality_result = pr.to_dict()

        # 格局成格/破格验证
        try:
            from .pattern import validate_pattern
            tiaohou = chart.tiaohou_result or {}
            pattern_val = validate_pattern(
                chart.pattern, chart.day_master, pd,
                harmful_shishen=harm_shishen,
                weighted_scores=pr.weighted_shishen.get("scores", {}),
                strength=yongshen_data.get("strength", "中和"),
                tiaohou_is_fei_ju=tiaohou.get("is_fei_ju", False),
                interactions=interactions_dict,
            )
            chart.personality_result["pattern_validation"] = pattern_val
        except Exception:
            pass

        # 家境分析
        fr = analyze_family(
            day_master_stem=chart.day_master.value,
            day_master_wuxing=chart.day_master.wuxing.value,
            gender=gender,
            strength=yongshen_data.get("strength", "中和"),
            yongshen_result=yongshen_data,
            pillars_data=pd,
            interactions=interactions_dict,
            pattern=chart.pattern,
            family_context=family_context,
        )
        chart.family_result = fr.to_dict()

        # ── LLM 融合引擎 (v0.11.0) ──
        try:
            from .personality_fusion import FUSION_ENABLED
            if FUSION_ENABLED:
                chart.personality_result["_fusion_ready"] = True
        except Exception:
            pass

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        chart.warnings.append(f"性格家境分析失败: {e}\n{tb}")

    # ── 13b. 宫位叠象 ──
    if pd is not None:
        try:
            from .palace_star import analyze_palace_stars
            pd_ps = build_pillars_data_for_analysis(chart)
            chart.palace_star_result = analyze_palace_stars(
                pd_ps, chart.spirits, chart.day_master
            ).to_dict()
        except Exception as e:
            chart.warnings.append(f"宫位叠象分析失败: {e}")

    # ── 13c. 宾主体用 + 墓库应期 ──
    try:
        from .body_use import analyze_body_use
        if pd is not None:
            chart.body_use_result = analyze_body_use(
                pd, interactions_dict, chart.luck_pillars, chart.annual_scans
            ).to_dict()
    except Exception as e:
        chart.warnings.append(f"宾主体用分析失败: {e}")

    return chart
