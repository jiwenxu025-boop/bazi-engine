"""LLM 融合引擎 (v0.11.0) — 将 Python 引擎的结构化数据缝合为连贯的性格报告

设计原则:
- Python 引擎 = 理性数据提取器（算分数、检测病药组合）
- LLM = 高情商内容缝合大师（消灭矛盾标签，融合为连贯叙事）
- 流式输出，避免 LLM 推理过程过长的等待感

用法:
    from .personality_fusion import generate_fusion_report

    report_text = await generate_fusion_report(pr, fr, stream_callback=print)
    report_text = generate_fusion_report_sync(pr, fr)  # 同步版(非流式)
"""

import json
import os
import re

import httpx
from ._http import shared_client

from ._deepseek_config import (
    DEEPSEEK_API_URL, DEEPSEEK_KEY, DEEPSEEK_MODEL,
    FUSION_ENABLED, get_timeout, is_available,
)

# ═══════════════════════════════════════════════════════════════
# 系统提示词 — 从 fusion_system.txt 加载，文件缺失时回退到内置副本
# 修改提示词请直接编辑 scripts/prompts/fusion_system.txt
# ═══════════════════════════════════════════════════════════════

_FUSION_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "prompts", "fusion_system.txt"
)

_FALLBACK_SYSTEM_PROMPT = """把一份结构化命理数据写成一份给人看的性格分析。不学术、不鸡汤、不装。

# 禁止
- 八字术语（比劫、官杀、印星、食伤、财星、格局、身强身弱、调候、用神忌神等）
- 开场白、收尾语、行动清单。直接从全局诊断开始写，写完最后一个分析板块就结束
- "你是一个...的人""骨子里就是..."这类句式——直接说事，别总结
- 给概念加引号（"耗电""卡住""压力处理器"）
- 每句话都追求金句效果——正常说话不需要句句精彩
- 占位符或异常符号：禁止输出 %、{{变量}}、未替换模板、半截句
- 人格定死话术：避免"你就是""骨子里""注定""一定会"。可以判断倾向，但要保留场景条件。

# 怎么写
陈述事实，不表演。短句为主。可以指出矛盾，但不刻意制造戏剧性。

# 表达人格：知禾式表达
语气温和、耐心、清楚，像一位稳重的陪伴型分析者。先理解人的处境，再给判断；指出问题时不刺人，不贴死标签，不制造羞耻感。
复杂内容要拆开讲，用日常语言解释，不要堆概念。提醒要稳妥、有分寸，给用户选择空间；不要输出独立建议清单。
保持诚实，不为了温柔而回避矛盾；可以指出风险和代价，但要把话说得有分寸。不要过度安抚、不要鸡汤、不要像客服一样寒暄。

**双面原则：没有绝对的好或坏。关键特质要写出优势和代价；弱信号或中性信号不必强行双面。不给任何特质贴上纯粹正面或纯粹负面的标签。**
**跨维度联动：写完一个维度后，如果它跟其他维度有明显互动关系，点一笔。** 比如"社交偏内敛+决策果断"可能意味着团队中你容易独断——别人来不及了解你的想法，你已经拍板了。

# 判断边界
- 强信号可以明确写；弱信号只写倾向，不做定论。
- 结构化数据优先，RAG/参考规则只能辅助解释，不能覆盖当前数据。
- 遇到矛盾信号，先解释它们分别在哪些场景成立，再给综合判断。
- 家境、感情、健康相关内容必须谨慎表达，不做绝对断言。

# 输出结构

全局诊断（核心矛盾 + 一句解释为什么是关键。比如"责任感极强但表达欲偏低——对承诺极度认真，但不喜欢张扬地证明这一点，容易被低估"）

## 社交
## 感情
## 内心
## 决策
## 事业
## 财富观
## 家境（如有数据）

每节 2-4 句为主。重点写清楚性格机制、现实表现和可能代价，不输出建议清单。
**覆盖度要求：每个维度必须覆盖主要偏高或偏低的信号，但要合并同类项，不要逐条复述标签。** 比如社交维度同时收到"表达欲偏高"和"内敛度偏高"，要解释它们如何共存，而不是罗列成清单。

# 数据使用
- [全局主要矛盾]是全盘最高指令，所有板块要跟它一致
- [当前人生阶段]只用于调整场景感：中学生偏学业，大学生偏专业/实习，职场人偏职业。不要因此输出"立刻能做的事"或行动清单。
- [六维度信号] 是结构化定性标签（偏低/中位/偏高），不是描述文字。你需要自己解读这些信号之间的关系和矛盾，写出具体的性格表现。注意矛盾组合（如表达欲偏高+内敛度偏高=需要安全感才释放的表达者）
- [粒度性格特质] 是引擎从十神藏干和地支关系提取的具体行为倾向。每条特质有"所属维度"标签，优先把该维度标注的特质融入对应章节，**但不限于此——标注特质是起点，不是边界。你还需要根据十神组合、地支驱动、六维度信号等数据，推导出标注列表中没有覆盖到的性格表现**。四柱藏干特质是底层性格驱动力（来自地支藏干），十神加权特质是外在行为倾向。**和六维度信号的关系：六维度信号给数值框架（强度高低），粒度特质给具体描述（怎么表现）。优先结合六维度信号和粒度特质；如果某维度粒度特质不足，不要硬编，用六维度信号简要说明即可。** 粒度特质数量不同是正常的（如感情只有几条，内心有很多），数量少不等于该维度不重要——用六维度信号补充数值强度
- 表面矛盾要融合（如又爱学术又想搞钱→"知识付费赛道比纯学术更适合你"）
- 古代概念做现代翻译：参考[古今差异提示]
- 禁止古代职业建议、古代婚恋观、古代健康判词
- **禁止在报告中输出任何原始分数**：定性标签只能融入自然语言，不要机械列成"表达欲偏高、内敛度偏高"这种清单。
- **禁止输出底层术语**：如果数据或参考里出现"七杀/偏印/伤官/食伤/夫妻宫/日支/华盖/财破印/杀印相生/自刑"等词，必须翻译成现代行为语言再写。

# 多信号叠合（重要）
**不允许只看一个信号写结论。每个维度的描述要覆盖主要偏高或偏低信号，合并同类项，不逐条解释；有明显跨维度互动时再点出关系。**
具体方法：
1. **维度内叠合**：同一维度的多个信号一起看。如社交维度同时有"表达欲偏高"和"内敛度偏高"→写出两种倾向如何共存，什么场景下哪一种占主导。
2. **跨维度叠合**：不同维度之间相互影响。如"社交表达欲低"+"决策果断"→团队中可能独断不想解释；"内心情绪敏感"+"感情表达欲低"→心里有事但不说的类型。
3. **底层驱动解读**：每个维度的高/低信号不是孤立的，背后有底层行为驱动在共同作用。比如"决策维度的冒险倾向高"可能不是单纯冲动，而是机会敏感、风险承受和执行力叠加的结果。在分析中把这种驱动关系点出来。
4. **粒度特质印证**：粒度特质出现的场景就是该信号在现实生活中的表现方式。如果六维度信号显示"内敛度偏高"+粒度特质有"不善表达情感"，那这两个肯定是一个意思——在描述中要合并说，不要当两件事分开说。
5. **当代场景落地**：每个维度写完，要让读者能在脑海中对应到一个具体的日常场景——不是"你很内向"，而是"在聚会上你会找角落站着，但如果有一个人主动来找你聊专业话题，你会说很久"。
- **如果一个维度的全部信号都处于中位，不需要硬写，一句话带过即可。**
- **不要输出"立刻能做的事"、"建议"、"行动步骤"这类独立板块。**"""

