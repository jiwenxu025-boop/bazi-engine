"""主扫描函数 — scan_years() 逐年循环。"""
import logging
from dataclasses import dataclass
from datetime import date

from ..enums import Dizhi, Tiangan
from ..ten_gods import get_ten_god
from .battle import _process_suiyun_clash
from .calibration import (
    _check_event_conflicts,
    _cross_ref_hunjia_taohua,
    _merge_same_category_events,
    apply_personality_notes,
    apply_shishen_year_notes,
)
from .events import (
    detect_banqian_signals,
    detect_caiyun_signals,
    detect_guanfei_signals,
    detect_hunjia_signals,
    detect_jiankang_signals,
    detect_renji_signals,
    detect_shiye_signals,
    detect_taohua_signals,
    detect_xuesheng_signals,
    detect_zhuangtai_signals,
)
from .features import _extract_year_features
from .llm_bridge import (
    _execute_llm_reviews_parallel,
    _execute_llm_reviews_streaming,
)
from .signal import AnnualScan, EventSignal, EvidenceItem
from .utils import (
    _life_stage,
    _make_prediction,
    classify_sb_relation,
    compute_liunian_pillar,
)

logger = logging.getLogger(__name__)


def _attach_default_evidence(
    events: list[EventSignal],
    liunian_label: str,
    dayun_label: str | None = None,
) -> None:
    """给未提供专门证据的规则事件补一条可审计摘要。

    具体组合规则（如三刑、三合）会写入更精确的柱位证据；这里只补
    流年规则的来源和触发摘要，避免事件在 API/LLM 上下文中变成不可追溯
    的自然语言结论。
    """
    for event in events:
        if event.evidence:
            continue
        text = "；".join([*event.triggers[:3], *event.notes[:1]])
        layers = ["流年"]
        pillars = ["流年"]
        if dayun_label and any(keyword in text for keyword in ("大运", "岁运")):
            layers.append("大运")
            pillars.append("大运")
        if any(keyword in text for keyword in ("原局", "日柱", "日支", "夫妻宫", "月柱", "时柱", "年柱")):
            layers.append("原局")
            pillars.append("命局相关柱")
        event.evidence.append(EvidenceItem(
            rule=f"{event.category}_rule",
            layers=tuple(dict.fromkeys(layers)),
            pillars=tuple(dict.fromkeys(pillars)),
            detail=f"{liunian_label}: {text[:220]}" if text else f"{liunian_label}: 规则层事件信号",
        ))


def _rewrite_student_event_language(event: EventSignal) -> None:
    """把事业规则的触发语义翻译成学生可用的学业场景。"""
    replacements = (
        ("主动跳槽/创业", "主动调整学习方向/竞赛项目"),
        ("跳槽/创业", "学习方向/竞赛项目调整"),
        ("跳槽", "学习方向调整"),
        ("创业", "竞赛或项目尝试"),
        ("离职风险", "转专业/换导师风险"),
        ("离职", "退出项目或学习方向调整"),
        ("晋升机会", "升学/竞赛机会"),
        ("工作地点", "学习环境"),
        ("工作有", "学习安排有"),
        ("工作", "学习"),
        ("职场", "校园"),
    )

    def rewrite(text: str) -> str:
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    event.triggers = [rewrite(item) for item in event.triggers]
    event.notes = [rewrite(item) for item in event.notes]
    event.evidence = [
        EvidenceItem(
            rule=item.rule,
            layers=item.layers,
            pillars=item.pillars,
            relation=item.relation,
            detail=rewrite(item.detail),
            effect=item.effect,
        ) if isinstance(item, EvidenceItem) else item
        for item in event.evidence
    ]


def _adapt_life_stage_events(
    events: list[EventSignal], stage_for_year: str, age: int,
) -> None:
    """统一处理阶段重命名和对应的当代语义。"""
    for event in events:
        if stage_for_year in ("职场", "晚年") and event.category == "升学":
            event.category = "进修"
        elif stage_for_year in ("中学", "大学", "深造") and event.category == "事业":
            event.category = "学业"
        if event.category == "学业":
            _rewrite_student_event_language(event)
            event.prediction = _make_prediction(
                "事业", event.direction, event.strength,
                event.triggers, event.notes, age=age, life_stage=stage_for_year,
            )


