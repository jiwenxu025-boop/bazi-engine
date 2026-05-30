"""性格分析主函数"""
from ..enums import Tiangan, Dizhi, Shishen
from .._constants import DIZHI_CANGGAN, DIZHI_LIUHE, DIZHI_SANHE
from ..ten_gods import get_ten_god
from .dataclasses import PersonalityResult
from .constants import DAY_MASTER_PERSONALITY, PATTERN_PERSONALITY, SHISHEN_PERSONALITY
from .weighting import (
    get_weighted_shishen_report, _compute_weighted_shishen,
)
from .bingyao import detect_bingyao_combos
from .special_combos import _check_special_combos
from .traits import (
    _compute_shishen_sub_traits, _compute_shishen_combo_traits,
    _compute_dizhi_traits, _compute_hidden_stem_personality,
)


def analyze_personality(
    day_master_stem: str,
    day_master_wuxing: str,
    day_master_yinyang: str,
    pattern: str,
    strength: str,
    score: float,
    favorable_shishen: list[str],
    harmful_shishen: list[str],
    pillars_data: list[dict],
    interactions: dict,
    gender: str,
) -> PersonalityResult:
    """分析性格

    Args:
        pillars_data: [{pillar_type, stem, branch, ten_god, source, hidden_stems, hidden_ten_gods}, ...]
        interactions: {"tiangan": [...], "dizhi": [...]}
    """
    result = PersonalityResult()

    # ── Step 1: 日干核心性格 → 结构化数据（不做预判文字）──
    dm_info = DAY_MASTER_PERSONALITY.get(day_master_stem)
    if dm_info:
        result.day_master_core = {
            "五行": day_master_wuxing,
            "阴阳": day_master_yinyang,
            "形象": dm_info["image"],
            "五德": dm_info["wude"],
        }
    else:
        result.day_master_core = {"五行": day_master_wuxing, "阴阳": day_master_yinyang}

    # ── Step 2: 身强弱调节 → 只传数值，不做性格预判 ──
    result.strength_label = f"{strength}（{score}分）"

    # ── Step 3: 最旺十神 ──
    dominant, is_fav, shishen_desc = _find_dominant_shishen(pillars_data, harmful_shishen, interactions)

    # 存储加权十神报告，供病药检测和LLM融合引擎使用
    result.stress_profile = result.stress_profile or {}
    w_report = get_weighted_shishen_report(pillars_data, interactions)
    result.stress_profile["_weighted_shishen"] = w_report  # type: ignore[assignment]
    result.weighted_shishen = w_report

    # 病药组合检测
    result.bingyao_combos = detect_bingyao_combos(
        w_report["scores"], strength, pattern, pillars_data
    )

    if dominant:
        fav_label = "喜用" if is_fav else "忌神"
        result.dominant_ten_god = (
            f"最旺十神：{dominant}（{fav_label}）→ {shishen_desc}"
        )

    # ── Step 4: 格局定基调（双面：喜用/忌神）──
    for key, sides in PATTERN_PERSONALITY.items():
        if key in pattern:
            # 判断格局是喜用还是忌神
            pattern_is_fav = key not in harmful_shishen if harmful_shishen else True
            side = "喜用" if pattern_is_fav else "忌神"
            desc = sides.get(side, sides.get("喜用", ""))
            label = "喜用面" if pattern_is_fav else "忌神面（需注意）"
            result.pattern_influence = f"格局{pattern}（{label}）→ {desc}"
            break
    if not result.pattern_influence:
        result.pattern_influence = f"格局{pattern}"

    # ── Step 5: 特殊组合 ──
    result.special_combos = _check_special_combos(
        day_master_stem, day_master_wuxing,
        pillars_data, interactions, gender,
        harmful_shishen, pattern,
    )

    # ── Step 5b: 粒度性格特质 (v0.15.0) ──
    result.sub_traits = _compute_shishen_sub_traits(w_report["scores"])
    result.combo_traits = _compute_shishen_combo_traits(w_report["scores"])
    result.dizhi_traits = _compute_dizhi_traits(interactions, pillars_data)

    # 四柱藏干→人格特质
    hidden_all = _compute_hidden_stem_personality(pillars_data)
    if hidden_all:
        result.sub_traits.extend(hidden_all)

    # ── Step 6: 分领域性格（加权分数驱动，6维度）──

    dm_core = dm_info["core"] if dm_info else ""
    dm_neg = dm_info["negative"] if dm_info else ""
    is_strong = "强" in strength
    is_weak = "弱" in strength

    # ── 加权分数快捷访问 ──
    ws = w_report["scores"]
    def _s(name: str) -> float:
        return ws.get(name, 0)

    shi_shen_s = _s("食神")
    shang_guan_s = _s("伤官")
    shishang_s = shi_shen_s + shang_guan_s
    zheng_yin_s = _s("正印")
    pian_yin_s = _s("偏印")
    yin_s = zheng_yin_s + pian_yin_s
    zheng_guan_s = _s("正官")
    qi_sha_s = _s("偏官") + _s("七杀")
    guan_s = zheng_guan_s + qi_sha_s
    zheng_cai_s = _s("正财")
    pian_cai_s = _s("偏财")
    cai_s = zheng_cai_s + pian_cai_s
    bijie_s = _s("比肩") + _s("劫财")

    # 辅助判断
    day_branch = pillars_data[2].get("branch", "") if len(pillars_data) > 2 else ""
    day_branch_str = day_branch

    day_branch_chong = False
    day_branch_he = False
    for inter in interactions.get("dizhi", []):
        if "日柱" in inter.get("pillars", []):
            if inter["type"] == "六冲":
                day_branch_chong = True
            elif inter["type"] in ("六合", "三合", "半合"):
                day_branch_he = True

    has_huagai = bool(_huagai_branch(day_branch_str)) and \
                 _has_branch_in_pillars(_huagai_branch(day_branch_str), pillars_data)
    taohua = _taohua_branch(day_branch_str)
    has_taohua_rizhi = taohua is not None and any(
        p.get("branch") == taohua and p.get("pillar_type") == "日柱"
        for p in pillars_data
    )
    cai_po_yin_flag = any("财破印" in c for c in result.special_combos)
    # 检查是否存在官杀混杂标签（病药检测已判断）
    has_guansha_hunza = any("官杀混杂" == c["combo"] for c in result.bingyao_combos)

    # ═══════════════════════════════════════════════════════════
    # 六维度信号：生成结构化数据供 LLM 融合，同时保留简短摘要供前端回退
    # ═══════════════════════════════════════════════════════════

    # ── 社交：食伤(表达欲) + 比劫(群体融入) - 印星(内敛) - 官杀(拘谨) ──
    social_extra = shishang_s * 0.6 + bijie_s * 0.4 - yin_s * 0.5 - guan_s * 0.2
    if is_strong:
        social_extra += 1.0
    elif is_weak:
        social_extra -= 1.0
    social_label = "外向" if social_extra >= 1 else ("平衡" if social_extra >= -2 else "内敛")
    result.trait_signals["社交"] = {
        "表达欲": round(shishang_s, 1),
        "群体融入": round(bijie_s, 1),
        "内敛度": round(yin_s, 1),
        "拘谨度": round(guan_s, 1),
        "身强弱修正": "身强+1" if is_strong else ("身弱-1" if is_weak else "中和±0"),
        "综合倾向": social_label,
        "综合分数": round(social_extra, 1),
    }
    _social_text = f"偏{'外向，在人群中自如' if social_extra >= 1 else ('平衡，大场合能应付，熟人圈放得开' if social_extra >= -2 else '内敛，社交消耗能量，独处才能恢复')}"
    if shishang_s >= 5 and yin_s >= 5:
        _social_text += "。表达欲和安全感需求并存，需要信任后才释放"
    result.traits["社交"] = _social_text

    # ── 感情：官杀(责任) + 财星(欲望) + 日支状态 + 桃花 ──
    day_hidden = pillars_data[2].get("hidden_ten_gods", []) if len(pillars_data) > 2 else []
    fq_state = "冲" if day_branch_chong else ("合" if day_branch_he else "平稳")
    spouse_star_note = "男命以财为妻星，女命以官杀为夫星" if gender in ("男", "女") else ""
    result.trait_signals["感情"] = {
        "责任感_官杀": round(guan_s, 1),
        "欲望_财星": round(cai_s, 1),
        "同辈竞争_比劫": round(bijie_s, 1),
        "独立反叛_伤官": round(shang_guan_s, 1),
        "夫妻宫状态": fq_state,
        "桃花坐日支": has_taohua_rizhi,
        "日支藏干": day_hidden[:3],
        "身强弱": "强" if is_strong else ("弱" if is_weak else "中和"),
        "性别": gender,
    }
    if spouse_star_note:
        result.trait_signals["感情"]["_性别提示"] = spouse_star_note
    _romance_parts = []
    if day_branch_chong:
        _romance_parts.append("夫妻宫被冲，感情波动较大，磨合期长")
    elif day_branch_he:
        _romance_parts.append("夫妻宫被合，配偶缘好但需注意边界感")
    if guan_s >= 5:
        _romance_parts.append("责任感强，在关系中重承诺" + ("，敢主动追求" if is_strong else "，但也容易感到压力"))
    elif cai_s >= 5:
        _romance_parts.append("重视实际付出和物质基础，浪漫体现在行动而非言语")
    if bijie_s >= 5 and gender == "男":
        _romance_parts.append("比劫旺，感情中注意同辈竞争或第三者介入")
    if shang_guan_s >= 5:
        _romance_parts.append("伤官旺，对传统关系模式有抵触，需要更多自由空间" if gender == "女" else "伤官旺，容易对伴侣挑剔，需注意沟通方式")
    if has_taohua_rizhi:
        _romance_parts.append("桃花坐日支，异性缘好，需学会分辨心动和合适")
    if not _romance_parts:
        _romance_parts.append("感情模式平稳，平常比较随缘")
    result.traits["感情"] = "。".join(_romance_parts)

    # ── 决策：七杀(果断) + 印星(分析) + 食伤(直觉) ──
    decide_risk = qi_sha_s * 0.7 + (shishang_s if shang_guan_s > shi_shen_s else shi_shen_s * 0.3) - yin_s * 0.6
    if is_strong:
        decide_risk += 0.5
    elif is_weak:
        decide_risk -= 0.5
    decide_label = "果断激进" if decide_risk >= 4 else ("分析后决策" if decide_risk >= 1 else ("审慎" if decide_risk >= -2 else "过度分析"))
    result.trait_signals["决策"] = {
        "果断度_七杀": round(qi_sha_s, 1),
        "分析度_印星": round(yin_s, 1),
        "直觉度_食伤": round(shishang_s, 1),
        "伤官倾向": round(shang_guan_s, 1),
        "食神倾向": round(shi_shen_s, 1),
        "综合倾向": decide_label,
        "综合分数": round(decide_risk, 1),
    }
    _decide_text = "果断激进型，大事不拖但偶尔冲动" if decide_risk >= 4 else (
        "分析后决策型，收集足够信息后能快速拍板" if decide_risk >= 1 else (
        "审慎型，决策前反复权衡，但决定了就不轻易改" if decide_risk >= -2 else "过度分析型，确定性的阈值很高，容易拖延"
    ))
    if qi_sha_s >= 6 and yin_s >= 6:
        _decide_text += "。果断和分析并存——平常想得多，关键时刻敢出手"
    result.traits["决策"] = _decide_text

    # ── 内心：偏印(精神世界) + 食神(自洽) + 华盖 + 比劫(自我意识) ──
    inner_complex = pian_yin_s * 0.8 + (1 if has_huagai else 0) * 2.0 - shi_shen_s * 0.4
    inner_self = bijie_s * 0.5
    inner_flags = []
    if has_huagai:
        inner_flags.append("华盖")
    if cai_po_yin_flag:
        inner_flags.append("财破印")
    inner_style = "印格安稳" if "印" in pattern else (f"{'阳' if day_master_yinyang == '阳' else '阴'}干{'直率' if day_master_yinyang == '阳' else '内敛'}")
    result.trait_signals["内心"] = {
        "精神世界_偏印": round(pian_yin_s, 1),
        "自洽度_食神": round(shi_shen_s, 1),
        "自我意识_比劫": round(bijie_s, 1),
        "特殊标记": inner_flags,
        "内在复杂度": round(inner_complex, 1),
        "自我强度": round(inner_self, 1),
        "基础风格": inner_style,
    }
    _inner_parts = []
    if has_huagai:
        _inner_parts.append("华盖入命，有独立的精神追求，不介意独处")
    if inner_complex >= 2:
        _inner_parts.append("精神世界丰富，内心有自己的逻辑体系")
    if cai_po_yin_flag:
        _inner_parts.append("财破印——理想与现实的拉扯感明显")
    if inner_self >= 3:
        _inner_parts.append("自我意识强，不被他人轻易带节奏")
    if not _inner_parts:
        _inner_parts.append(inner_style + ("，内心与外表较一致" if day_master_yinyang == "阳" else "，外表温和内有主见"))
    result.traits["内心"] = "。".join(_inner_parts)

    # ── 事业 ──
    career_scores = {
        "体制/管理": guan_s * 0.8 + yin_s * 0.4,
        "商业/经营": cai_s * 0.8 + shishang_s * 0.3,
        "技术/创意": shishang_s * 0.8 + pian_yin_s * 0.4,
        "学术/专业": yin_s * 0.8 + guan_s * 0.2,
        "创业/独立": bijie_s * 0.5 + shishang_s * 0.4 + qi_sha_s * 0.3,
    }
    top_career = sorted(career_scores.items(), key=lambda x: x[1], reverse=True)
    primary, secondary = top_career[0], top_career[1]
    career_gap = primary[1] - secondary[1]
    result.trait_signals["事业"] = {
        "体制_管理": round(career_scores["体制/管理"], 1),
        "商业_经营": round(career_scores["商业/经营"], 1),
        "技术_创意": round(career_scores["技术/创意"], 1),
        "学术_专业": round(career_scores["学术/专业"], 1),
        "创业_独立": round(career_scores["创业/独立"], 1),
        "主导方向": primary[0],
        "次要方向": secondary[0],
        "方向差距": round(career_gap, 1),
        "格局": pattern,
    }
    if career_gap > 2.0:
        result.traits["事业"] = f"方向明确：{primary[0]}型，不适合纯{secondary[0]}路线"
    else:
        result.traits["事业"] = f"{primary[0]}+{secondary[0]} 混合型，适合交叉赛道而非纯单一方向"

    # ── 财富观：财星(欲望) + 比劫(散财) + 食伤(创造力变现) ──
    wealth_flags = []
    if cai_po_yin_flag:
        wealth_flags.append("财破印→短期诱惑冲击长期积累")
    if cai_s >= 6.0 and not is_strong:
        wealth_flags.append("财旺身弱→机会多但精力撑不起野心")
    result.trait_signals["财富观"] = {
        "欲望_财星": round(cai_s, 1),
        "散财_比劫": round(bijie_s, 1),
        "创造力变现_食伤": round(shishang_s, 1),
        "储蓄保守_印星": round(yin_s, 1),
        "身强弱": "强" if is_strong else ("弱" if is_weak else "中和"),
        "特殊标记": wealth_flags,
    }
    _wealth_parts = []
    if cai_s >= 6.0 and is_strong:
        _wealth_parts.append("财旺身强，有赚钱头脑，对机会敏感")
    elif cai_s >= 6.0 and not is_strong:
        _wealth_parts.append("财旺身弱，想赚钱但精力撑不起野心，先补专业壁垒再求财")
    elif bijie_s >= 6.0 and cai_s < 3.0:
        _wealth_parts.append("比劫旺财弱，钱财易散，不适合合伙。赚钱应走差异化路线")
    elif cai_po_yin_flag:
        _wealth_parts.append("财破印，容易为短期利益放弃长期积累。把大目标拆成短期里程碑")
    elif shishang_s >= 6.0 and cai_s < 3.0:
        _wealth_parts.append("食伤旺财弱，才华是最大资产，变现靠创造力而非资本")
    elif cai_s < 2.0:
        _wealth_parts.append("财星不显，对钱不执着，更看重工作意义和人生体验")
    else:
        _wealth_parts.append("财星适中，对钱有正常欲望但不极端。" + ("能守能赚" if is_strong else "优先增强自身实力，钱自然跟来"))
    result.traits["财富观"] = "。".join(_wealth_parts)

    # ── 综合画像 ──
    parts = [f"日主{day_master_stem}（{day_master_wuxing}·{day_master_yinyang}），身{strength}，{pattern}。"]
    if dm_info:
        parts.append(f"核心性格：{dm_info['core']}。")
    if dominant:
        parts.append(f"最突出十神为{dominant}（{'喜用' if is_fav else '忌神'}），{shishen_desc}。")
    if result.special_combos:
        # 挑选2-3个最重要的组合
        key_combos = result.special_combos[:3]
        parts.append("关键组合：" + "；".join(c.split("→")[0] for c in key_combos) + "。")
    parts.append(f"社交{'外向开放' if is_strong else '偏内向收敛'}，"
                 f"决策{'果断' if is_strong else '审慎'}，"
                 f"事业{'求稳' if '官' in pattern or '印' in pattern else '求变' if '杀' in pattern or '伤' in pattern else '平衡'}。")
    result.profile = "".join(parts)

    # ── Step 7: 现实校验 —— 检测矛盾、修正套路化判断 ──
    _apply_reality_check(result, day_master_stem, day_master_wuxing, strength, score,
                         pattern, pillars_data, interactions, gender,
                         harmful_shishen, favorable_shishen)

    # ── v0.10.0: 抗压心理画像（三引擎）──
    result.stress_profile = analyze_stress_profile(
        favorable_shishen=favorable_shishen,
        harmful_shishen=harmful_shishen,
        strength=strength,
        pattern=pattern,
        gender=gender,
        pillars_data=pillars_data,
        special_combos=result.special_combos,
    )

    return result

