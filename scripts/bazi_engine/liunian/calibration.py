"""校准规则 — 十神出处 + 性格联动 + 信号合并 + 事件矛盾检查。"""
from .._constants import chong_pair
from ..enums import Dizhi, Tiangan
from .signal import EventSignal
from .utils import _make_prediction

SHISHEN_YEAR_SOURCES = {
    "比肩": (
        "比肩年",
        "《渊海子平·论兄弟姊妹》：「甲木旺相，兄姊争财」— "
        "比肩代表同辈、兄弟、朋友、竞争者。比肩年社交活跃但易有竞争分夺，"
        "合作需谨慎，利益容易被分散。"
    ),
    "劫财": (
        "劫财年",
        "《渊海子平·论妻妾》：「比肩分夺、财临沐浴桃花，主妻妾私通」— "
        "劫财比之比肩争夺性更强，主破财、被借钱、竞争激烈。"
        "男命劫财年注意感情被夺，女命注意闺蜜介入。"
    ),
    "食神": (
        "食神年",
        "《渊海子平·论食神》：「财厚食丰、腹量宽洪、肌体肥大、优游自足、有子息、有寿考」— "
        "食神主享受、口福、才华展现、心宽体胖。食神年心态放松，"
        "适合创作、享受生活，但忌偏印夺食（枭神夺食则福减）。"
    ),
    "伤官": (
        "伤官年",
        "《渊海子平·论伤官》：「伤官见官，为祸百端」「伤官主人多才艺、傲物气高」— "
        "伤官主才华、叛逆、不拘一格、口才出众。伤官年创造力和表达欲强，"
        "但注意言行锋芒，避免与权威冲突。"
    ),
    "正财": (
        "正财年",
        "《渊海子平·论正财》：「大抵吾妻之财也，人之女赉财以事我」— "
        "正财主稳定收入、正妻、务实节俭。正财年适合积累、理财规划，"
        "收入稳定可期。男命正财年正缘运强。"
    ),
    "偏财": (
        "偏财年",
        "《渊海子平》：「偏财，妾也」；《滴天髓·何知章》：「夫论财与论妻之法，可相通也」— "
        "偏财主意外之财、情人、多情慷慨、一掷千金。偏财年消费欲和情感欲望同步增强，"
        "男命异性缘上升，但也容易用情不专。"
    ),
    "正官": (
        "正官年",
        "《渊海子平》：「正气官星者，真君子也，最忌有破」— "
        "正官主事业、名誉、上级、规则约束。正官年适合争取晋升、考试、"
        "建立威信。注意言行合规，忌与上级对抗。"
    ),
    "偏官": (
        "七杀年",
        "《渊海子平·论偏官》：「有制伏则为偏官，无制伏则为七杀」；"
        "「人有偏官，如抱虎而眠，虽借其威足以慑群畜，稍失关防，必为其噬脐」— "
        "七杀主权威、压力、挑战、魄力。有制则化权升职，无制则小人是非。"
        "七杀年压力大但机会也大，关键是'制化'。"
    ),
    "正印": (
        "正印年",
        "《渊海子平》：「生气印绶，利官运畏见财乡」— "
        "正印主学习、贵人、庇护、母亲。正印年适合进修深造、考试考证，"
        "有贵人相助，内心安稳。忌财星来破印。"
    ),
    "偏印": (
        "偏印年",
        "《渊海子平·论食神》：「忌倒食，恐伤其食神」— "
        "偏印（枭神）主偏门学问、孤独思考、洞察力。偏印年适合钻研冷门领域，"
        "但注意人际关系疏离，枭神夺食则福气被打折扣。"
    ),
}

def apply_shishen_year_notes(events: list[EventSignal],
                              shishen_name: str | None) -> None:
    """为所有事件追加流年十神权威出处"""
    if not shishen_name:
        return
    # "七杀" → "偏官" 别名（Shishen 枚举统一用"偏官"）
    lookup_name = "偏官" if shishen_name == "七杀" else shishen_name
    info = SHISHEN_YEAR_SOURCES.get(lookup_name)
    if not info:
        return
    label, source = info
    note_text = f"[{label}] {source}"
    for e in events:
        e.notes.append(note_text)