def build_personality_context(day_master: Tiangan, strength: str,
                              favorable_shishen: list[str],
                              harmful_shishen: list[str],
                              pillars_tengan: list[Tiangan],
                              gender: str) -> dict:
    """从命盘数据提取性格关键指标，供流年事件个性化用"""
    ctx = {}

    # 身强弱
    ctx["is_strong"] = "强" in strength
    ctx["is_weak"] = "弱" in strength
    ctx["gender"] = gender

    # 是否有正财/正官合日主 → 感情被动
    from .._constants import TIANGAN_WUHE
    ctx["passive_romance"] = False
    for tg in pillars_tengan:
        pair = (day_master, tg)
        if pair in TIANGAN_WUHE or (tg, day_master) in TIANGAN_WUHE:
            from ..ten_gods import get_ten_god
            g = get_ten_god(day_master, tg)
            if g and g.value in ("正财", "正官"):
                ctx["passive_romance"] = True
                break

    # 七杀旺 + 有制 → 果断恢复型
    ctx["resilient"] = False
    if "偏官" in favorable_shishen or "七杀" in favorable_shishen:
        ctx["resilient"] = True

    # 偏印忌神 → 内心疏离
    ctx["inner_withdrawn"] = "偏印" in harmful_shishen

    # 食伤旺 → 外放表达型
    ctx["expressive"] = ("食神" in favorable_shishen or
                         "伤官" in favorable_shishen)

    # 印星旺 → 内敛思考型
    ctx["introspective"] = ("正印" in favorable_shishen or
                            "偏印" in favorable_shishen)

    return ctx

