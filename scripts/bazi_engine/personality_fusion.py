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
from dataclasses import dataclass

import httpx

# ── API 配置 ──
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
FUSION_ENABLED = os.getenv("BAZI_FUSION_ENGINE", "0") == "1"

# ═══════════════════════════════════════════════════════════════
# 系统提示词
# ═══════════════════════════════════════════════════════════════

FUSION_SYSTEM_PROMPT = """# Role (角色设定)
你是一个具备全局视野、精通现代心理学与商业逻辑的"人生战略分析师"。你的任务是接收底层 Python 引擎传来的多维度结构化数据，将其"缝合"并转化为一篇逻辑严密、富有洞察力且高度连贯的现代分析报告。

# Core Objective (核心目标：消灭矛盾，跨界融合)
你接收到的数据分属不同板块，有时会出现表面的"标签冲突"（例如：性格板块带有[清高/学术]标签，财富板块带有[强烈搞钱欲望]标签）。
**【绝对指令】**：你绝不能像机器人一样罗列矛盾的结论！你必须充当"戴维南等效源"，找到这些冲突标签的现实融合点。
*融合示例*：当【学术】遇上【搞钱】，不要说"你既适合做纯学者又适合经商"，而必须融合成："你最适合的路径是'知识付费'、'技术专利变现'或'将小众研究成果进行商业化落地'。"

# Input Data Format (输入数据说明)
用户发来的提示词将包含一个由 Python 生成的 JSON 数据包，包含以下维度：
- [全局主要矛盾/病药]：这是全盘的最高指令，其余所有板块的解读必须服从这一基调。
- [核心性格标签]
- [事业驱动力]
- [财富变现路径]
- [人际与感情状态]

# Output Structure (输出排版规范)
请用温暖、坚定、专业的语调，输出一篇不少于 800 字的综合解析，必须包含以下结构（请使用 Markdown 标题，不要输出 JSON 或多余的废话）：

## 核心能量画像 (Core Persona)
（不要罗列术语，用一段极其精准的现代语言，概括命主在这个社会上运作的核心底层逻辑。指出其最大的性格优势与最容易陷入的心理内耗陷阱。）

## 事业与财富的转化链路 (Career & Wealth)
（结合事业与财富板块的数据进行**强融合**。指出命主应该通过什么具体的技能或策略在这个商业社会立足，以及财富积累的最佳方式。如果存在冲突标签，必须在这里给出融合后的现代职业建议。）

## 圈层与亲密关系 (Social & Relationship)
（结合社交与感情板块的数据。分析命主在团队合作中的角色表现，以及在亲密关系中深层的安全感诉求和容易爆发的雷区。）

## 现代破局处方 (Actionable Advice)
（严格依据输入的[全局主要矛盾/病药]数据，给出 3 条在现代生活中可以立刻执行的物理动作或战略调整建议，帮助命主化解内耗或抓住机遇。）"""


# ═══════════════════════════════════════════════════════════════
# 数据包构建
# ═══════════════════════════════════════════════════════════════

