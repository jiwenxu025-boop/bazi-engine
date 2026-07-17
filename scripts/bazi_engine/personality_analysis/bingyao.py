"""病药组合候选检测。"""
from .constants import (
    BIJIE_STARS,
    CAI_STARS,
    GUAN_STARS,
    SHISHANG_STARS,
    THRESHOLD_PRESENT,
    THRESHOLD_STRONG,
    YIN_STARS,
)


def _sum_group(scores, group: tuple[str, ...]) -> float:
    """计算一组十神的加权总分"""
    return sum(scores.get(s, 0) for s in group)

def _is_adjacent(pillars_data: list[dict], shishen_a: str, shishen_b: str) -> bool:
    """检查两个十神是否在相邻柱或同柱出现（贴身关系）"""
    positions: dict[str, list[int]] = {}
    for i, p in enumerate(pillars_data):
        tg = p.get("ten_god")
        if tg:
            positions.setdefault(tg, []).append(i)
        for htg in p.get("hidden_ten_gods", []):
            positions.setdefault(htg, []).append(i)
    pos_a = positions.get(shishen_a, [])
    pos_b = positions.get(shishen_b, [])
    for pa in pos_a:
        for pb in pos_b:
            if abs(pa - pb) <= 1:  # 同柱(差0)或相邻柱(差1)
                return True
    return False