def _apply_reality_check(result: PersonalityResult,
                         day_master_stem: str, day_master_wuxing: str,
                         strength: str, score: float,
                         pattern: str, pillars_data: list[dict],
                         interactions: dict, gender: str,
                         harmful_shishen: list[str], favorable_shishen: list[str]):
    """检测命局矛盾，修正套路化/脸谱化判断。

    核心原则：
    1. 任何十神/格局描述都不能脱离身强弱
    2. 存在对立组合时（如财破印、伤官见官），必须标注矛盾而非单面描述
    3. 大运影响当前性格表现
    4. 现实行为优先于理论标签
    """
    corrections: list[str] = []

    is_weak = "弱" in strength
    is_strong = "强" in strength
    is_neutral = "中和" in strength

    # 快速判断
    all_tg = set(p.get("ten_god", "") for p in pillars_data if p.get("source") == "stem")
    all_hidden = set()
    for p in pillars_data:
        for h in p.get("hidden_ten_gods", []):
            all_hidden.add(h)
    all_combined = all_tg | all_hidden

    has_cai_stem = any("财" in (p.get("ten_god") or "") and p.get("source") == "stem" for p in pillars_data)
    has_yin_stem = any("印" in (p.get("ten_god") or "") and p.get("source") == "stem" for p in pillars_data)
    has_shang = "伤官" in all_combined
    has_guan = "正官" in all_combined
    has_zhengcai = "正财" in all_combined
    has_piancai = "偏财" in all_combined
    shang_jian_guan = has_shang and has_guan
    cai_po_yin = has_cai_stem and has_yin_stem
    bijie_count = sum(1 for p in pillars_data if p.get("ten_god") in ("比肩", "劫财"))
    yin_count = sum(1 for p in pillars_data if p.get("ten_god") in ("正印", "偏印"))

    # ── 规则 1: 财破印 —— 现实利益与学业/理想的冲突 ──
    if cai_po_yin:
        if "正印" in pattern or "偏印" in pattern:
            corrections.append(
                "财破印——虽为印格，但现实中对利益的兴趣 ≥ 对学问的兴趣。"
                "不是不爱学习，是更爱能变现的东西。若做学术，需是自己真心热爱的领域，"
                "否则坚持不下去。"
            )
            # 修正 pattern_influence
            result.pattern_influence = result.pattern_influence.replace(
                "好学深思", "有学习潜力但需要内在动机驱动"
            ).replace("淡泊名利", "内心有清高的一面，但现实诱惑常拉扯")
            # 修正 dominant_ten_god if 正印
            if result.dominant_ten_god and "正印" in result.dominant_ten_god:
                result.dominant_ten_god = result.dominant_ten_god.replace(
                    "爱读书思考", "有学习天赋，但需自发兴趣驱动，被动灌输无效"
                ).replace("淡泊名利", "精神追求与物质欲望并存")

    # ── 规则 2: 身弱 —— 所有正面特质打折扣 ──
    if is_weak and score < 1.0:
        corrections.append(
            f"身极弱（{score}分）——理想中的性格特质因能量不足而难以充分发挥。"
            "表现出的状态：容易累、容易纠结、想得多做得少、需要外界推一把。"
            "这不是懒或性格缺陷，是能量层面的客观限制。补身（增强实力、积累学历/技能）后会有质的飞跃。"
        )
        # 调整 strength_label
        result.strength_label += (
            "。现实中容易表现为：专注力不够持久、对压力敏感、做事需要外力推动。"
            "能量积累（学历/技能/身体）是性格发挥的前提，在这之前不要苛责自己。"
        )

    # ── 规则 3: 伤官见官 —— 不服管、不走寻常路 ──
    if shang_jian_guan:
        if "正印" in pattern:
            corrections.append(
                "伤官见官+正印格——表面文静听话，内心极其有自己的想法。"
                "不是叛逆张扬型的反叛，而是'你说的我都听着，但我该怎么做还怎么做'。"
                "不适合高度规则化、层级森严的环境，适合有自主空间的工作。"
            )
        elif "正官" in pattern:
            corrections.append(
                "伤官见官+官格——内心有强烈的反规则冲动，但又不得不在规则内行事。"
                "这种矛盾会带来内耗：做自己想做的不敢，做别人要求的又不甘。"
                "解决方案是找到合规范围内的创新空间。"
            )

    # ── 规则 4: 比劫多 —— 朋友的影响 ──
    if bijie_count >= 3:
        if is_weak:
            corrections.append(
                "比劫多（朋友/同辈多）——社交圈对她的影响很大，容易因为朋友的事分心或破财。"
                "帮朋友前先掂量自己的能力和精力"
            )
        else:
            corrections.append(
                "比劫多——社交圈广，朋友多且能在关键时刻帮忙。适合团队合作。"
            )

    # ── 规则 5: 印星重但身弱 —— 依赖性强 ──
    if yin_count >= 3 and is_weak:
        corrections.append(
            "印星重重但身弱——需要依靠却得到的帮助不够（印多而不生身=湿木不生火）。"
            "现实中表现为：有贵人/长辈/导师的潜在帮助，但真正关键时还得靠自己。"
            "建议主动筛选真正能帮到你的人，不要被动等待。"
        )

    # ── 规则 6: 阴干+身弱 —— 内敛的表达方式 ──
    if day_master_stem in ("乙", "丁", "己", "辛", "癸") and is_weak:
        corrections.append(
            "阴干身弱——不是真的内向或社恐，是在不熟的人面前会自动收敛。"
            "小圈子或对信任的人会很放得开。需要的是安全感，不是社交训练。"
        )

    # ── 规则 7: 财星透干+身弱 —— 对钱的态度 ──
    if has_cai_stem and is_weak:
        corrections.append(
            "财星透干但身弱——想赚钱但能量撑不起野心，容易'富屋贫人'（看起来有赚钱机会但实际到手的少）。"
            "先投资自己（技能/学历/身体），等身变强了再追求财富，否则容易被钱反噬。"
        )

    # ── 规则 8: 格局与行为的偏差 ──
    if "正印" in pattern and is_weak and has_shang:
        corrections.append(
            "正印格+伤官——传统认知的'乖乖女'标签不适合她。"
            "她有独立的精神世界和创造力，只是不轻易对外展示。"
            "找到能发挥她创造力的出口，比规规矩矩走寻常路更适合。"
        )

    # 将修正注入 result
    result.special_combos.append("── 现实校验（防止脸谱化）──")
    for c in corrections:
        result.special_combos.append(c)

    # ── 重写 profile 为实用版本 ──
    dm_info = DAY_MASTER_PERSONALITY.get(day_master_stem, {})
    dm_core_short = dm_info.get("core", "").split("，")[0] if dm_info else ""
    dm_image = dm_info.get("image", "") if dm_info else ""

    # 基础画像
    strength_word = "偏弱" if is_weak else "偏强" if is_strong else "中和"
    profile_parts = [
        f"日主{day_master_stem}（{day_master_wuxing}·{strength_word}），{dm_image}。",
        f"核心：{dm_core_short}。" if dm_core_short else "",
    ]

    # 加入最重要的1-2条现实校验
    key_corrections = [c for c in corrections if not c.startswith("印星重") and not c.startswith("阴干身弱")]
    if key_corrections:
        # 取最短最重要的一条
        best = min(key_corrections, key=len)
        profile_parts.append(best.split("——")[-1] if "——" in best else best)

    result.profile = "".join(profile_parts)