def apply_personality_notes(events: list[EventSignal],
                            ctx: dict) -> None:
    """为事件追加性格联动备注。只保留有具体行为指引的，删掉空洞安慰和性格吹捧。"""
    for e in events:
        note = ""

        if e.category == "桃花":
            if e.direction == "负面" and ctx.get("introspective"):
                note = "你偏内省，感情波动后建议给自己多一些时间消化，不必急于做决定"
            elif e.direction == "负面":
                note = "感情波动期，注意沟通方式"
            elif e.direction == "正面" and ctx.get("passive_romance"):
                note = "机会出现，但你偏被动——对方可能会先迈出第一步，注意接收信号"
            elif e.direction == "中性" and ctx.get("passive_romance"):
                note = "感情节点期，你倾向于等对方推进——但有时主动一步效果更好"

        elif e.category == "事业":
            if e.direction == "负面" and ctx.get("is_weak"):
                note = "身弱时期事业压力较大，建议优先保稳，不要在这个阶段做冒险决策"

        elif e.category == "财运":
            if e.direction == "负面":
                note = "注意控制消费冲动，这个阶段宜守不宜攻"

        elif e.category == "健康":
            if e.direction == "负面":
                note = "健康信号值得重视，建议规律作息和定期体检"

        elif e.category == "状态":
            if e.direction == "负面" and ctx.get("inner_withdrawn"):
                note = "你容易在低谷时封闭自己——记得找信任的人聊聊，独处太久反而加重"

        elif e.category == "人际":
            if e.direction == "负面" and ctx.get("inner_withdrawn"):
                note = "人际摩擦时你倾向回避——有时直接沟通比沉默更有效"
            elif e.direction == "负面":
                note = "注意言辞分寸，这个阶段的人际冲突宜冷处理"

        if note:
            e.personality_note = note

def _merge_same_category_events(events: list[EventSignal]) -> list[EventSignal]:
    """同类别信号合并：同一年的多个桃花/婚嫁等信号汇总为一条，避免前端重复冗杂。"""
    if len(events) <= 1:
        return events

    groups: dict[str, list[EventSignal]] = {}
    for e in events:
        groups.setdefault(e.category, []).append(e)

    merged: list[EventSignal] = []
    for cat, sigs in groups.items():
        if len(sigs) == 1:
            merged.append(sigs[0])
            continue

        best = max(sigs, key=lambda s: (s.strength, 0))
        all_triggers: list[str] = []
        seen_t = set()
        for s in sigs:
            for t in s.triggers:
                if t not in seen_t:
                    all_triggers.append(t)
                    seen_t.add(t)
        all_notes: list[str] = []
        seen_n = set()
        for s in sigs:
            for n in s.notes:
                if n not in seen_n:
                    all_notes.append(n)
                    seen_n.add(n)
        all_cal_refs: list[str] = []
        seen_c = set()
        for s in sigs:
            for c in s.calibration_refs:
                if c not in seen_c:
                    all_cal_refs.append(c)
                    seen_c.add(c)

        merged.append(EventSignal(
            category=cat,
            direction=best.direction,
            strength=best.strength,
            prediction=_make_prediction(cat, best.direction, best.strength,
                                        all_triggers, all_notes),
            triggers=all_triggers,
            notes=all_notes,
            calibration_refs=all_cal_refs,
            personality_note=best.personality_note,
            magnitude=best.magnitude,
        ))
    return merged

