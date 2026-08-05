"""校准规则 — 十神出处 + 性格联动 + 信号合并 + 事件矛盾检查。"""
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
    """停用未逐句核验的十神引文自动注入。

    ``SHISHEN_YEAR_SOURCES`` 作为待审历史资料保留，不能把其中的项目释义或
    未核对版本的引文附加到用户事件输出。待完成版本、篇章与原文核验后，才可按
    ``古籍摘要`` 的来源等级重新启用。
    """
    del events, shishen_name

def apply_personality_notes(events: list[EventSignal],
                            ctx: dict) -> None:
    """追加不依赖人格推断的现实核对建议。"""
    del ctx
    for e in events:
        note = ""

        if e.category == "桃花":
            if e.direction == "负面":
                note = "如现实中出现关系压力，可先核对沟通、边界和双方意愿"

        elif e.category == "事业":
            if e.direction == "负面":
                note = "如现实中工作或学业压力增加，先核对任务、资源和可调整事项"

        elif e.category == "财运":
            if e.direction == "负面":
                note = "以实际预算、账单和合同为准，不仅凭该信号作财务决定"

        elif e.category == "健康":
            if e.direction == "负面":
                note = "仅作作息与安全提醒；如有不适，请以专业医疗意见为准"

        elif e.category == "状态":
            if e.direction == "负面":
                note = "如现实压力持续影响生活，可向可信任的人或专业人士寻求支持"

        elif e.category == "人际" and e.direction == "负面":
            note = "如现实中出现分歧，可核对信息、边界和沟通方式"

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

        all_evidence = []
        seen_evidence = set()
        all_conflicts: list[str] = []
        seen_conflicts = set()
        for s in sigs:
            for item in s.evidence:
                key = repr(item.to_dict() if hasattr(item, "to_dict") else item)
                if key not in seen_evidence:
                    all_evidence.append(item)
                    seen_evidence.add(key)
            for conflict in s.conflicts:
                if conflict not in seen_conflicts:
                    all_conflicts.append(conflict)
                    seen_conflicts.add(conflict)

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
            evidence=all_evidence,
            conflicts=all_conflicts,
        ))
    return merged

def _check_event_conflicts(events: list[EventSignal],
                          ln_dz: Dizhi, day_branch: Dizhi,
                          day_master: Tiangan, year_branch: Dizhi,
                          month_branch: Dizhi, hour_branch: Dizhi):
    """事件矛盾检查：检测同一年内多个信号之间的冲突，修正强度和方向。

    规则：
    - 桃花+空亡只保留结构备注，不自动降低强度
    - 事业+伤官见官 → 同时输出上升/冲突两面
    - 财+比劫夺财 → 标注社交/感情消费
    - 日支六冲只作结构提示，不自动改变方向
    """
    # 收集事件类别
    cats = {e.category for e in events}
    ev_map = {e.category: e for e in events}

    # 桃花+财运同时出现只说明两个主题同年出现，不能推断消费动机。
    if "桃花" in cats and "财运" in cats:
        shared_note = "桃花与财运信号同现，分别核对关系互动和实际收支，不推断两者存在因果"
        ev_map["桃花"].notes.append(shared_note)
        ev_map["财运"].notes.append(shared_note)

    # 事业+搬迁同时出现 → 可能是工作地点变动
    if "事业" in cats and "搬迁" in cats:
        ev_map["事业"].notes.append("事业+搬迁同现→工作地点或环境可能变动")
        ev_map["搬迁"].notes.append("搬迁+事业同现→可核对工作或学业环境是否有调整安排")

    # 健康+事业同时出现 → 注意工作压力影响健康
    if "健康" in cats and "事业" in cats:
        ev_map["健康"].notes.append("健康+事业同现→工作/学业压力可能影响身体")

    # 桃花关系压力信号 + 婚嫁正面 → 婚嫁降级。
    # 仅当桃花负面明确来自卯辰穿时才降级；日支六冲本身不决定现实关系结果。
    if "桃花" in ev_map and "婚嫁" in ev_map:
        th = ev_map["桃花"]
        hj = ev_map["婚嫁"]
        th_trig = str(th.triggers)
        is_relationship_pressure = "卯辰穿" in th_trig
        if th.direction == "负面" and hj.direction == "正面" and is_relationship_pressure:
            hj.direction = "中性"
            hj.strength = max(1, hj.strength - 1)
            hj.notes.append("桃花关系压力信号与婚嫁正面信号同现→关系定型信号需谨慎核对")
            conflict = "桃花负面与婚嫁正面同年，且桃花含明确穿害结构；婚嫁方向降为中性"
            hj.conflicts.append(conflict)
            th.conflicts.append(conflict)

def _cross_ref_hunjia_taohua(events: list[EventSignal], age: int = 0):
    """婚嫁可以带来桃花铺垫，但普通桃花不能反推婚嫁。

    规则:
    1. 婚嫁≥2★ → 派生桃花信号（星数上限2），表示关系事件的感情铺垫。
    2. 桃花无论强弱都不派生婚嫁。桃花只说明关系领域活跃，不能证明婚期。

    ``age`` 保留为兼容参数；年龄不再改变这个单向关系。
    """
    taohua_evts = [e for e in events if e.category == "桃花"]
    hunjia_evts = [e for e in events if e.category == "婚嫁"]
    max_th = max((e.strength for e in taohua_evts), default=0)
    max_hj = max((e.strength for e in hunjia_evts), default=0)

    # 婚嫁≥2 → 补桃花（仅当无原生桃花≥2★时才补，避免重复）
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
                notes=[*best.notes, "婚嫁规则信号较强→感情领域同步活跃的候选，需以现实进展核对"],
            ))