def _load_system_prompt() -> str:
    try:
        with open(_FUSION_PROMPT_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            return content
    except FileNotFoundError:
        pass
    return _FALLBACK_SYSTEM_PROMPT

FUSION_SYSTEM_PROMPT = _load_system_prompt()

# 最终报告质量闸门：把模型偶发泄漏的术语和格式残留转成用户可读表达。
_REPORT_TERM_REPLACEMENTS: list[tuple[str, str]] = [
    ("比劫", "同辈竞争意识"),
    ("劫财", "竞争和资源分配压力"),
    ("比肩", "独立和同辈意识"),
    ("官杀混杂", "关系标准容易摇摆"),
    ("官杀", "责任和压力感"),
    ("正官", "规则感和责任感"),
    ("偏官", "压力反应和执行冲劲"),
    ("七杀", "压力反应和执行冲劲"),
    ("杀印相生", "高压执行力和深度分析相互配合"),
    ("印重身滞", "想得多、启动慢"),
    ("枭神夺食", "过度分析压住表达和行动"),
    ("枭神", "深度分析倾向"),
    ("偏印", "深度分析倾向"),
    ("正印", "吸收知识和寻求依据的倾向"),
    ("印星", "知识吸收和安全感需求"),
    ("伤官见官", "表达冲动和规则压力冲突"),
    ("伤官", "表达冲动和反规则倾向"),
    ("食神", "自我调节和表达舒展度"),
    ("食伤", "表达和创造力"),
    ("财破印", "短期收益和长期积累冲突"),
    ("正财", "务实和稳定收益意识"),
    ("偏财", "机会敏感度"),
    ("财星", "现实收益意识"),
    ("日支", "亲密关系位置"),
    ("夫妻宫", "亲密关系位置"),
    ("华盖星", "独处和精神探索倾向"),
    ("华盖", "独处和精神探索倾向"),
    ("多自刑", "自我拉扯和反复内耗"),
    ("自刑", "自我拉扯"),
    ("三合", "关系牵引"),
    ("六合", "关系牵引"),
    ("六冲", "关系冲突"),
    ("相冲", "关系冲突"),
    ("穿害", "隐性摩擦"),
    ("相害", "隐性摩擦"),
    ("桃花", "吸引力和情感机会"),
    ("格局", "整体结构"),
    ("调候", "环境适配"),
    ("用神", "有利因素"),
    ("忌神", "阻力因素"),
    ("身强身弱", "能量承载状态"),
    ("身强", "承载力偏强"),
    ("身弱", "承载力偏弱"),
]

_REPORT_HARDENING_REPLACEMENTS: list[tuple[str, str]] = [
    ("你是一个“被刺激才能启动”的人", "你更容易在明确压力或挑战出现后启动"),
    ("你是一个被刺激才能启动的人", "你更容易在明确压力或挑战出现后启动"),
    ("你更像个工程兵，不是总设计师", "你更擅长把复杂问题拆开落地；长期蓝图需要刻意训练"),
    ("不要平躺", "尽量避免长期停在缺乏挑战的状态里"),
    ("家里给不了太多金钱或人脉上的强力支持", "家里更像是提供基础支持，外部资源仍需要你自己争取"),
]

_REPORT_BANNED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\d+(?:\.\d+)?\s*分"),
    re.compile(r"%[^\n，。；]*"),
    re.compile(r"[A-Za-z_]+_PLACEHOLDER"),
    re.compile(r"\{\{.*?\}\}"),
]


