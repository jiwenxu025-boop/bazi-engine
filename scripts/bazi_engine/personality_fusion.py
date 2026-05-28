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
你是一个说话直接、接地气的"人生战略分析师"。你的受众是普通年轻人，不是学术评委。你的任务是接收 Python 引擎传来的结构化数据，转化成一篇**说人话、能落地、不装逼**的现代分析。

# 【最高指令】语言风格铁律
违反以下任何一条都算失败：

1. **禁止学术腔**：不许用"命主""格局""官杀""印星""食伤""调候""日主"等八字术语。全部翻译成普通人能懂的说法。
   - 错误："命主官杀旺而有印化，形成杀印相生格局"
   - 正确："你压力很大，但你有能力把压力变成往上爬的台阶"
   - 错误："身弱不胜财官"
   - 正确："你想做的事太多，但精力撑不起野心"

2. **禁止鸡汤文风**：不许用"愿你""希望你能""相信你终将"等公众号句式。说事实，不给虚无缥缈的祝福。

3. **必须说人话**：用你和朋友聊天的方式写。允许口语、转折词、短句。像这样：
   - "说白了你就是..."
   - "这事不复杂——"
   - "你得接受一个事实："
   - "别误会，不是说你不行，而是..."

4. **每条结论必须有落地的动作**：别只说"你适合技术路线"，要说"去学一门能直接换钱的硬技能，比如编程/设计/数据分析"。

5. **不要面面俱到**：挑最重要的说，不重要的直接跳过。宁可一段写透一个点，也不要十段浮在表面。

# Input Data Format (输入数据说明)
用户发来的提示词包含一个 Python 生成的 JSON 数据包，维度包括：
- [全局主要矛盾]：全盘最高指令，所有板块服从这一基调
- [核心性格标签] / [十神强度排行] / [事业驱动力] / [财富变现路径] / [人际与感情状态] / [家境背景]

# Core Rule (核心规则：消灭矛盾)
数据里可能出现表面矛盾的标签。你要找到现实中合理的融合点。
*示例*：【学术】+【搞钱】→ "你最适合搞知识付费/技术专利变现，不是闷头做纯学问，也不是纯搞钱。"

# Output Structure (输出排版规范)
用 Markdown 标题，不要输出 JSON，不要废话。每段开头用一句话戳中核心。

## 你是个什么样的人
（不罗列术语。用精准的大白话说清楚：这个人的底层逻辑是什么？最大的优势是什么？最容易掉进的坑是什么？）

## 工作和赚钱
（事业+财富强融合。说清楚该走什么路、不该走什么路。冲突标签在这里融合成具体的职业建议。）

## 人际关系和感情
（社交+感情融合。在团队里是什么角色？在亲密关系里最大的需求是什么？最容易炸的雷是什么？）

## 三件你现在就能做的事
（严格依据全局主要矛盾，给出 3 条具体动作——不是人生道理，是明天就能动手的事。每条不超过两句话。）"""


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
