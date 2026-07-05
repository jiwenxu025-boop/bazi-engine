"""抗压画像分析"""
from ..enums import Tiangan, Dizhi, Shishen


def analyze_stress_profile(
    favorable_shishen: list[str],
    harmful_shishen: list[str],
    strength: str,
    pattern: str,
    gender: str,
    pillars_data: list[dict],
    special_combos: list[str],
    bingyao_combos: list[dict] | None = None,
    scores: dict | None = None,
) -> dict:
    """抗压心理画像——三引擎架构（v0.10.0）

    引擎一：压力源定位（官杀扫描）
    引擎二：防御机制分类（A比劫硬刚 / B杀印相生 / C食伤制杀）
    引擎三：崩溃临界点（七杀攻身 / 财破印生杀）
    """
    is_strong = "强" in strength

    # ── 统计十神分布 ──
    all_shishen = []
    for p in pillars_data:
        if p.get("ten_god"):
            all_shishen.append(p["ten_god"])
        for h in (p.get("hidden_ten_gods") or []):
            all_shishen.append(h)

    has_zhengguan = "正官" in all_shishen
    has_qisha = "偏官" in all_shishen or "七杀" in all_shishen
    has_zhengyin = "正印" in all_shishen
    has_pianyin = "偏印" in all_shishen
    has_shishen = "食神" in all_shishen
    has_shangguan = "伤官" in all_shishen
    has_bijian = "比肩" in all_shishen
    has_jiecai = "劫财" in all_shishen
    has_zhengcai = "正财" in all_shishen
    has_piancai = "偏财" in all_shishen

    guan_count = sum(1 for s in all_shishen if s in ("正官", "偏官"))
    sha_count = sum(1 for s in all_shishen if s == "偏官")
    yin_count = sum(1 for s in all_shishen if s in ("正印", "偏印"))
    shishang_count = sum(1 for s in all_shishen if s in ("食神", "伤官"))
    bijie_count = sum(1 for s in all_shishen if s in ("比肩", "劫财"))

    # ════════════════════════════════════════
    # 引擎一：压力源定位
    # ════════════════════════════════════════
    if sha_count >= 2 or (has_qisha and guan_count >= 3):
        pressure_type = "七杀主导型"
        pressure_desc = (
            f"压力以突发性、高强度、生存级危机为主。"
            f"命局七杀{'多重' if sha_count >= 2 else '透出'}，"
            f"长期处于警觉/应激状态，对潜在威胁极度敏感，安全感基线偏低。"
            f"{'官多化杀——体制内规则性压力也转化为心理上的生存焦虑。' if guan_count >= 3 else ''}"
        )
    elif has_zhengguan and guan_count >= 2:
        pressure_type = "正官主导型"
        pressure_desc = (
            "压力以体制化、规则性、慢性积累为主。"
            "对权威、规范、社会评价敏感，压力来自KPI/长辈期许/社会角色期待。"
            "有底线思维，守规矩，但长期处于'达标焦虑'中。"
        )
    elif has_qisha and guan_count == 1:
        pressure_type = "隐性七杀型"
        pressure_desc = (
            "表面压力不大，但潜意识中有未解决的恐惧源。"
            "七杀藏而不透→压力是慢性背景噪音，特定流年引动时集中爆发。"
        )
    else:
        pressure_type = "低官杀型"
        pressure_desc = (
            "命局官杀不显，日常心理压力较低。"
            "缺乏外部压力驱动，自驱力需靠食伤(兴趣)或印星(求知)来补充。"
            "优点是心态松弛，缺点是紧迫感不足、容易拖延。"
        )

    # ════════════════════════════════════════
    # 引擎二：防御机制分类
    # ════════════════════════════════════════
    defense_mode = ""
    defense_desc = ""

    # C: 食伤制杀（优先级最高——主动反击型）
    _bingyao_names = {c["combo"] for c in bingyao_combos} if bingyao_combos else set()
    _has_shishang_zhisha = bool(_bingyao_names & {"食神制杀", "伤官驾杀"})
    _has_shayin = "杀印相生" in _bingyao_names
    if scores and not _has_shishang_zhisha:
        qs = scores.get("偏官", 0)
        ss = scores.get("食神", 0) + scores.get("伤官", 0)
        _has_shishang_zhisha = ss >= 3.0 and qs >= 3.0
    if not _has_shayin and scores:
        qs = scores.get("偏官", 0)
        yi = scores.get("正印", 0) + scores.get("偏印", 0)
        _has_shayin = qs >= 3.0 and yi >= 3.0
    if _has_shishang_zhisha or (has_shishen and has_qisha):
        defense_mode = "C：火力反击型（食伤制杀）"
        defense_desc = (
            "遇到压力直接反击——用才华、语言、或破格行动去消灭压力源。"
            "思维敏捷，擅长在绝境中找到非对称破局点。"
            "极度慕强，只服比自己更强的人。弱点：情绪上头时可能过度反击、破坏关系。"
        )
    # B: 杀印相生（逻辑降维型）
    elif _has_shayin or (has_qisha and (has_zhengyin or has_pianyin) and yin_count >= 1):
        defense_mode = "B：逻辑降维型（杀印相生）"
        defense_desc = (
            "遇到绝境不靠体力靠脑力——用深度学习、技术钻研、规则利用来吸收压力。"
            "越是在高压环境下，思维越清晰冷静。"
            "将每一次危机转化为经验值和知识储备。弱点：过度依赖理性，情感表达受阻。"
        )
    # A: 比劫硬刚（身强+比劫）
    elif is_strong and bijie_count >= 2:
        defense_mode = "A：物理硬刚型（身强+比劫抗杀）"
        defense_desc = (
            "遇到高压不妥协、不拐弯。靠意志力、体能、或拉拢同伴去硬拼。"
            "极度固执，宁折不弯，遇强则强。"
            "优势是执行力超强，劣势是不善迂回——硬扛不过时容易突然崩溃。"
        )
    # 混合/弱防御
    elif not is_strong and guan_count >= 2 and yin_count == 0 and shishang_count == 0:
        defense_mode = "无有效防御（⚠ 脆弱型）"
        defense_desc = (
            "面对压力缺乏有效的心理防御工具——无印星化解，无食伤反击，无比劫硬抗。"
            "容易陷入深度焦虑，遭遇挫折后恢复周期长。"
        )
    else:
        # 模糊型
        defense_mode = "混合型"
        if is_strong:
            defense_desc = "身强有一定抗压底子，但缺乏突出的防御专长。压力下倾向于'先扛再说'，建议有意识培养印星（学习/规划）或食伤（表达/创作）作为减压出口。"
        else:
            defense_desc = "身偏弱但有一定缓冲机制。压力下倾向于回避或依赖他人。建议强化比劫（运动/社交）或印星（阅读/冥想）来建立主动抗压能力。"

    # ════════════════════════════════════════
    # 引擎三：崩溃临界点
    # ════════════════════════════════════════
    crash_points = []

    # 规则1：七杀攻身（身极弱+无印+无食伤）
    if (not is_strong and has_qisha and guan_count >= 2
        and yin_count == 0 and shishang_count == 0):
        crash_points.append({
            "trigger": "七杀攻身（纯肉身挨打型）",
            "mechanism": (
                "身弱+官杀旺+无印无食伤→面对压力无任何化解或反击工具，"
                "属于'纯肉身挨打'状态。极易陷入深度焦虑、讨好型人格、"
                "遇到重大挫折后可能彻底摆烂或产生自我毁灭倾向。"
            ),
            "prevention": (
                "必须后天建立防御：①培养一项需要深度专注的技能（印星替代）；"
                "②坚持高强度体育锻炼（比劫替代）；③远离PUA型环境和人物。"
            ),
        })

    # 规则2：财破印生杀
    if (has_zhengcai or has_piancai) and (has_zhengyin or has_pianyin) and has_qisha:
        crash_points.append({
            "trigger": "财破印生杀（逻辑崩盘型）",
            "mechanism": (
                "原局印星（理智/信仰/原则）是抵御七杀（危机）的防火墙。"
                "但财星（欲望/利益/情欲）会击碎印星，并源源不断给七杀供弹。"
                "典型场景：因贪婪（钱/色/捷径）放弃原则→防线瞬间决堤→危机全面失控。"
            ),
            "prevention": (
                "核心红线：面临高回报诱惑时必须回归原则性判断（印星），"
                "不要用'这次例外'破坏自己的底层逻辑。建立'诱惑审查清单'："
                "这件事是否在消耗我的核心防御？"
            ),
        })

    # ── 组装输出 ──
    daily_psyche = (
        f"压力类型：{pressure_type}。{pressure_desc}"
    )
    extreme_response = (
        f"防御模式：{defense_mode}。{defense_desc}"
    )
    prevention_text = (
        "；".join([cp["prevention"] for cp in crash_points])
        if crash_points
        else "当前命局防御体系完整，未检测到系统性崩溃临界点。压力管理重点：维持现有防御机制的有效运转，避免长期透支。"
    )

    return {
        "pressure_type": pressure_type,
        "pressure_source": pressure_desc,
        "defense_mode": defense_mode,
        "defense_desc": defense_desc,
        "crash_points": crash_points,
        "daily_psyche": daily_psyche,
        "extreme_response": extreme_response,
        "prevention": prevention_text,
    }