def sanitize_fusion_report(text: str) -> str:
    """清理 LLM 最终报告中的术语泄漏、占位符和过硬断言。"""
    if not text:
        return text

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    for old, new in _REPORT_HARDENING_REPLACEMENTS:
        cleaned = cleaned.replace(old, new)
    for old, new in _REPORT_TERM_REPLACEMENTS:
        cleaned = cleaned.replace(old, new)

    # 当前产品形态只保留分析稿，不展示独立建议/行动板块。
    cleaned = re.sub(
        r"\n?#{0,3}\s*(立刻能做的事|建议|行动步骤)[：:：]?\s*\n[\s\S]*$",
        "",
        cleaned,
    )

    # 清理模型偶发的格式残留，比如“%的时间...”。
    cleaned = re.sub(r"%[^，。；\n]*", "", cleaned)
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*分", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.replace("（）", "").replace("()", "")
    return cleaned.strip()


def fusion_report_quality_issues(text: str) -> list[str]:
    """返回最终报告中仍然可检测的质量问题。"""
    issues: list[str] = []
    for term, _ in _REPORT_TERM_REPLACEMENTS:
        if term in text:
            issues.append(f"术语泄漏:{term}")
    for pat in _REPORT_BANNED_PATTERNS:
        if pat.search(text):
            issues.append(f"异常格式:{pat.pattern}")
    return issues