def build_fusion_data_package(pr_dict: dict, family_dict: dict | None = None) -> dict:
    """从 PersonalityResult + FamilyResult 构建 LLM 融合数据包。

    Args:
        pr_dict: PersonalityResult.to_dict() 的输出
        family_dict: FamilyResult.to_dict() 的输出 (可选)

    Returns:
        规整的 JSON 数据包，可直接序列化后喂给 LLM
    """
    package: dict = {}

    # ── 全局最高指令（病药组合）──
    bingyao = pr_dict.get("bingyao_combos", [])
    if bingyao:
        # 取优先级最高的病药组合
        top = bingyao[0]
        package["全局最高指令"] = f"{top['combo']}：{top['directive']}"
        if len(bingyao) > 1:
            package["次要病药"] = [
                f"{c['combo']}：{c['directive'][:150]}..." for c in bingyao[1:]
            ]

    # ── 核心性格标签 ──
    traits = []
    dm_core = pr_dict.get("day_master_core", "")
    if dm_core:
        # 从日干核心提取第一句
        first_line = dm_core.split("\n")[0] if "\n" in dm_core else dm_core[:120]
        traits.append(first_line)

    dominant = pr_dict.get("dominant_ten_god", "")
    if dominant:
        traits.append(dominant)

    pattern_info = pr_dict.get("pattern_influence", "")
    if pattern_info:
        traits.append(pattern_info)

    strength_label = pr_dict.get("strength_label", "")
    if strength_label:
        traits.append(strength_label)

    # 从分领域 traits 中提取
    area_traits = pr_dict.get("traits", {})
    for area, desc in area_traits.items():
        if desc:
            traits.append(f"[{area}] {desc[:200]}")

    special_combos = pr_dict.get("special_combos", [])
    for combo in special_combos:
        traits.append(combo[:200])

    package["核心性格标签"] = traits

    # ── 加权十神数据 ──
    weighted = pr_dict.get("weighted_shishen", {})
    sorted_scores: list[tuple[str, float]] = []
    if weighted:
        scores = weighted.get("scores", {})
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        package["十神强度排行"] = [
            {"十神": name, "强度": round(score, 1)} for name, score in sorted_scores[:8]
        ]
        package["月令五行"] = weighted.get("month_wuxing", "未知")
        heju = weighted.get("heju_wuxing", {})
        if heju:
            package["合局化神"] = heju

    # ── 事业驱动力 ──
    career_tags = []
    if pattern_info:
        career_tags.append(f"格局影响: {pattern_info[:200]}")

    # 从十日神提取事业相关
    if sorted_scores:
        top3 = sorted_scores[:3]
        for name, score in top3:
            if name in ("正官", "偏官", "七杀"):
                career_tags.append(f"官杀旺({name} {score:.1f})→ 管理/体制/竞争型驱动力")
            elif name in ("食神", "伤官"):
                career_tags.append(f"食伤旺({name} {score:.1f})→ 创意/技术/表达型驱动力")
            elif name in ("正财", "偏财"):
                career_tags.append(f"财星旺({name} {score:.1f})→ 商业/经营/结果导向型驱动力")
            elif name in ("正印", "偏印"):
                career_tags.append(f"印星旺({name} {score:.1f})→ 学术/研究/专业型驱动力")
            elif name in ("比肩", "劫财"):
                career_tags.append(f"比劫旺({name} {score:.1f})→ 执行/合作/体力型驱动力")

    # 从格局提取
    for combo in special_combos:
        if any(kw in combo for kw in ("食神制", "伤官", "财", "官", "印", "杀")):
            career_tags.append(combo[:200])

    package["事业驱动力"] = career_tags if career_tags else ["十神分布均衡，驱动力多元化"]

    # ── 财富变现路径 ──
    wealth_tags = []
    cai_scores = {k: v for k, v in (weighted.get("scores", {})).items() if "财" in k}
    if cai_scores:
        for name, score in cai_scores.items():
            wealth_tags.append(f"{name}(强度{score:.1f})")
    else:
        wealth_tags.append("财星不显，需借助食伤/官杀间接生财")

    # 从格局提取
    for combo in special_combos:
        if "财" in combo:
            wealth_tags.append(combo[:200])

    package["财富变现路径"] = wealth_tags

    # ── 人际与感情状态 ──
    social_tags = []
    social_trait = area_traits.get("社交", "")
    if social_trait:
        social_tags.append(f"社交模式: {social_trait[:200]}")
    emotion_trait = area_traits.get("感情", "")
    if emotion_trait:
        social_tags.append(f"感情模式: {emotion_trait[:200]}")
    inner_trait = area_traits.get("内心", "")
    if inner_trait:
        social_tags.append(f"内心世界: {inner_trait[:200]}")

    # 日支状况
    stress = pr_dict.get("stress_profile", {}) or {}
    if stress and "_weighted_shishen" not in str(stress):
        for key in ("pressure_source", "defense_mechanism", "break_point"):
            val = stress.get(key, "")
            if val:
                social_tags.append(f"压力特征: {val[:200]}")

    package["人际与感情状态"] = social_tags if social_tags else ["社交模式无显著标签，待人接物较为随性"]

    # ── 家境信息（如有）──
    if family_dict:
        fam_info = {}
        for key in ("level_label", "family_type", "surface", "reality", "childhood"):
            val = family_dict.get(key, "")
            if val:
                fam_info[key] = val
        if fam_info:
            package["家境背景"] = fam_info

    return package


def build_fusion_user_prompt(data_package: dict) -> str:
    """构建发给 LLM 的 User Prompt"""
    return f"""请根据以下 Python 引擎提取的全盘底层数据，严格按照 System Prompt 的要求，生成一份综合融合报告。

【底层数据输入】：
{json.dumps(data_package, ensure_ascii=False, indent=2)}"""


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
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    full_text_parts: list[str] = []

    try:
        _timeout = 120.0  # 流式响应最长等待 2 分钟
        with httpx.Client(timeout=_timeout) as client:
            with client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    return None

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

        return "".join(full_text_parts) if full_text_parts else None

    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return None


def generate_fusion_report_sync(data_package: dict) -> str | None:
    """同步（非流式）调用，返回完整文本。适合不需要实时展示的场景。"""
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
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        _timeout = 90.0 if "v4" in DEEPSEEK_MODEL.lower() else 30.0
        with httpx.Client(timeout=_timeout) as client:
            resp = client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                return None

            body = resp.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content or None

    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return None