def _check_event_conflicts(events: list[EventSignal],
                          ln_dz: Dizhi, day_branch: Dizhi,
                          day_master: Tiangan, year_branch: Dizhi,
                          month_branch: Dizhi, hour_branch: Dizhi):
    """事件矛盾检查：检测同一年内多个信号之间的冲突，修正强度和方向。

    规则：
    - 桃花+空亡 → 强度-1，"浮桃花不落地"
    - 桃花+冲夫妻宫 → 方向变中性
    - 事业+伤官见官 → 同时输出上升/冲突两面
    - 财+比劫夺财 → 标注社交/感情消费
    - 婚嫁+冲夫妻宫 → 方向变中性
    """
    # 收集事件类别
    cats = {e.category for e in events}
    ev_map = {e.category: e for e in events}

    # 检查流年是否冲夫妻宫（日支）
    chong_fuqi = (ln_dz == chong_pair(day_branch)) if day_branch else False

    # 桃花+冲夫妻宫 → 中性
    if "桃花" in ev_map and chong_fuqi:
        e = ev_map["桃花"]
        if e.direction == "正面":
            e.direction = "中性"
            e.notes.append("流年冲夫妻宫→桃花机会与波动并存，感情节点期")
            if e.strength >= 2:
                e.strength -= 1

    # 婚嫁+冲夫妻宫 → 中性
    if "婚嫁" in ev_map and chong_fuqi:
        e = ev_map["婚嫁"]
        if e.direction == "正面":
            e.direction = "中性"
            e.notes.append("婚年逢冲夫妻宫→婚姻建立可能伴随压力，需沟通")

    # 桃花+财运同时出现 → 感情消费提示
    if "桃花" in cats and "财运" in cats:
        ev_map["桃花"].notes.append("桃花+财运同现→社交和感情消费增加")
        ev_map["财运"].notes.append("财运+桃花同现→部分开支与感情/社交有关")

    # 事业+搬迁同时出现 → 可能是工作地点变动
    if "事业" in cats and "搬迁" in cats:
        ev_map["事业"].notes.append("事业+搬迁同现→工作地点或环境可能变动")
        ev_map["搬迁"].notes.append("搬迁+事业同现→搬家可能与工作/学业有关")

    # 健康+事业同时出现 → 注意工作压力影响健康
    if "健康" in cats and "事业" in cats:
        ev_map["健康"].notes.append("健康+事业同现→工作/学业压力可能影响身体")

    # 桃花负面(分手型) + 婚嫁正面 → 婚嫁降级
    # 仅当桃花负面源于分手信号(冲夫妻宫/卯辰穿)才降级, 竞争型(劫财)不降
    if "桃花" in ev_map and "婚嫁" in ev_map:
        th = ev_map["桃花"]
        hj = ev_map["婚嫁"]
        th_trig = str(th.triggers)
        is_breakup_type = ("冲夫妻宫" in th_trig or "卯辰穿" in th_trig)
        if th.direction == "负面" and hj.direction == "正面" and is_breakup_type:
            hj.direction = "中性"
            hj.strength = max(1, hj.strength - 1)
            hj.notes.append("桃花负面(分手型)+婚嫁正面矛盾→婚期信号存疑")

def _cross_ref_hunjia_taohua(events: list[EventSignal], age: int = 0):
    """婚嫁与桃花共享触发空间（合冲、配偶星、天喜红鸾），一侧≥2★时应补足另一侧。

    规则:
    1. 成人(>21): 桃花≥2★但无婚嫁 → 派生婚嫁信号（星数=桃花-0或2，取低值）
    2. 婚嫁≥2★ → 派生桃花信号（星数=婚嫁-1），婚嫁必有感情机遇
    3. 学生(≤21): 不派生——婚嫁原已降级为桃花，反向不处理
    """
    taohua_evts = [e for e in events if e.category == "桃花"]
    hunjia_evts = [e for e in events if e.category == "婚嫁"]
    max_th = max((e.strength for e in taohua_evts), default=0)
    max_hj = max((e.strength for e in hunjia_evts), default=0)

    # Rule 1: 成人桃花≥2 → 补婚嫁（max_hj<2：婚嫁本身未达到2★才补）
    if age > 21 and max_th >= 2 and max_hj < 2:
        best = max(taohua_evts, key=lambda e: e.strength)
        derived_strength = min(best.strength, 2)
        events.append(EventSignal(
            category="婚嫁",
            direction=best.direction,
            strength=derived_strength,
            triggers=[*best.triggers, "桃花→婚嫁(交叉引用)"],
            notes=[*best.notes, "感情信号较强，成年命主→倾向婚姻/长期关系方向"],
        ))

    # Rule 2: 婚嫁≥2 → 补桃花（仅当无原生桃花≥2★时才补，避免重复）
    if max_hj >= 2 and max_th < 2:
        already_derived = any(
            "婚嫁→桃花" in str(t)
            for e in taohua_evts
            for t in (e.triggers or [])
        )
        if not already_derived:
            best = max(hunjia_evts, key=lambda e: e.strength)
            events.append(EventSignal(
                category="桃花",
                direction=best.direction,
                strength=min(best.strength, 2),
                triggers=[*best.triggers, "婚嫁→桃花(交叉引用)"],
                notes=[*best.notes, "婚嫁信号强→必有感情事件铺垫"],
            ))