# ═══════════════════════════════════════════════════════════════
# 数据包构建
# ═══════════════════════════════════════════════════════════════

def _clean_ancient_refs(text: str) -> str:
    """清洗引擎标签：去古籍引用 + 拦截性别歧视 + 降级健康恐吓。"""
    import re

    # ── 1. 去古籍引用 ──
    text = re.sub(r'《[^》]+》[：:「][^」」]*[」」]', '', text)
    text = re.sub(r'《[^》]+》[^，。]*，', '', text)
    text = re.sub(r'【[^】]+】', '', text)

    # ── 2. 拦截性别歧视标签 ──
    _gender_bias = [
        (r'伤官克夫[^，。]*[，。]?', '性格独立，对伴侣要求高，传统关系中容易产生矛盾'),
        (r'克夫[^，。]*[，。]?', '对伴侣要求较高，需注意关系中的平等沟通'),
        (r'官杀混杂[^，。]*贱[^，。]*[，。]?', '面对多种选择时容易犹豫，需建立清晰的标准'),
        (r'女命不宜[^，。]*[，。]?', ''),
        (r'无官[^星]*星[^，。]*无夫[^，。]*[，。]?', '对传统婚姻制度的需求不强，更看重个人成长'),
        (r'夫星不[^，。]*[，。]?', '在感情中偏被动，需要时间建立信任'),
        (r'妾[^，。]*[，。]?', ''),
        (r'贱[^，。]*[，。]?', ''),
    ]
    for pattern, replacement in _gender_bias:
        text = re.sub(pattern, replacement, text)

    # ── 3. 降级健康恐吓措辞 ──
    _health_downgrade = [
        (r'此命多病', '体质偏弱，宜注意日常保养'),
        (r'夭[^，。]*[，。]?', ''),
        (r'短命[^，。]*[，。]?', ''),
        (r'早逝[^，。]*[，。]?', ''),
        (r'难养[^，。]*[，。]?', '养育需多加用心'),
        (r'体弱多病', '体质需多加关注'),
        (r'多病[^，。]*灾[^，。]*[，。]?', '需注意劳逸结合，定期体检'),
    ]
    for pattern, replacement in _health_downgrade:
        text = re.sub(pattern, replacement, text)

    # ── 4. 去残余古籍标注 ──
    text = re.sub(r'（《[^》]+》[^）]*）', '', text)
    text = re.sub(r'[（(]《[^》]+》[^）)]*[）)]', '', text)

    return text.strip()


def _score_to_band(val: float) -> str:
    """将原始数值(0-10)转为定性标签。"""
    if val >= 7:
        return "偏高"
    elif val >= 4:
        return "中位"
    else:
        return "偏低"


def _strip_score_text(text: str) -> str:
    """移除给 LLM 的文本中的原始分数片段。"""
    import re

    text = re.sub(r"[（(]\s*[-+]?\d+(?:\.\d+)?\s*分\s*[）)]", "", text)
    text = re.sub(r"[-+]?\d+(?:\.\d+)?\s*分", "", text)
    return text.strip()