def _annotate_taohua_clusters(results: list[AnnualScan]) -> list[AnnualScan]:
    """v0.11.1: 扫描后聚类——识别连续桃花年，标注首发年和延续年。

    逻辑：
    - 连续≥2年出现正面桃花信号 → 形成"桃花簇"
    - 簇中第一年标记为"最可能脱单/关系开始的年份"
    - 簇中后续年份标记为"关系内事件（升温/危机/里程碑），非新恋情"
    - 如果引擎已在运行时通过 relationship_state 做了标注，此处做补充校验
    """
    # 找出所有有正面桃花的年份
    positive_years: list[int] = []
    for r in results:
        taohua_events = [e for e in r.events if e.category == "桃花" and e.direction == "正面"]
        if taohua_events:
            positive_years.append(r.year)

    if len(positive_years) < 2:
        return results

    # 识别连续簇（间隔≤1年视为同一簇）
    clusters: list[list[int]] = []
    current_cluster = [positive_years[0]]
    for i in range(1, len(positive_years)):
        if positive_years[i] - positive_years[i-1] <= 1:
            current_cluster.append(positive_years[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [positive_years[i]]
    clusters.append(current_cluster)

    # 为每个簇的首发年和后续年添加注记
    year_to_note: dict[int, str] = {}
    for cluster in clusters:
        if len(cluster) >= 2:
            first_year = cluster[0]
            year_to_note[first_year] = (
                f"连续{len(cluster)}年桃花簇首发年→最可能是感情开始的年份"
            )
            for y in cluster[1:]:
                year_to_note[y] = (
                    f"桃花簇第{cluster.index(y)+1}年→若已脱单则为关系内深化/升温，非新恋情；"
                    f"若仍单身则信号可能虚浮（首发年{first_year}未兑现时）"
                )

    # 将注记添加到对应年份的桃花事件中
    for r in results:
        if r.year in year_to_note:
            for e in r.events:
                if e.category == "桃花" and e.direction == "正面" and year_to_note[r.year] not in str(e.notes):
                    # 避免重复添加
                    e.notes.insert(0, year_to_note[r.year])

    return results


@dataclass
class ScanConfig:
    """流年扫描配置 — scan_years 的参数封装"""
    day_master: Tiangan
    year_branch: Dizhi
    day_branch: Dizhi
    month_branch: Dizhi
    hour_branch: Dizhi
    gender: str
    start_age: int
    luck_pillars: list[tuple[Tiangan, Dizhi]]
    birth_date: date
    start_year: int
    end_year: int
    start_age_exact: float | None = None
    known_events: dict[int, str] | None = None
    favorable: set[str] | None = None
    personality_ctx: dict | None = None
    life_stage_override: str = ""
    chart_pattern: str = ""
    pillars_tengan: list[Tiangan] | None = None
    is_fei_ju: bool = False
    tiaohou_climate: str = "中和"
    dayun_modulations: list[dict] | None = None
    tansheng_wangke: list[dict] | None = None
    false_generations: list[dict] | None = None
    health_profile: dict | None = None
    chart_data: dict | None = None
    on_llm_result=None
    on_llm_token=None
    defer_llm: bool = False
    llm_tasks_out: list[tuple[int, dict]] | None = None


def scan_years_from_config(config: ScanConfig) -> list[AnnualScan]:
    """从 ScanConfig 调用 scan_years (解包后传入)"""
    return scan_years(
        config.day_master, config.year_branch, config.day_branch,
        config.month_branch, config.hour_branch, config.gender,
        config.start_age, config.luck_pillars, config.birth_date,
        config.start_year, config.end_year,
        known_events=config.known_events,
        favorable=config.favorable,
        personality_ctx=config.personality_ctx,
        life_stage_override=config.life_stage_override,
        chart_pattern=config.chart_pattern,
        pillars_tengan=config.pillars_tengan,
        is_fei_ju=config.is_fei_ju,
        tiaohou_climate=config.tiaohou_climate,
        dayun_modulations=config.dayun_modulations,
        tansheng_wangke=config.tansheng_wangke,
        false_generations=config.false_generations,
        health_profile=config.health_profile,
        chart_data=config.chart_data,
        on_llm_result=config.on_llm_result,
        on_llm_token=config.on_llm_token,
        defer_llm=config.defer_llm,
        llm_tasks_out=config.llm_tasks_out,
        start_age_exact=config.start_age_exact,
    )


def scan_years(
    day_master: Tiangan,
    year_branch: Dizhi,
    day_branch: Dizhi,
    month_branch: Dizhi,
    hour_branch: Dizhi,
    gender: str,
    start_age: int,
    luck_pillars: list[tuple[Tiangan, Dizhi]],
    birth_date: date,
    start_year: int,
    end_year: int,
    known_events: dict[int, str] | None = None,
    favorable: set[str] | None = None,
    personality_ctx: dict | None = None,
    life_stage_override: str = "",
    chart_pattern: str = "",
    pillars_tengan: list[Tiangan] | None = None,
    is_fei_ju: bool = False,
    tiaohou_climate: str = "中和",
    dayun_modulations: list[dict] | None = None,
    tansheng_wangke: list[dict] | None = None,
    false_generations: list[dict] | None = None,
    health_profile: dict | None = None,
    chart_data: dict | None = None,
    on_llm_result=None,  # v0.11.1: 流式回调 callable(year, llm_events)
    on_llm_token=None,   # v0.11.2: token级回调 callable(year, token)
    start_age_exact: float | None = None,
    defer_llm: bool = False,
    llm_tasks_out: list[tuple[int, dict]] | None = None,
) -> list[AnnualScan]:
    """逐年扫描，返回每年所有事件信号

    known_events: {year: "relationship"/"single"} — 该年已知的感情状态
    favorable: {"正印","比肩",...} — 日主喜用十神集合，None=不判断喜忌
    is_fei_ju: 调候废局标志（v0.8.0: 废局→所有信号降1星）
    tiaohou_climate: 调候气候类型（v0.8.0: 大燥/大寒→信号额外压制）
    dayun_modulations: 大运调制结果列表（v0.8.0: 方向二—基线偏移+主题加权+岁运交战）
    tansheng_wangke: 贪生忘克结果（v0.8.0: 七杀/伤官攻击日主时若有通关→减凶）
    """
    results: list[AnnualScan] = []

    logger.debug(
        "llm review setup chart_data=%s callback=%s",
        bool(chart_data),
        on_llm_result is not None,
    )

    # 检测命局是否有伤官见官
    has_natal_shangguan = False
    if pillars_tengan:
        natal_stems_shishen = [get_ten_god(day_master, s) for s in pillars_tengan if s != day_master]
        has_shang = any(ss and ss.value == "伤官" for ss in natal_stems_shishen)
        has_guan = any(ss and ss.value in ("正官", "偏官") for ss in natal_stems_shishen)
        has_natal_shangguan = has_shang and has_guan

    # 将 known_events 转换为按年存储的"进入该年时是否恋爱中"
    known_rel: dict[int, bool] = {}
    if known_events:
        for y, status in known_events.items():
            known_rel[int(y)] = (status == "relationship")
    prev_year_rel = False
    relationship_state = "single"  # v0.11.1: 跨年关系状态机 single/dating/married
    llm_tasks: list[tuple[int, dict]] = []  # v0.11.1: (result_index, review_context) 延迟并行执行

    for year in range(start_year, end_year + 1):
        ln_tg, ln_dz = compute_liunian_pillar(year)

        # 确定当前大运。年度扫描不能把交运前或交运中的整年强行套入第一步大运。
        age = year - birth_date.year
        effective_start_age = float(start_age if start_age_exact is None else start_age_exact)
        year_start_age = (date(year, 1, 1) - birth_date).days / 365.2425
        year_end_age = (date(year, 12, 31) - birth_date).days / 365.2425
        dayun_idx: int | None = None
        if not luck_pillars or year_end_age < effective_start_age:
            dn_tg, dn_dz = None, None
            dn_weight_note = "未交大运（童限/小运另列），不强行套用第一步大运"
        elif year_start_age < effective_start_age <= year_end_age:
            dn_tg, dn_dz = None, None
            dn_weight_note = "本年交运，大运前后分段；年度扫描不单列大运干支"
        else:
            start_idx = int((year_start_age - effective_start_age) // 10)
            end_idx = int((year_end_age - effective_start_age) // 10)
            if start_idx != end_idx:
                dn_tg, dn_dz = None, None
                dn_weight_note = "本年换运，大运前后分段；年度扫描不单列大运干支"
            else:
                dayun_idx = max(0, min(start_idx, len(luck_pillars) - 1))
                dn_tg, dn_dz = luck_pillars[dayun_idx]

        # 流年干支分论: 权重分配
        sb_rel, sb_sw, sb_bw = classify_sb_relation(ln_tg, ln_dz)

        # 大运与流年关系的工程说明，不使用古籍化的固定百分比。
        if dn_dz:
            dn_weight_note = (
                f"工程提示：大运{dn_tg.value}{dn_dz.value}与流年{ln_tg.value}{ln_dz.value}共同参照；"
                "不使用固定百分比断语"
            )
        elif not dn_weight_note:
            dn_weight_note = "大运未定，流年干支并重"

        # 已知事件状态：前一年是否恋爱中（校准数据按年存储的是"该年状态"）
        if (year - 1) in known_rel:
            prev_year_rel = known_rel[year - 1]

        # 检测七类事件
        events: list[EventSignal] = []
        events.extend(detect_taohua_signals(
            ln_tg, ln_dz, year_branch, day_branch, day_master, gender,
            dn_tg, dn_dz, prev_year_rel, favorable,
            (year_branch, month_branch, day_branch, hour_branch),
        ))
        events.extend(detect_xuesheng_signals(
            ln_tg, ln_dz, day_branch, day_master, year_branch, month_branch, hour_branch, favorable,
        ))
        events.extend(detect_hunjia_signals(
            ln_tg, ln_dz, day_branch, day_master, year_branch, gender, favorable, dn_dz, age,
            (year_branch, month_branch, day_branch, hour_branch),
        ))
        events.extend(detect_shiye_signals(
            ln_tg, ln_dz, day_master, year_branch, month_branch, day_branch,
            hour_branch, dn_tg, dn_dz, favorable,
        ))
        events.extend(detect_caiyun_signals(
            ln_tg, ln_dz, day_master, year_branch, day_branch, favorable,
            (year_branch, month_branch, day_branch, hour_branch),
        ))
        events.extend(detect_jiankang_signals(
            ln_tg, ln_dz, day_branch, day_master, year_branch, dn_tg, dn_dz, favorable,
            (year_branch, month_branch, day_branch, hour_branch),
            health_profile=health_profile,
            first_year=(year == start_year),
        ))
        events.extend(detect_banqian_signals(
            ln_dz, year_branch, day_branch, month_branch, hour_branch, dn_dz,
            dn_tg, ln_tg, day_master, favorable,
        ))
        events.extend(detect_zhuangtai_signals(
            ln_tg, ln_dz, day_master, day_branch, dn_tg, dn_dz, favorable,
        ))
        events.extend(detect_renji_signals(
            ln_tg, ln_dz, year_branch, month_branch, day_branch, hour_branch,
            day_master,
            (year_branch, month_branch, day_branch, hour_branch),
            favorable,
            dayun_branch=dn_dz,
        ))
        events.extend(detect_guanfei_signals(
            ln_tg, ln_dz, day_master, day_branch,
            year_branch, month_branch, hour_branch,
            dn_tg, dn_dz,
            natal_shang_guan=has_natal_shangguan,
            pillars_tengan=pillars_tengan,
        ))

        _attach_default_evidence(
            events,
            liunian_label=f"{ln_tg.value}{ln_dz.value}",
            dayun_label=f"{dn_tg.value}{dn_dz.value}" if dn_tg and dn_dz else None,
        )

        # 流年十神权威出处
        ln_shishen_name = get_ten_god(day_master, ln_tg)
        ln_shishen_val = ln_shishen_name.value if ln_shishen_name else None
        if ln_shishen_val:
            apply_shishen_year_notes(events, ln_shishen_val)

        # 财星流年联动：同时有桃花+财运信号时，加欲望消费提示
        has_taohua = any(e.category == "桃花" for e in events)
        has_caiyun = any(e.category == "财运" for e in events)
        is_caixing_year = ln_shishen_val in ("正财", "偏财")

        if is_caixing_year:
            for e in events:
                if e.category == "桃花":
                    e.notes.append(f"{ln_shishen_val}年→情感欲望增强，对异性的关注度上升")
                if e.category == "财运":
                    e.notes.append(f"{ln_shishen_val}年→消费欲增加，可能为感情/社交花钱")
            if has_taohua and has_caiyun:
                for e in events:
                    if e.category == "桃花" or e.category == "财运":
                        e.notes.append(f"{ln_shishen_val}年桃花+财运同现→钱和情的欲望同步放大，注意为感情消费")

        # 注入性格联动备注
        if personality_ctx:
            apply_personality_notes(events, personality_ctx)

        # 人生阶段适配：学生时期修正事业/财运措辞
        if life_stage_override:
            stage_for_year = life_stage_override
        else:
            # 智能判断：年龄 + 大运十神 + 格局 + 升学信号
            # 计算大运天干的十神（相对于日主），而非传天干本身
            dn_shishen = get_ten_god(day_master, dn_tg) if dn_tg else None
            dn_tg_name = dn_shishen.value if dn_shishen else None
            has_xs = any(e.category == "升学" for e in events)
            stage_for_year = _life_stage(
                age, dayun_ten_god=dn_tg_name,
                pattern=chart_pattern, has_xuesheng_signal=has_xs
            )

        for e in events:
            e.prediction = _make_prediction(
                e.category, e.direction, e.strength,
                e.triggers, e.notes, age=age,
                life_stage=stage_for_year,
            )

        # 人生阶段适配：先处理基础事件，后置规则追加事件时会再处理一次。
        _adapt_life_stage_events(events, stage_for_year, age)

        # ── 事件矛盾检查 + 融合 ──
        _check_event_conflicts(events, ln_dz, day_branch, day_master,
                               year_branch, month_branch, hour_branch)

        # ── 婚嫁↔桃花交叉引用（v0.9.1: 两者共享触发空间，一侧≥2★时补足另一侧）──
        _cross_ref_hunjia_taohua(events, age)

        # ── 同柱隔离带调制（v0.8.0: 盖头/截脚→流年干支内部消耗，信号打折）──
        # 截脚破坏权重 > 盖头（《滴天髓》：截脚者地克天，根基不稳）
        # 仅降低最高烈度信号（≥3★），中等信号（2★）不受影响
        if sb_rel == "截脚":
            for e in events:
                if e.strength >= 3:
                    e.strength -= 1
                    e.notes.append(f"流年{sb_rel}({ln_tg.value}{ln_dz.value})→地支反克天干，内力消耗，高烈度事件打折")
        elif sb_rel == "盖头":
            for e in events:
                if e.strength >= 3:
                    e.strength -= 1
                    e.notes.append(f"流年{sb_rel}({ln_tg.value}{ln_dz.value})→天干压制地支，能量内耗，高烈度事件概率降低")

        # ── 调候废局降权（v0.8.0: 仅压制最高烈度，中等信号保留）──
        # 废局 + 极端气候合并处理：最多降1星，不重复
        tiaohou_severe = is_fei_ju and tiaohou_climate in ("大燥", "大寒")
        if is_fei_ju:
            for e in events:
                if e.strength >= 3:
                    e.strength -= 1
                    e.notes.append("⚠ 命局为调候废局：格局难发挥，高烈度事件打折（陆致极「失去调候为废局」）")
                    if tiaohou_severe:
                        e.notes.append(f"气候{tiaohou_climate}→环境极端，事件发挥进一步受限")
                elif e.strength == 2:
                    e.notes.append("调候废局：信号可信度打折扣，实际体验可能低于预期")
                elif e.strength == 1:
                    e.notes.append("调候废局：弱信号可信度降低")

        # ── 大运调制（v0.8.0: 方向二—基线偏移 + 主题加权）──
        current_dayun_mod = None
        if dayun_modulations and dayun_idx is not None:
            current_dayun_mod = next(
                (mod for mod in dayun_modulations if mod.get("period_index") == dayun_idx),
                None,
            )

        if current_dayun_mod:
            baseline = current_dayun_mod.get("baseline_offset", 0)
            theme = current_dayun_mod.get("theme", "")
            theme_w = current_dayun_mod.get("theme_weight", 1.0)

            # 基线偏移: 吉运+1星, 凶运-1星（仅影响≥2★的信号）
            # v0.9.1: 桃花/婚嫁免于凶运正面打压——方向判断常有歧义，不因大运基调降级
            if baseline != 0:
                for e in events:
                    if baseline > 0 and e.direction == "正面" and e.strength >= 2:
                        e.strength = min(3, e.strength + 1)
                        e.notes.append("大运吉调：十年基调偏吉，正面事件放大")
                    elif baseline < 0 and e.direction == "负面" and e.strength >= 2:
                        e.strength = min(3, e.strength + 1)
                        e.notes.append("大运凶调：十年基调偏凶，负面事件放大")
                    elif baseline < 0 and e.direction == "正面" and e.strength >= 2:
                        if e.category in ("桃花", "婚嫁"):
                            e.notes.append("大运凶调：婚恋事件在凶运中需谨慎辨别，但机会本身仍存在")
                        else:
                            e.strength = max(1, e.strength - 1)
                            e.notes.append("大运凶调：不幸之运，吉事打折扣")

            # 主题加权: 大运主题与流年事件一致时加权
            if theme and theme_w != 1.0:
                theme_event_map = {
                    "财运": "财运",
                    "官运": "事业",
                    "印运": "升学",
                    "食伤运": "事业",
                    "比劫运": "人际",
                }
                boosted_category = theme_event_map.get(theme, "")
                for e in events:
                    if boosted_category and e.category == boosted_category:
                        if theme_w > 1.0 and e.strength >= 2:
                            e.strength = min(3, e.strength + 1)
                            e.notes.append(f"大运主题'{theme}'共振→{e.category}信号增强")
                        elif theme_w < 1.0 and e.strength >= 2:
                            e.strength = max(1, e.strength - 1)
                            e.notes.append(f"大运主题偏移→{e.category}非此运重点，信号减弱")

        # ── 岁运交战处理器（v0.8.0: P6—流年vs大运优先级拦截）──
        if dn_tg and dn_dz:
            sui_yun_signals = _process_suiyun_clash(ln_tg, ln_dz, dn_tg, dn_dz,
                                                     day_master, current_dayun_mod)
            if sui_yun_signals:
                events.extend(sui_yun_signals)
                has_conflict = any(
                    any(
                        marker in trigger
                        for marker in ("天战", "地战", "刑大运", "害大运")
                    )
                    for signal in sui_yun_signals
                    for trigger in signal.triggers
                )
                if has_conflict:
                    # v0.11.1: 岁运交战分方向处理——动荡加剧≠信号变弱
                    # 吉事打折(动荡中好事难落实)，凶事加码(动荡中坏事更易发生)
                    is_dizhan = any("地战" in str(s.triggers) for s in sui_yun_signals)
                    for e in events:
                        if e.category == "健康":
                            continue
                        if e.direction == "正面":
                            if is_dizhan:
                                e.notes.append("⚠ 岁运地战→根基动摇，好事打折，宜守不宜攻")
                            else:
                                e.notes.append("⚠ 岁运交战→吉事可信度下降，好事可能落空或附带代价")
                        elif e.direction == "负面":
                            if is_dizhan:
                                e.notes.append("⚠ 岁运地战→根基动摇，坏事加剧，重大决策暂缓")
                            else:
                                e.notes.append("⚠ 岁运交战→动荡加剧，负面事件更易坐实，不可轻视")
                        else:
                            e.notes.append("⚠ 岁运交战→波动大、变数多，中性事件偏负面方向倾斜")

        # 岁运交战可能追加事业事件；在 LLM 收集上下文前统一转换场景。
        _adapt_life_stage_events(events, stage_for_year, age)

        # ── LLM 推理层（v0.11.1: 延迟到循环结束后并行执行）──
        if chart_data:
            try:
                from ..llm_review import DEEPSEEK_KEY, LLM_REVIEW_ENABLED, build_review_context, should_invoke_llm
                yr_features = _extract_year_features(
                    ln_tg, ln_dz, year_branch, day_branch, day_master,
                    gender, dn_tg, dn_dz,
                )
                personality_text = chart_data.get("personality", {}).get("profile", "")
                # 判断是否需要 LLM，需要则收集上下文（不立即调用）
                llm_ok = should_invoke_llm(events, year, age)
                if year == start_year:
                    logger.debug(
                        "llm review enabled=%s key_configured=%s age=%s",
                        LLM_REVIEW_ENABLED,
                        bool(DEEPSEEK_KEY),
                        age,
                    )
                if llm_ok:
                    review_ctx = build_review_context(
                        chart_data, year, age,
                        ln_tg.value, ln_dz.value,
                        dn_tg.value if dn_tg else None,
                        dn_dz.value if dn_dz else None,
                        events, current_dayun_mod, tansheng_wangke,
                        false_generations=false_generations,
                        year_features=yr_features,
                        personality_text=personality_text,
                    )
                    llm_tasks.append((len(results), review_ctx))
            except Exception as error:
                logger.warning(
                    "llm review context failed year=%s type=%s",
                    year,
                    type(error).__name__,
                )

        # ── 贪生忘克化解（v0.8.0: P7—七杀/伤官攻击日主若有通关→减凶）──
        if tansheng_wangke:
            dm_protected = any(
                gg.get("cancelled_ke") and
                (day_master and day_master.value == gg["cancelled_ke"][1])
                for gg in tansheng_wangke
            )
            if dm_protected:
                for e in events:
                    # 健康: 七杀攻身信号降级
                    if e.category == "健康":
                        sha_triggers = [t for t in e.triggers if "七杀" in t or "偏官" in t]
                        if sha_triggers and e.strength >= 2:
                            e.strength -= 1
                            e.notes.append("贪生忘克化解：杀印相生→压力转化动力，七杀凶性大减")
                    # 事业: 官杀混杂信号降级
                    if e.category == "事业":
                        guansha_triggers = [t for t in e.triggers if "官杀混杂" in t]
                        if guansha_triggers and e.strength >= 2:
                            e.strength -= 1
                            e.notes.append("贪生忘克化解：印星通关→官杀混杂压力可控")
                    # 女命伤官见官 → 有印制伤则减凶
                    if e.category in ("桃花", "婚嫁") and gender == "女":
                        shang_triggers = [t for t in e.triggers if "伤官" in t]
                        if shang_triggers:
                            e.notes.append("贪生忘克提示：若有印星通关，伤官克官之凶可减")

        _attach_default_evidence(
            events,
            liunian_label=f"{ln_tg.value}{ln_dz.value}",
            dayun_label=f"{dn_tg.value}{dn_dz.value}" if dn_tg and dn_dz else None,
        )

        # 合并同类别信号（同类多触发源→汇总为一条）
        events = _merge_same_category_events(events)

        results.append(AnnualScan(
            year=year,
            liunian_stem=ln_tg,
            liunian_branch=ln_dz,
            dayun_stem=dn_tg,
            dayun_branch=dn_dz,
            events=events,
            age=age,
            sb_relation=sb_rel,
            stem_weight=sb_sw,
            branch_weight=sb_bw,
            dayun_weight_note=dn_weight_note,
        ))

        # ── v0.11.1: 跨年关系状态机更新 ──
        taohua_sigs = [e for e in events if e.category == "桃花"]
        hunjia_sigs = [e for e in events if e.category == "婚嫁"]
        prev_year_rel = any(e.strength >= 2 for e in taohua_sigs)

        # 状态转换
        if relationship_state == "single":
            # 单身→恋爱：桃花≥3★正面 或 婚嫁信号
            has_strong_positive = any(
                e.strength >= 3 and e.direction == "正面"
                for e in taohua_sigs
            )
            has_hunjia = any(e.strength >= 2 for e in hunjia_sigs)
            if has_strong_positive or has_hunjia:
                relationship_state = "dating"
        elif relationship_state == "dating":
            # 恋爱→分手：负面桃花≥2★ 且有其他明确风险信号；日支六冲本身不定方向。
            has_breakup = any(
                e.direction == "负面" and e.strength >= 2 and
                any("劫财" in str(t) or "伤官克官" in str(t)
                    for t in e.triggers)
                for e in taohua_sigs
            )
            if has_breakup:
                relationship_state = "single"
            # 恋爱→已婚：婚嫁信号≥3★（未分手才可能结婚）
            elif any(e.strength >= 3 for e in hunjia_sigs):
                relationship_state = "married"
        # married→single: 婚嫁负面信号（离婚）
        elif relationship_state == "married":
            has_divorce = any(
                e.direction == "负面" and e.strength >= 3 and
                any("伤官" in str(t) for t in e.triggers)
                for e in hunjia_sigs + taohua_sigs
            )
            if has_divorce:
                relationship_state = "single"

    # ── v0.11.1: LLM审查并行执行（循环中收集，此处并行发射）──
    if llm_tasks and defer_llm:
        if llm_tasks_out is not None:
            llm_tasks_out.extend(llm_tasks)
        logger.debug("deferred llm reviews count=%s", len(llm_tasks))
    elif llm_tasks:
        logger.debug("executing llm reviews count=%s", len(llm_tasks))
        if on_llm_result is not None:
            # 流式模式：逐个回调（含token级逐字推送）
            _execute_llm_reviews_streaming(results, llm_tasks, on_llm_result, on_llm_token)
        else:
            _execute_llm_reviews_parallel(results, llm_tasks)
    else:
        logger.debug("no llm review tasks collected")

    # ── v0.15.2: 婚嫁回溯—强信号前一年检测前奏 ──
    results = _backtrack_hunjia_prelude(results)

    # ── v0.11.1: 扫描后聚类处理—标注连续桃花年的"首发年" ──
    results = _annotate_taohua_clusters(results)

    return results


def _backtrack_hunjia_prelude(results: list[AnnualScan]) -> list[AnnualScan]:
    """婚嫁 ±1 年回溯：强婚嫁信号（≥3★）出现时，检查前一年是否有前奏信号。

    如果有但不触发婚嫁，将前一年标注为"婚嫁前奏年"。
    校准数据中 4/22 婚嫁案例偏差 ±1 年，此逻辑可覆盖。
    """
    for i in range(1, len(results)):
        prev_scan = results[i - 1]
        curr_scan = results[i]

        # 当前年有强婚嫁信号
        has_strong_hunjia = any(
            e.category == "婚嫁" and e.strength >= 3
            for e in curr_scan.events
        )
        if not has_strong_hunjia:
            continue

        # 前一年检查前奏信号
        prelude_triggers = []
        for e in prev_scan.events:
            if e.category == "桃花" and e.strength >= 2:
                prelude_triggers.append(f"桃花★{e.strength}")
            elif e.category == "婚嫁" and e.strength == 1:
                prelude_triggers.append("婚嫁弱信号")

        if prelude_triggers:
            prev_scan.events.append(EventSignal(
                category="婚嫁",
                direction="正面",
                strength=1,
                prediction="婚嫁前奏年——强信号出现在次年，本年已开始酝酿",
                triggers=prelude_triggers,
                notes=[f"次年{curr_scan.year}年有≥3★婚嫁信号，本年出现前奏: {'; '.join(prelude_triggers)}"],
                evidence=[EvidenceItem(
                    rule="hunjia_prelude",
                    layers=("前一年", "流年"),
                    pillars=("前一年", "流年"),
                    relation="时点回溯",
                    detail=f"次年{curr_scan.year}年强婚嫁信号；前一年触发: {'; '.join(prelude_triggers)}",
                )],
            ))

    return results