def detect_bingyao_combos(
    weighted_scores,
    strength: str,
    pattern: str,
    pillars_data: list[dict],
) -> list[dict]:
    """检测病药组合，返回按优先级排序的规则候选列表。

    Returns:
        [{"combo": "伤官见官", "priority": 1, "directive": "...",
          "evidence": {...}, "evidence_status": "heuristic_candidate"}, ...]
    """
    scores = weighted_scores
    combos: list[dict] = []

    shang_guan = scores.get("伤官", 0)
    shi_shen = scores.get("食神", 0)
    zheng_guan = scores.get("正官", 0)
    qi_sha = scores.get("偏官", scores.get("七杀", 0))
    pian_yin = scores.get("偏印", 0)
    scores.get("正印", 0)
    scores.get("正财", 0)
    scores.get("偏财", 0)

    cai_total = _sum_group(scores, CAI_STARS)
    guan_total = _sum_group(scores, GUAN_STARS)
    yin_total = _sum_group(scores, YIN_STARS)
    shishang_total = _sum_group(scores, SHISHANG_STARS)
    bijie_total = _sum_group(scores, BIJIE_STARS)

    is_weak = "弱" in strength

    # ── 1. 伤官见官：真我洁癖 vs 秩序需要 ──
    if shang_guan >= THRESHOLD_PRESENT and zheng_guan >= THRESHOLD_PRESENT:
        combos.append({
            "combo": "伤官见官",
            "priority": 1,
            "directive": (
                "规则候选说明：伤官与正官同时达到触发线，可能表现为自主表达与遵循规则之间的拉扯；"
                "需结合具体沟通和规则场景核对，不直接推断性格定型、职业适配或心理状态。"
            ),
            "evidence": {"伤官": shang_guan, "正官": zheng_guan},
            "evidence_status": "heuristic_candidate",
        })

    # ── 2. 食神制杀 / 伤官驾杀：创造本能 × 生存应激 ──
    if qi_sha >= THRESHOLD_STRONG and shishang_total >= THRESHOLD_PRESENT:
        combo_name = "食神制杀" if shi_shen >= shang_guan else "伤官驾杀"
        combos.append({
            "combo": combo_name,
            "priority": 1,
            "directive": (
                "规则候选说明：偏官较强且食伤达到触发线，可能表现为压力场景中更倾向通过表达或解决问题来应对；"
                "需结合实际压力反应核对，不直接推断健康情况、职业能力或工作环境偏好。"
            ),
            "evidence": {"七杀": qi_sha, "食伤": shishang_total, "食神": shi_shen, "伤官": shang_guan},
            "evidence_status": "heuristic_candidate",
        })

    # ── 3. 比劫夺财：归属焦虑 × 欲望引擎 ──
    if (
        bijie_total >= THRESHOLD_STRONG
        and cai_total < THRESHOLD_PRESENT
        and guan_total < THRESHOLD_PRESENT
    ):
        combos.append({
            "combo": "比劫夺财",
            "priority": 2,
            "directive": (
                "规则候选说明：比劫较强且财星、官杀未达触发线，可能表示同辈参照对资源选择的影响较大；"
                "需结合实际消费、合作和边界习惯核对，不直接推断财务纠纷、关系结果或职业选择。"
            ),
            "evidence": {"比劫": bijie_total, "财星": cai_total, "官杀": guan_total},
            "evidence_status": "heuristic_candidate",
        })

    # ── 4. 财多身弱：外部反馈过载 ──
    if cai_total >= THRESHOLD_STRONG and is_weak and cai_total > yin_total:
        combos.append({
            "combo": "财多身弱",
            "priority": 1,
            "directive": (
                "规则候选说明：财星较强、身弱且财星高于印星，可能表示面对较多目标或外部反馈时更易分散；"
                "需结合实际精力和取舍方式核对，不直接推断健康情况、团队依赖或事业结果。"
            ),
            "evidence": {"财星": cai_total, "印星": yin_total, "比劫": bijie_total, "身强弱": strength},
            "evidence_status": "heuristic_candidate",
        })

    # ── 5. 杀印相生：控制焦虑 → 战略武器 ──
    if guan_total >= THRESHOLD_STRONG and yin_total >= THRESHOLD_PRESENT:
        adjacent = (
            _is_adjacent(pillars_data, "偏官", "偏印") or
            _is_adjacent(pillars_data, "偏官", "正印") or
            _is_adjacent(pillars_data, "七杀", "偏印") or
            _is_adjacent(pillars_data, "七杀", "正印") or
            _is_adjacent(pillars_data, "正官", "偏印") or
            _is_adjacent(pillars_data, "正官", "正印")
        )
        if adjacent:
            combos.append({
                "combo": "杀印相生",
                "priority": 1,
                "directive": (
                    "规则候选说明：官杀和印星达到触发线且位置相邻，可能表示面对规则或压力时倾向先理解、规划再行动；"
                    "需结合实际应对方式核对，不直接推断抗压能力、组织适配或职业成就。"
                ),
                "evidence": {"七杀": qi_sha, "印星": yin_total, "贴身": adjacent},
                "evidence_status": "heuristic_candidate",
            })

    # ── 6. 枭神夺食：安全系统绞杀创造本能 ──
    if pian_yin >= THRESHOLD_STRONG and shi_shen >= THRESHOLD_PRESENT:
        combos.append({
            "combo": "枭神夺食",
            "priority": 1,
            "directive": (
                "规则候选说明：偏印较强且食神达到触发线，可能表示谨慎评估与表达、享受之间存在拉扯；"
                "需结合实际表达和放松情境核对，不直接推断心理健康、创造能力或生活经历。"
            ),
            "evidence": {"偏印": pian_yin, "食神": shi_shen},
            "evidence_status": "heuristic_candidate",
        })

    # ── 7. 印重身滞：安全系统过载 ──
    # 印星过旺（≥8.0）→ 必须先理解所有变量才敢行动 → 永远在准备
    if yin_total >= 8.0 and yin_total >= max(scores.values(), default=0):
        combos.append({
            "combo": "印重身滞",
            "priority": 1,
            "directive": (
                "规则候选说明：印星总分较高且为当前最高组，可能表示准备和理解需求较强，启动速度会随情境变化；"
                "需结合实际学习与执行记录核对，不直接推断意志力、职业适配或心理状态。"
            ),
            "evidence": {"印星": yin_total, "食伤": shishang_total},
            "evidence_status": "heuristic_candidate",
        })

    # ── 8. 财破印：欲望引擎 vs 安全系统 ──
    # 财星≥5 且 印星≥3 且 财>印 → 等不了结果 vs 没理解不敢动
    if cai_total >= 5.0 and yin_total >= THRESHOLD_PRESENT and cai_total > yin_total:
        combos.append({
            "combo": "财破印",
            "priority": 2,
            "directive": (
                "规则候选说明：财星和印星同时达到触发线且财星更高，可能表示短期反馈与充分理解之间存在取舍；"
                "需结合实际学习、交付和转换记录核对，不直接推断专注力、收入或职业轨迹。"
            ),
            "evidence": {"财星": cai_total, "印星": yin_total},
            "evidence_status": "heuristic_candidate",
        })

    # ── 9. 食伤过旺泄身：创造本能耗干自己 ──
    # 食伤≥8.0 且 身弱 → 不输出会死但精力撑不住
    if shishang_total >= 8.0 and is_weak:
        combos.append({
            "combo": "食伤过旺泄身",
            "priority": 1,
            "directive": (
                "规则候选说明：食伤总分较高且身弱，可能表示想法、表达需求与可用精力之间存在落差；"
                "需结合实际项目完成和休息情况核对，不直接推断倦怠、身体状态或工作能力。"
            ),
            "evidence": {"食伤": shishang_total, "食神": shi_shen, "伤官": shang_guan, "身强弱": strength},
            "evidence_status": "heuristic_candidate",
        })

    # ── 10. 官杀混杂：两套标准互搏 ──
    # 正官≥3.0 且 七杀≥3.0 → 自我要求内部分裂
    if zheng_guan >= 3.0 and qi_sha >= 3.0:
        combos.append({
            "combo": "官杀混杂",
            "priority": 2,
            "directive": (
                "规则候选说明：正官和偏官同时达到触发线，可能表示稳妥标准与竞争标准并存；"
                "需结合具体决策场景核对，不直接推断选择障碍、睡眠情况、关系结果或心理状态。"
            ),
            "evidence": {"正官": zheng_guan, "七杀": qi_sha},
            "evidence_status": "heuristic_candidate",
        })

    # ── 排序：priority 升序（1最先），同 priority 按影响分数降序 ──
    _STRENGTH_MAP = {"强": 0.8, "偏强": 0.6, "中和": 0.5, "偏弱": 0.4, "弱": 0.2}
    def _sort_key(c):
        ev = c.get("evidence", {})
        nums = []
        for v in ev.values():
            if isinstance(v, (int, float, bool)):
                nums.append(float(v))
            elif isinstance(v, str) and v in _STRENGTH_MAP:
                nums.append(_STRENGTH_MAP[v])
        score_sum = sum(nums)
        return (c["priority"], -score_sum)

    combos.sort(key=_sort_key)
    return combos