def _sanitize_package(package: dict) -> dict:
    """将 LLM 数据包中的原始数值转换为定性标签。

    防止原始分数泄漏到 prompt 中导致 LLM 复读数字。
    内部规则数据不受影响。
    """
    import re

    # ── 0. 日主画像：去掉身强弱等文本中的原始分数 ──
    dm_profile = package.get("日主画像", {})
    if isinstance(dm_profile, dict):
        for key, val in list(dm_profile.items()):
            if isinstance(val, str):
                dm_profile[key] = _strip_score_text(val)

    # ── 1. 六维度信号：去掉综合分数，数值→定性标签 ──
    signals = package.get("六维度信号", {})
    for dim_name, dim_data in list(signals.items()):
        if not isinstance(dim_data, dict):
            continue
        # 去掉综合分数（内部聚合值，LLM 不需要）
        dim_data.pop("综合分数", None)
        # 数值 → 定性标签
        for key, val in list(dim_data.items()):
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)) and key not in ("身强弱修正",):
                dim_data[key] = _score_to_band(val)
        # 重新格式化 _需覆盖信号: "表达欲=8.0(偏高)" → "表达欲偏高"
        hint = dim_data.get("_需覆盖信号", "")
        if hint and isinstance(hint, str):
            parts = [p.strip() for p in hint.split("|")]
            parts = [p for p in parts if p and not p.startswith("综合分数=")]
            hint = " | ".join(parts)
            dim_data["_需覆盖信号"] = re.sub(
                r'(\w+)=[\d.]+\((偏高|偏低)\)', r'\1\2', hint
            )

    # ── 2. 十神加权特质：强度 → 强度定性 ──
    granular = package.get("粒度性格特质", {})
    weighted_traits = granular.get("十神加权特质", [])
    for item in weighted_traits:
        if "强度" in item:
            raw = item.pop("强度")
            item["强度定性"] = _score_to_band(raw)

    # ── 3. 十神强度排行：始终去掉原始强度，始终提供相对强度定性标签 ──
    ranking = package.get("十神强度排行", [])
    for item in ranking:
        s = item.pop("强度", 0)
        if s >= 5:
            item["相对强度"] = "偏高"
        elif s >= 2:
            item["相对强度"] = "正常"
        else:
            item["相对强度"] = "偏低"

    return package


