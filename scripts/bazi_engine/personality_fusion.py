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
import threading
from contextlib import suppress

from ._deepseek_config import (
    DEEPSEEK_API_URL,
    DEEPSEEK_KEY,
    DEEPSEEK_MODEL,
)
from ._http import shared_client
from ._token_budget import prepare_messages_for_request
from .personality_analysis.evidence import (
    build_fusion_signals_from_evidence,
    build_fusion_trait_signals,
    normalize_strength_label,
    weighted_score_level,
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
- 八字术语（比劫、官杀、印星、食伤、财星、藏干、格局、身强身弱、调候、用神忌神等）
- 开场白、收尾语、行动清单。直接从“核心画像”开始写，写完“重点分析”就结束
- "你是一个...的人""骨子里就是..."这类句式——直接说事，别总结
- 给概念加引号（"耗电""卡住""压力处理器"）
- 每句话都追求金句效果——正常说话不需要句句精彩
- 占位符或异常符号：禁止输出 %、{{变量}}、未替换模板、半截句
- 人格定死话术：避免"你就是""骨子里""注定""一定会"。可以判断倾向，但要保留场景条件。
- 网络梗、贬损型比喻和制造羞耻感的反差，例如“反复横跳”“行动开关失灵”“理论上的巨人，行动上的矮子”。

# 怎么写
陈述事实，不表演。短句为主。可以指出矛盾，但不刻意制造戏剧性。
先写最有辨识度、最容易被本人验证的部分，再补充解释。年轻化不等于堆网络热词，不使用“社恐”“恋爱脑”“卷王”等流行标签代替分析。
优先使用能被观察到的当代生活场景，例如群聊、陌生人聚会、合作分工、截止日期、亲密沟通和消费选择；场景必须与[当前人生阶段]匹配，不能为了画面感硬编经历。

# 表达人格：知禾式表达
语气温和、耐心、清楚，像一位稳重的陪伴型分析者。先理解人的处境，再给判断；指出问题时不刺人，不贴死标签，不制造羞耻感。
复杂内容要拆开讲，用日常语言解释，不要堆概念。提醒要稳妥、有分寸，给用户选择空间。
保持诚实，不为了温柔而回避矛盾；可以指出风险和代价，但要把话说得有分寸。不要过度安抚、不要鸡汤、不要像客服一样寒暄。

**双面原则：没有绝对的好或坏。关键特质要写出优势和代价；弱信号或中性信号不必强行双面。不给任何特质贴上纯粹正面或纯粹负面的标签。**
**跨维度联动：写完一个维度后，如果它跟其他维度有明显互动关系，点一笔。** 比如"社交偏内敛+决策果断"可能意味着团队中你容易独断——别人来不及了解你的想法，你已经拍板了。

# 判断边界
- 强信号可以明确写；弱信号只写倾向，不做定论。
- 结构化数据优先；组合候选只能交叉核对，不能单独生成结论。
- 遇到矛盾信号，先解释它们分别在哪些场景成立，再给综合判断。
- 感情和健康相关内容必须谨慎表达，不做绝对断言；禁止输出心理或医学诊断。

# 生成前的人物建模（只在内部完成，不要输出过程）
1. 从六维度中提炼一条至少由两个领域共同支持的核心驱动力，作为全文人物主线。
2. 找出1-2组最有依据的内在拉扯；矛盾不是互相抵消，而是要说明它们分别在什么场景、关系距离或压力状态下更容易出现。
3. 找出至少2处有依据的跨维度影响，例如内心处理方式如何影响决策、社交方式如何影响事业协作。依据不足时宁可少写，不得硬连。
4. 区分强信号、普通信号和较弱信号，决定各板块篇幅与语气，不把六个板块写成同样重要。
5. 规划完成后只输出正式报告，不得展示“核心驱动力”“内在拉扯”“行为链”等分析过程或标签。

# 输出结构

## 核心画像
60-100字。用核心驱动力和最有辨识度的一组拉扯建立人物主线，让后面六个领域像在解释同一个人。不要使用“你是一个……的人”这类空泛定义，也不要在这里重复后文的具体场景。

## 重点分析
必须按社交、感情、内心、决策、事业、财富观的顺序写满6个主题，每个领域单独出现一次，不得省略或合并标题。每个主题使用“### 【领域】具体标题”：领域标签用于导航，后半句必须概括该领域真实的矛盾或表现，不能只有“社交”“内心”这类维度名。跨维度联动写进正文，不使用跨领域合并标题。
按证据强弱分配篇幅，不要求六个主题等长：强信号或矛盾信号可写80-110字、2-3句，普通或弱信号写40-70字、1-2句。每段自然组成一条小型行为链，在“触发场景、内在处理、外在表现、带来的优势或代价、适用边界”中至少写清3项；不要把这些名称直接写成小标题。优先说明“在什么情况下更容易这样”，避免把倾向写成全天候人格。能解释“容易被误解”的落差时，直接写进对应主题，不另起板块。信号中等、较弱或较少时也要保留对应主题，但只能保守描述数据支持的倾向和适用边界，不能用空话或虚构经历凑数。

六个主题必须围绕核心画像中的同一条人物主线，但不能换词重复同一句结论。全文至少自然串联2处有依据的跨维度影响；存在矛盾信号时，至少解释1组倾向如何随场景切换。不要连续使用“你比较……”“你也比较……”罗列标签。

全文控制在500-800个汉字左右。六个领域都要覆盖，同时把更多篇幅留给证据充分、辨识度高的部分。不要输出开场白、总结、收尾语或建议清单。

# 数据使用
- [组合候选]只表示工程规则命中，不是最高指令；必须有六维度中的不同字段相互印证才可使用。
- [当前人生阶段]只用于调整场景感：中学生偏学业，大学生偏专业/实习，职场人偏职业。不要因此输出"立刻能做的事"或行动清单。
- [六维度信号] 已按字段语义处理。强度字段使用较弱/中等/较强；事业方向只表示本盘内相对排序，不能把“方向接近”写成能力偏低。
- 表面矛盾要融合，但不能据此虚构具体职业、赛道、收入方式或人生经历。只解释数据支持的行为机制。
- 严格遵守[证据边界]，传统结构名称不能直接等同于现代心理特征。
- 禁止古代职业建议、古代婚恋观、古代健康判词
- **禁止在报告中输出任何原始分数**：定性标签只能融入自然语言，不要机械列成"表达欲较强、内敛度较强"这种清单。
- **禁止输出底层术语**：如果数据或参考里出现"七杀/偏印/伤官/食伤/夫妻宫/日支/华盖/财破印/杀印相生/自刑"等词，必须翻译成现代行为语言再写。

# 多信号叠合（重要）
**不允许只看一个信号写结论。六个领域必须逐一覆盖，但优先级仍是辨识度高于平均篇幅：证据充分的领域展开写，普通或弱信号领域简写，合并同类项，不逐条解释；有明显跨维度互动时再点出关系。**
具体方法：
1. **维度内叠合**：同一维度的多个信号一起看。如社交维度同时有"表达欲较强"和"内敛度较强"→写出两种倾向如何共存，什么场景下哪一种占主导。
2. **跨维度叠合**：不同维度之间相互影响，但不得从两个分值直接编造具体经历。
3. **底层驱动解读**：每个维度的高/低信号不是孤立的，背后有底层行为驱动在共同作用。比如"决策维度的冒险倾向高"可能不是单纯冲动，而是机会敏感、风险承受和执行力叠加的结果。在分析中把这种驱动关系点出来。
4. **当代场景落地**：每个重点主题都要让读者能在脑海中对应到一个具体的日常场景——不是"你很内向"，而是"在聚会上你通常先观察，但遇到真正感兴趣的话题会聊得很深"。场景用于解释信号，不得假装知道用户实际发生过什么。
- **如果一个维度的全部信号都处于中等，只写数据支持的温和倾向或场景差异，不把“中等”硬说成鲜明特质。**
- **不要输出"立刻能做的事"、"建议"、"行动步骤"这类独立板块。**"""

def _load_system_prompt() -> str:
    try:
        with open(_FUSION_PROMPT_PATH, encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            return content
    except FileNotFoundError:
        pass
    return _FALLBACK_SYSTEM_PROMPT

FUSION_SYSTEM_PROMPT = _load_system_prompt()
FUSION_PROMPT_VERSION = "2026-07-19-human-portrait-v5"

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
    ("日支藏干", "亲密关系中的底层倾向"),
    ("日支", "亲密关系位置"),
    ("夫妻宫", "亲密关系位置"),
    ("藏干", "底层倾向"),
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
    ("理论上的巨人，行动上的矮子", "理解得很深，行动却容易晚一步"),
    ("行动开关失灵", "理解充分后仍难启动"),
    ("反复横跳", "反复拉扯"),
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

    def _qualitative_percentage(match: re.Match[str]) -> str:
        value = float(match.group(1))
        if value >= 80:
            return "大部分"
        if value >= 60:
            return "多数"
        if value >= 40:
            return "接近一半"
        if value >= 20:
            return "一部分"
        return "少量"

    # 百分数先转为定性表达，避免后续移除“%”时留下残缺数字和半截句。
    cleaned = re.sub(r"(\d+(?:\.\d+)?)\s*%", _qualitative_percentage, cleaned)

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


_REPORT_REQUIRED_SECTIONS = ("核心画像", "重点分析")
_REPORT_REMOVED_SECTIONS = ("最像你的三个瞬间", "容易被误解的一面")
_FOCUS_DOMAINS = ("社交", "感情", "内心", "决策", "事业", "财富观")
_FOCUS_TOPIC_LABEL = rf"【({'|'.join(_FOCUS_DOMAINS)})】"
_FOCUS_TOPIC_PATTERN = re.compile(rf"{_FOCUS_TOPIC_LABEL}\s*\S.+")
_FOCUS_TOPIC_SECTION_PATTERN = re.compile(
    r"^###\s*(.+?)\s*$\n([\s\S]*?)(?=^###\s|\Z)",
    re.MULTILINE,
)


def fusion_report_structure_issues(text: str) -> list[str]:
    """检查会明显破坏阅读体验的结构问题，不追逐轻微字数波动。"""
    issues: list[str] = []
    normalized = text.strip()

    for title in _REPORT_REQUIRED_SECTIONS:
        if not re.search(rf"^#{{1,3}}\s*{re.escape(title)}\s*$", normalized, re.MULTILINE):
            issues.append(f"缺少板块:{title}")

    topics_match = re.search(
        r"^#{1,3}\s*重点分析\s*$([\s\S]*)$",
        normalized,
        re.MULTILINE,
    )
    if topics_match:
        topic_sections = _FOCUS_TOPIC_SECTION_PATTERN.findall(topics_match.group(1))
        topic_titles = [title for title, _ in topic_sections]
        topic_count = len(topic_titles)
        if topic_count != len(_FOCUS_DOMAINS):
            issues.append(f"重点主题数量:{topic_count}")
        topic_matches = [_FOCUS_TOPIC_PATTERN.fullmatch(title) for title in topic_titles]
        if topic_titles and any(match is None for match in topic_matches):
            issues.append("重点主题标签不合格")
        covered_domains = [match.group(1) for match in topic_matches if match]
        missing_domains = [domain for domain in _FOCUS_DOMAINS if domain not in covered_domains]
        if missing_domains:
            issues.append(f"重点主题缺少领域:{'、'.join(missing_domains)}")
        duplicate_domains = [
            domain for domain in _FOCUS_DOMAINS if covered_domains.count(domain) > 1
        ]
        if duplicate_domains:
            issues.append(f"重点主题重复领域:{'、'.join(duplicate_domains)}")

        normalized_bodies: dict[str, str] = {}
        short_domains: list[str] = []
        repeated_domains: list[str] = []
        for (title, body), match in zip(topic_sections, topic_matches, strict=True):
            domain = match.group(1) if match else title
            normalized_body = re.sub(r"\s+", "", body)
            if len(normalized_body) < 30:
                short_domains.append(domain)
                continue
            if normalized_body in normalized_bodies:
                repeated_domains.extend((normalized_bodies[normalized_body], domain))
            else:
                normalized_bodies[normalized_body] = domain
        if short_domains:
            issues.append(f"重点主题内容过短:{'、'.join(dict.fromkeys(short_domains))}")
        if repeated_domains:
            issues.append(f"重点主题内容重复:{'、'.join(dict.fromkeys(repeated_domains))}")

    for title in _REPORT_REMOVED_SECTIONS:
        if re.search(rf"^#{1,3}\s*{re.escape(title)}\s*$", normalized, re.MULTILINE):
            issues.append(f"多余板块:{title}")

    if len(normalized) < 420:
        issues.append(f"篇幅过短:{len(normalized)}")
    elif len(normalized) > 1050:
        issues.append(f"篇幅过长:{len(normalized)}")

    if normalized and normalized[-1] not in "。！？!?":
        issues.append("结尾残缺")
    return issues


def _repair_fusion_report(
    text: str,
    issues: list[str],
    data_package: dict | None = None,
    cancel_event: threading.Event | None = None,
) -> str | None:
    """对明显不合格的报告做一次低温修订；失败时由调用方保留原文。"""
    if cancel_event and cancel_event.is_set():
        return None
    six_domain_signals = (data_package or {}).get("六维度信号", {})
    signals_text = json.dumps(six_domain_signals, ensure_ascii=False, indent=2)
    messages = [
        {"role": "system", "content": FUSION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "下面的报告已经完成事实分析。只根据待修订报告和所附六维度信号修订结构与表达，"
                "不添加任何其他事实、职业、经历或建议。\n"
                f"需要修复的问题：{'；'.join(issues)}\n"
                "核心画像必须用共同驱动力和主要拉扯建立人物主线，六个主题要像在解释同一个人，不能各说各话。"
                "必须保留核心画像和重点分析两个板块；重点分析按顺序写满社交、感情、内心、决策、事业、财富观六个主题，"
                "每个领域单独出现一次并使用“### 【领域】具体标题”，不得省略、重复或使用跨领域合并标题。"
                "每段从触发场景、内在处理、外在表现、优势或代价、适用边界中自然写清至少3项，不显示这些过程标签。"
                "强信号多写，普通或弱信号少写；信号中等或较少时只做保守表述，不得重复段落。"
                "全文自然串联至少2处有依据的跨维度影响；存在矛盾信号时，解释它们如何随场景切换。"
                "总长度控制在500-800个汉字左右。"
                "直接输出修订后的完整报告，不解释修改过程。\n\n"
                f"【六维度信号】\n{signals_text}\n\n"
                f"【待修订报告】\n{text}"
            ),
        },
    ]
    max_output_tokens = 1800
    messages = prepare_messages_for_request(
        messages,
        DEEPSEEK_MODEL,
        max_output_tokens,
        operation="personality_fusion_repair",
    )
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.1,
        "max_tokens": max_output_tokens,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }

    try:
        if cancel_event and cancel_event.is_set():
            return None
        _timeout = 90.0 if "v4" in DEEPSEEK_MODEL.lower() else 45.0
        with shared_client(_timeout) as client:
            resp = client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                return None
            body = resp.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            return sanitize_fusion_report(content) if content else None
    except Exception:
        return None


def _finalize_fusion_report(
    text: str,
    result_metadata: dict | None = None,
    data_package: dict | None = None,
    cancel_event: threading.Event | None = None,
) -> str:
    """清洗报告，并在严重结构问题出现时最多修订一次。"""
    cleaned = sanitize_fusion_report(text)
    issues = fusion_report_quality_issues(cleaned) + fusion_report_structure_issues(cleaned)

    def record_metadata(repaired: bool) -> None:
        if result_metadata is not None:
            result_metadata.update({
                "prompt_version": FUSION_PROMPT_VERSION,
                "model": DEEPSEEK_MODEL,
                "temperature": float(os.getenv("BAZI_FUSION_TEMPERATURE", "0.3")),
                "repaired": repaired,
            })

    if (
        not issues
        or os.getenv("BAZI_FUSION_REPAIR", "1") != "1"
        or (cancel_event and cancel_event.is_set())
    ):
        record_metadata(False)
        return cleaned

    if cancel_event is None:
        repaired = _repair_fusion_report(cleaned, issues, data_package)
    else:
        repaired = _repair_fusion_report(
            cleaned, issues, data_package, cancel_event=cancel_event,
        )
    if not repaired:
        record_metadata(False)
        return cleaned

    repaired_issues = fusion_report_quality_issues(repaired) + fusion_report_structure_issues(repaired)
    use_repaired = len(repaired_issues) < len(issues)
    record_metadata(use_repaired)
    return repaired if use_repaired else cleaned

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


def _strip_score_text(text: str) -> str:
    """移除给 LLM 的文本中的原始分数片段。"""
    import re

    text = re.sub(r"[（(]\s*[-+]?\d+(?:\.\d+)?\s*分\s*[）)]", "", text)
    text = re.sub(r"[-+]?\d+(?:\.\d+)?\s*分", "", text)
    return text.strip()


def _sanitize_package(package: dict) -> dict:
    """Remove raw scores from the already field-aware LLM package.

    Field classification happens before this function. This final pass only
    protects against score leakage from compatibility payloads.
    """
    dm_profile = package.get("日主画像", {})
    if isinstance(dm_profile, dict):
        for key, val in list(dm_profile.items()):
            if isinstance(val, str):
                dm_profile[key] = _strip_score_text(val)

    ranking = package.get("十神强度排行", [])
    for item in ranking:
        if "强度" in item:
            item["工程强度档"] = weighted_score_level(item.pop("强度"))

    return package


def build_fusion_data_package(pr_dict: dict, family_dict: dict | None = None,
                              life_stage: str = "", age_info: dict | None = None) -> dict:
    """从 PersonalityResult + FamilyResult 构建 LLM 融合数据包。"""
    package: dict = {}
    evidence_view = pr_dict.get("evidence_view", {}) or {}
    evidence_status = evidence_view.get("status", {}) or {}

    # ── 命主基本信息 ──
    if life_stage:
        package["当前人生阶段"] = life_stage
    if age_info:
        package["日主信息"] = age_info

    package["证据边界"] = (
        "以下内容是传统规则启发的工程信号，不是概率、准确率或临床测量。"
        "只描述多个结构化信号共同支持、且用户能够现实核对的行为倾向；"
        "不得推导心理诊断、职业、收入、健康、家庭经历或确定事件。"
    )

    # ── 格局验证（成格/破格/带忌/不成格）──
    pattern_val = pr_dict.get("pattern_validation", {}) or {}
    pattern_status = pattern_val.get("status") or evidence_status.get("pattern_status", "")
    pattern_name = evidence_status.get("pattern", "")
    if pattern_status or pattern_name:
        package["格局状态"] = {"证据等级": "传统结构候选"}
        if pattern_name:
            package["格局状态"]["名称"] = pattern_name
        if pattern_status:
            package["格局状态"]["判定"] = pattern_status
        if pattern_status == "破格":
            package["格局状态"]["使用边界"] = "不使用格局特性下结论"
        elif pattern_status == "带忌":
            package["格局状态"]["使用边界"] = "只能与其他信号交叉核对"
        elif pattern_status == "成格":
            package["格局状态"]["使用边界"] = "仍不能单独推导现代人格"
        else:
            package["格局状态"]["使用边界"] = "不强调格局特性"

    # 病药检测只提供候选名称。未经验证的心理因果和行动指令不进入 LLM。
    bingyao = pr_dict.get("bingyao_combos", [])
    if bingyao:
        package["组合候选"] = [
            {"名称": item.get("combo", ""), "证据等级": "工程规则候选"}
            for item in bingyao[:3]
            if item.get("combo")
        ]

    # 仅保留结构字段，移除未经验证的性格、道德和职业描述。
    dm_core = pr_dict.get("day_master_core", {})
    if isinstance(dm_core, dict):
        package["日主画像"] = {
            key: dm_core[key]
            for key in ("五行", "阴阳")
            if dm_core.get(key)
        }
    strength_label = pr_dict.get("strength_label") or evidence_status.get("strength", "")
    if strength_label:
        package.setdefault("日主画像", {})
        package["日主画像"]["身强弱"] = normalize_strength_label(strength_label)

    # 子特质名称含现代人格、道德和职业断言；原文与验证未补齐前不进入融合输入。

    # ── 加权十神数据 ──
    weighted = pr_dict.get("weighted_shishen", {})
    sorted_scores: list[tuple[str, float]] = []
    if weighted:
        scores = weighted.get("scores", {})
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        package["十神强度排行"] = [
            {"十神": name, "强度": round(score, 1)} for name, score in sorted_scores[:8]
        ]
    elif evidence_view.get("weighted_scores"):
        package["十神强度排行"] = [
            {"十神": item.get("name", ""), "工程强度档": item.get("level", "")}
            for item in evidence_view["weighted_scores"][:8]
            if item.get("name")
        ]

    trait_signals = pr_dict.get("trait_signals", {})
    if trait_signals:
        package["六维度信号"] = build_fusion_trait_signals(trait_signals)
    elif evidence_view.get("dimensions"):
        package["六维度信号"] = build_fusion_signals_from_evidence(evidence_view["dimensions"])
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

    # 家境规则仍在溯源，不进入性格融合；保留参数只为兼容调用契约。
    del family_dict

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

    # Personality references currently mix classical summaries and single-case
    # notes. Keep retrieval opt-in until evidence grades are available.
    if os.getenv("BAZI_PERSONALITY_RAG", "0") == "1":
        try:
            from .rag import format_snippets, retrieve_for_generation
            rag_snippets = retrieve_for_generation("personality", data_package, top_k=2)
            if rag_snippets:
                parts.append("")
                parts.append(format_snippets(rag_snippets, max_chars=800))
        except Exception:
            pass

    # 3. 最终输出约束（结尾）
    parts.append("")
    parts.append(
        "【输出要求】\n"
        "- 严格按照系统提示的格式和约束输出。\n"
        "- 禁止在报告中出现任何原始分数或原始八字术语。\n"
        "- 输出前在内部提炼共同驱动力、主要拉扯、场景切换和跨维度影响，不展示规划过程。\n"
        "- 核心画像建立贯穿全文的人物主线，后面六个主题必须像在解释同一个人，不能各说各话。\n"
        "- 先写核心画像，再按社交、感情、内心、决策、事业、财富观的顺序写满六个主题，每个领域单独出现一次。\n"
        "- 每个主题必须写成“### 【领域】具体标题”，不得省略、重复或使用跨领域合并标题；跨维度联动写进正文。\n"
        "- 六个领域不要求等长：强信号展开写，普通或弱信号简写；合并同类信号，不逐条罗列标签。\n"
        "- 每段从触发场景、内在处理、外在表现、优势或代价、适用边界中自然写清至少3项，不显示这些过程标签。\n"
        "- 全文自然串联至少2处有依据的跨维度影响；存在矛盾信号时，解释它们如何随场景切换。\n"
        "- 中等、较弱或信号较少的领域也要保留，但只做有依据的保守表述，不用空话或虚构经历凑数。\n"
        "- 组合候选和粒度候选不能单独生成结论，至少需要两个不同字段相互印证。\n"
        "- 全文控制在500-800个汉字左右，不使用网络热词、贬损比喻代替分析。\n"
        "- 不输出“立刻能做的事”“建议”“行动步骤”等独立板块。"
    )

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# LLM 调用 — 流式
# ═══════════════════════════════════════════════════════════════

def generate_fusion_report(
    data_package: dict,
    on_chunk=None,
    result_metadata: dict | None = None,
    cancel_event: threading.Event | None = None,
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
    if cancel_event and cancel_event.is_set():
        return None

    user_prompt = build_fusion_user_prompt(data_package)
    messages = [
        {"role": "system", "content": FUSION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    max_output_tokens = 4096
    messages = prepare_messages_for_request(
        messages,
        DEEPSEEK_MODEL,
        max_output_tokens,
        operation="personality_fusion_stream",
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": float(os.getenv("BAZI_FUSION_TEMPERATURE", "0.3")),
        "max_tokens": max_output_tokens,
    }

    full_text_parts: list[str] = []

    try:
        if cancel_event and cancel_event.is_set():
            return None
        _timeout = 120.0
        with (
            shared_client(_timeout) as client,
            client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers) as resp,
        ):
            if resp.status_code != 200:
                body = ""
                with suppress(Exception):
                    body = resp.read().decode("utf-8", errors="replace")[:300]
                raise RuntimeError(f"API返回{resp.status_code}: {body}")

            for line in resp.iter_lines():
                if cancel_event and cancel_event.is_set():
                    return None
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
                            if on_chunk and not (cancel_event and cancel_event.is_set()):
                                on_chunk(content)
                except json.JSONDecodeError:
                    continue

        text = _finalize_fusion_report(
            "".join(full_text_parts),
            result_metadata,
            data_package,
            cancel_event=cancel_event,
        )
        if not text:
            raise RuntimeError("流式响应已完成但未收到任何内容")
        return text

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"API调用异常: {e}") from e


def generate_fusion_report_sync(data_package: dict) -> str | None:
    """同步（非流式）调用。API失败返回None（兼容旧调用方）。"""
    if not DEEPSEEK_KEY:
        return None

    user_prompt = build_fusion_user_prompt(data_package)
    messages = [
        {"role": "system", "content": FUSION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    max_output_tokens = 4096
    messages = prepare_messages_for_request(
        messages,
        DEEPSEEK_MODEL,
        max_output_tokens,
        operation="personality_fusion_sync",
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": float(os.getenv("BAZI_FUSION_TEMPERATURE", "0.3")),
        "max_tokens": max_output_tokens,
    }

    try:
        _timeout = 90.0 if "v4" in DEEPSEEK_MODEL.lower() else 30.0
        with shared_client(_timeout) as client:
            resp = client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                return None

            body = resp.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            return _finalize_fusion_report(content, data_package=data_package) if content else None

    except Exception:
        return None