def build_fusion_data_package(pr_dict: dict, family_dict: dict | None = None,
                              life_stage: str = "", age_info: dict | None = None) -> dict:
    """从 PersonalityResult + FamilyResult 构建 LLM 融合数据包。"""
    package: dict = {}

    # ── 命主基本信息 ──
    if life_stage:
        package["当前人生阶段"] = life_stage
    if age_info:
        package["日主信息"] = age_info

    # ── 古今差异说明 ──
    package["古今差异提示"] = (
        "以下引擎数据基于古代规则生成。做现代翻译：'爱读书'在现代=信息吸收力强/擅长考证学历/需要理论支撑后行动；"
        "'适合公务员'在现代=在大公司/体制/专业机构里发挥更好；'善于经营'在现代=数字资产/知识付费/技术变现等多元路径；"
        "'才艺'在现代=内容创作/技术创新/表达输出；'朋友多'在现代=社交网络/协作能力。"
        "过滤古籍引用和古代职业建议（考功名、走仕途等）。"
    )

    # ── 格局验证（成格/破格/带忌/不成格）──
    pattern_val = pr_dict.get("pattern_validation", {})
    if pattern_val:
        package["格局状态"] = {
            "判定": pattern_val.get("status", "不成格"),
            "说明": pattern_val.get("note", ""),
        }
        if pattern_val.get("status") == "破格":
            package["格局状态"]["提示"] = "当前格局已破，不要用此格局的特性来解读命主。请忽略引擎标签中格局相关描述，基于十神分布和病药组合来分析。"
        elif pattern_val.get("status") == "带忌":
            package["格局状态"]["提示"] = "格局成中有败，可以部分参考格局特性，但需标注矛盾。"
        elif pattern_val.get("status") == "成格":
            package["格局状态"]["提示"] = "格局成立，可以放心参考格局特性。"
        else:
            package["格局状态"]["提示"] = "格局信号偏弱，不建议强调格局特性，以实际十神分布为准。"

    # ── 全局最高指令（病药组合）──
    bingyao = pr_dict.get("bingyao_combos", [])
    if bingyao:
        top = bingyao[0]
        package["全局最高指令"] = f"{top['combo']}：{top['directive']}"
        if len(bingyao) > 1:
            package["次要病药"] = [
                f"{c['combo']}：{c['directive'][:150]}{'...' if len(c['directive']) > 150 else ''}"
                for c in bingyao[1:]
            ]

    # ── 日主核心（结构化数据，LLM自己写描述）──
    dm_core = pr_dict.get("day_master_core", {})
    if isinstance(dm_core, dict):
        package["日主画像"] = dm_core
    elif isinstance(dm_core, str) and dm_core:
        package["日主画像"] = {"原始描述": _clean_ancient_refs(dm_core[:300])}
    strength_label = pr_dict.get("strength_label", "")
    if strength_label and isinstance(package.get("日主画像"), dict):
        package["日主画像"]["身强弱"] = _clean_ancient_refs(strength_label[:100])

    # ── 关键组合（只传组合名+涉及十神，不传引擎结论）──
    special_combos_raw = []
    for combo in pr_dict.get("special_combos", [])[:8]:
        # 提取组合名（→之前的部分），去掉古籍引用和结论
        name_part = combo.split("→")[0].strip() if "→" in combo else combo[:80]
        # 去古籍引用
        cleaned = _clean_ancient_refs(name_part)
        if cleaned and not cleaned.startswith("──"):
            special_combos_raw.append(cleaned)
    package["关键组合"] = special_combos_raw

    # ── v0.15.0: 粒度性格特质（按六维度分组，LLM 无法跳过）──
    sub_traits = pr_dict.get("sub_traits", [])
    combo_traits = pr_dict.get("combo_traits", [])
    dizhi_traits = pr_dict.get("dizhi_traits", [])

    # 特质→维度映射（一个特质可属于多个维度）
    _TRAIT_DIMENSION_MAP: dict[str, list[str]] = {
        # 社交维度
        "分享表达欲": ["社交", "感情"], "才华外露": ["社交", "感情"],
        "毒舌犀利": ["社交"], "朋友多": ["社交"], "社交能量": ["社交"],
        "温和表达": ["社交"], "社交手腕": ["社交", "财富观"],
        "不喜冲突": ["社交"], "讲义气": ["社交"], "护短": ["社交"],
        "独处需求": ["社交", "内心"], "依赖性强": ["社交", "内心"],
        "不善表达情感": ["社交", "内心"], "好面子": ["社交", "内心"],
        "乐观豁达": ["社交", "内心"], "懒得争执": ["社交", "内心"],
        # 内心维度
        "深度思考": ["内心"], "钻牛角尖": ["内心"], "冷门兴趣": ["内心"],
        "直觉洞察": ["内心"], "情绪敏感": ["内心", "感情"],
        "多疑敏感": ["内心", "社交"], "完美主义": ["内心", "决策"],
        "审美挑剔": ["内心"], "自我意识强": ["内心", "决策"],
        "固执己见": ["内心", "决策"], "保守求稳": ["内心", "决策"],
        "心理压力": ["内心"], "心宽体胖": ["内心"],
        "爱读书思考": ["内心"], "仁慈包容": ["内心", "社交"],
        "贵人运": ["内心", "事业"], "重名誉": ["内心", "事业"],
        "博而不精": ["内心"], "安于现状": ["内心", "财富观"],
        "争强好胜": ["内心", "决策"],
        # 决策维度
        "果断勇猛": ["决策"], "急躁冲动": ["决策"],
        "冲动行事": ["决策"], "冒险精神": ["决策", "财富观"],
        "灵活变通": ["决策"], "危机嗅觉": ["决策"],
        "竞争意识": ["决策", "事业"], "反叛性": ["决策", "事业"],
        "不服权威": ["决策", "事业"], "报复心": ["决策", "社交"],
        "独立自主": ["决策", "事业"],
        # 事业维度
        "商业头脑": ["事业", "财富观"], "稳定追求": ["事业", "财富观"],
        "责任感": ["事业"], "处事周全": ["事业"], "守规矩": ["事业"],
        # 感情维度
        "情感丰富": ["感情"], "家庭观念": ["感情", "财富观"],
        "讲义气": ["社交", "感情"], "护短": ["社交", "感情"],
        "多疑敏感": ["内心", "感情"], "依赖性强": ["内心", "感情"],
        "不善表达情感": ["社交", "感情"], "冲动行事": ["决策", "感情"],
        "慷慨大方": ["财富观", "感情"], "保守求稳": ["内心", "感情"],
        # 财富观维度
        "务实节俭": ["财富观"], "慷慨大方": ["财富观"],
        "精打细算": ["财富观"], "花钱大手大脚": ["财富观"],
        "享受生活": ["财富观", "内心"],
    }

    def _assign_dimensions(trait_name: str) -> list[str]:
        return _TRAIT_DIMENSION_MAP.get(trait_name, ["内心"])  # 默认归内心

    if sub_traits or combo_traits or dizhi_traits:
        granular = {}

        # 四柱藏干特质（底层性格驱动力，优先级最高）
        hidden_all = [st for st in sub_traits if st.get("source_type")]
        if hidden_all:
            granular["四柱藏干特质"] = [
                {"特质": st["trait_name"], "描述": st["description"],
                 "来源": st.get("source_type", ""),
                 "所属维度": _assign_dimensions(st["trait_name"])}
                for st in hidden_all
            ]

        # 十神加权子特质（全局外在行为倾向）
        weighted_subs = [st for st in sub_traits if not st.get("source_type")]
        if weighted_subs:
            granular["十神加权特质"] = [
                {"特质": st["trait_name"], "描述": st["description"],
                 "十神": st.get("shishen", ""), "强度": st.get("score", 0),
                 "所属维度": _assign_dimensions(st["trait_name"])}
                for st in weighted_subs[:15]
            ]

        # 十神组合特质
        if combo_traits:
            granular["十神组合特质"] = [
                {"组合": ct.get("combo", ""), "特质": ct["trait"],
                 "描述": ct["description"]}
                for ct in combo_traits
            ]

        # 地支→性格
        if dizhi_traits:
            granular["地支驱动特质"] = [
                {"关系": dt.get("relation", ""), "特质": dt["trait"],
                 "描述": dt["description"]}
                for dt in dizhi_traits
            ]

        package["粒度性格特质"] = granular

    # ── 加权十神数据 ──
    weighted = pr_dict.get("weighted_shishen", {})
    sorted_scores: list[tuple[str, float]] = []
    if weighted:
        scores = weighted.get("scores", {})
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        package["十神强度排行"] = [
            {"十神": name, "强度": round(score, 1)} for name, score in sorted_scores[:8]
        ]
        # 注意：数值→定性标签的转换由 _sanitize_package() 统一处理
        # 月令五行/合局化神已去除（引擎内部字段，LLM 不需要）

    # ── 六维度结构化信号（LLM从零写描述，自由解释数值）──
    trait_signals = pr_dict.get("trait_signals", {})
    if trait_signals:
        # 给每个维度标注"需覆盖的信号"（偏离中位≥2的都要提到）
        _enriched = {}
        for dim in ["社交", "感情", "内心", "决策", "事业", "财富观"]:
            raw = trait_signals.get(dim, {})
            if not raw:
                _enriched[dim] = raw
                continue
            _hints = []
            for k, v in raw.items():
                if k == "综合分数" or isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)) and (v >= 7 or v <= 3):
                    _hints.append(f"{k}={v}" + ("(偏高)" if v >= 7 else "(偏低)"))
            for k, v in raw.items():
                if isinstance(v, list) and v:
                    _hints.append(f"{k}={v}")
                elif isinstance(v, str) and v and v not in ("平稳", "中和", "强", "弱"):
                    _hints.append(f"{k}={v}")
            _enriched[dim] = dict(raw)
            if _hints:
                _enriched[dim]["_需覆盖信号"] = " | ".join(_hints)
        package["六维度信号"] = _enriched
    else:
        # 回退：旧版 traits 文本（向后兼容）
        area_traits = pr_dict.get("traits", {})
        package["六维度信号"] = {
            "社交": _clean_ancient_refs(area_traits.get("社交", "")),
            "感情": _clean_ancient_refs(area_traits.get("感情", "")),
            "内心": _clean_ancient_refs(area_traits.get("内心", "")),
            "决策": _clean_ancient_refs(area_traits.get("决策", "")),
            "事业": _clean_ancient_refs(area_traits.get("事业", "")),
            "财富观": _clean_ancient_refs(area_traits.get("财富观", "")),
        }

    # ── 家境信息（如有）──
    if family_dict:
        fam_info = {}
        for key in ("level_label", "family_type", "surface", "reality", "childhood"):
            val = family_dict.get(key, "")
            if val:
                fam_info[key] = val
        if fam_info:
            package["家境背景"] = fam_info

    # ── 统一数据清洗：数值→定性标签 ──
    package = _sanitize_package(package)

    return package


def build_fusion_user_prompt(data_package: dict) -> str:
    """构建发给 LLM 的 User Prompt（数据 + RAG 参考知识 + 生成指令）。

    顺序：结构化数据 → RAG 参考片段 → 最终输出约束。
    输出约束放在最后，确保 LLM 在生成前最后看到的是输出规格。
    """
    parts: list[str] = []

    # 1. 结构化数据
    parts.append(
        "请根据以下结构化数据进行性格分析。\n\n"
        "【结构化数据】\n"
        f"{json.dumps(data_package, ensure_ascii=False, indent=2)}"
    )

    # 2. RAG 参考片段（中间）
    try:
        from .rag import retrieve_for_generation, format_snippets
        rag_snippets = retrieve_for_generation("personality", data_package, top_k=4)
        if rag_snippets:
            parts.append("")
            parts.append(format_snippets(rag_snippets, max_chars=1200))
    except Exception:
        pass

    # 3. 最终输出约束（结尾）
    parts.append("")
    parts.append(
        "【输出要求】\n"
        "- 严格按照系统提示的格式和约束输出。\n"
        "- 禁止在报告中出现任何原始分数或原始八字术语。\n"
        "- 每个维度优先解释主要矛盾，合并同类信号，不逐条罗列标签。\n"
        "- 如果全部信号处于中位，一句话带过即可。\n"
        "- 不输出“立刻能做的事”“建议”“行动步骤”等独立板块。"
    )

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# LLM 调用 — 流式
# ═══════════════════════════════════════════════════════════════

def generate_fusion_report(
    data_package: dict,
    on_chunk=None,
) -> str | None:
    """流式调用 DeepSeek API，生成融合报告。

    Args:
        data_package: build_fusion_data_package() 的输出
        on_chunk: 可选回调，每收到一个 token 时调用 on_chunk(token_text)

    Returns:
        完整的 LLM 生成文本。API 失败时返回 None。
    """
    if not DEEPSEEK_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY未设置")

    user_prompt = build_fusion_user_prompt(data_package)
    messages = [
        {"role": "system", "content": FUSION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": float(os.getenv("BAZI_FUSION_TEMPERATURE", "0.3")),
        "max_tokens": 4096,
    }

    full_text_parts: list[str] = []

    try:
        _timeout = 120.0
        with shared_client(_timeout) as client:
            with client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = ""
                    try:
                        body = resp.read().decode("utf-8", errors="replace")[:300]
                    except Exception:
                        pass
                    raise RuntimeError(f"API返回{resp.status_code}: {body}")

                for line in resp.iter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]  # remove "data: " prefix
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_text_parts.append(content)
                                if on_chunk:
                                    on_chunk(content)
                    except json.JSONDecodeError:
                        continue

        text = sanitize_fusion_report("".join(full_text_parts))
        if not text:
            raise RuntimeError("流式响应已完成但未收到任何内容")
        return text

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"API调用异常: {e}")


def generate_fusion_report_sync(data_package: dict) -> str | None:
    """同步（非流式）调用。API失败返回None（兼容旧调用方）。"""
    if not DEEPSEEK_KEY:
        return None

    user_prompt = build_fusion_user_prompt(data_package)
    messages = [
        {"role": "system", "content": FUSION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": float(os.getenv("BAZI_FUSION_TEMPERATURE", "0.3")),
        "max_tokens": 4096,
    }

    try:
        _timeout = 90.0 if "v4" in DEEPSEEK_MODEL.lower() else 30.0
        with shared_client(_timeout) as client:
            resp = client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                return None

            body = resp.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            return sanitize_fusion_report(content) if content else None

    except Exception:
        return None
