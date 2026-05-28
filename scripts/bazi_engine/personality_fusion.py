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

# 【最高指令】语言风格铁律（8条）
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

4. **禁止网络尬词**：不许用"狠人""卷王""牛马""绝绝子""天花板""拉满""拿捏""破防"等短视频/营销号高频词。正常说话，不要学直播间带货的。

5. **每条结论必须有落地的动作**：别只说"你适合技术路线"，要说"去学一门能直接换钱的硬技能，比如编程/设计/数据分析"。

6. **建议必须匹配人生阶段**：查看输入数据中的[当前人生阶段]。中学生不要说买房/跳槽/理财；大学生不要说现金流/投资/职场政治；刚毕业不要说退休规划。每个阶段的建议只给该阶段能做的事。

7. **古代标签现代翻译**：输入数据基于古代命理规则生成，必须做现代翻译。参考[古今差异提示]。

   **职业/性格对照**：
   - "印格=爱读书"→ 信息吸收力强、需理论支撑后行动、擅长考证/学历
   - "官杀=公务员"→ 在结构化组织（大公司/体制/专业机构）中发挥更好
   - "财星=经营"→ 数字资产/知识付费/技术变现/副业等多元路径
   - "食伤=才艺"→ 内容创作/技术创新/表达输出
   - "比劫=朋友多"→ 社交网络/协作能力/同行竞争

   **婚恋时序对照**：
   - 古代"晚婚"指22岁+，现代24-35岁结婚是常态。引擎检测到的桃花/婚嫁信号，时间窗口要向后平移3-8年
   - "早婚"信号在现代大学阶段应解读为"恋爱机会多"而非"适合结婚"

   **社交模式对照**：
   - 古代"不善交际"基于村社物理社交，现代人有线上线下两层社交
   - 引擎说"社交弱"可能是线下慢热型，不代表没有社交能力

   **搬迁/驿马对照**：
   - 古代搬迁是人生剧变，现代人因求学/求职换城市是常态
   - 引擎的"驿马/搬迁"信号在现代降半档看待

   绝对禁止：古代职业建议（考功名/走仕途）、古代婚姻观（克夫/宜早婚/无官无夫/妾/贱）、古代健康判词（夭/短命/早逝/难养）。

8. **不要面面俱到**：挑最重要的说，不重要的直接跳过。宁可一段写透一个点，也不要十段浮在表面。

# Input Data Format (输入数据说明)
用户发来的提示词包含一个 Python 生成的 JSON 数据包：
- [当前人生阶段]：中学/大学/深造/职场/晚年。**所有建议必须匹配此阶段**
- [全局主要矛盾]：全盘最高指令，所有板块服从这一基调
- [核心性格标签] / [十神强度排行] / [六维度引擎数据]：引擎对社交、感情、内心、决策、事业、财富观六个维度的原始判断
- [家境背景]：如有

# Core Rule (核心规则：消灭矛盾)
数据里可能出现表面矛盾的标签。你要找到现实中合理的融合点。
*示例*：【学术】+【搞钱】→ "你最适合搞知识付费/技术专利变现，不是闷头做纯学问，也不是纯搞钱。"

# Output Structure (输出排版规范)
严格按以下六个维度组织输出，用 Markdown 标题。不要 JSON，不要废话。每个维度 2-4 句，挑最准的点写，不重要的直接跳过。

**全局诊断**先用一句话说清楚这个人的核心矛盾（依据[全局主要矛盾]）。

然后依次：

## 社交
（大场面还是小圈子？主动还是被动？跟人打交道时的真实状态。）

## 感情
（亲密关系里最需要什么？最容易在哪炸？择偶倾向。）

## 内心
（一个人的时候在想什么？焦虑来源？真正的驱动力是什么？）

## 决策
（做决定快还是慢？靠直觉还是靠分析？犹豫的原因是什么？）

## 事业
（适合什么赛道、什么角色？不适合什么？）

## 财富观
（对钱的态度。能存住还是散财？该用什么方式赚钱？）

## 家境
（如有[家境背景]数据，整合成 1-2 句大白话。家庭经济状况、父母特质、童年环境。别罗列字段。）

最后给 1-2 条**立刻能做的事**——不是道理，是动作。每条不超过两句话。必须匹配[当前人生阶段]。"""


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


def build_fusion_data_package(pr_dict: dict, family_dict: dict | None = None,
                              life_stage: str = "", age_info: dict | None = None) -> dict:
    """从 PersonalityResult + FamilyResult 构建 LLM 融合数据包。"""
    package: dict = {}

    # ── 命主基本信息 ──
    if life_stage:
        package["当前人生阶段"] = life_stage
    if age_info:
        package["日主信息"] = age_info

    # ── 古今差异说明（注入数据包，让 LLM 知道要做现代翻译）──
    package["古今差异提示"] = (
        "【重要】以下引擎数据基于古代命理规则生成，部分描述带有古代社会语境。"
        "请做现代翻译：'印星=爱读书'在现代指'吸收信息能力强、需要理论支撑后才行动、擅长考证/学历路径'，"
        "不一定是传统意义上的爱学习。'官杀=适合公务员'在现代指'在结构化组织（大公司/体制/专业机构）中发挥更好'。"
        "'财星=善于经营'在现代包含数字资产/知识付费/技术变现等多元路径。"
        "'食伤'在现代=内容创作/技术创新/表达输出能力。请过滤掉古籍引用和古代社会特有的职业建议。"
    )

    # ── 全局最高指令（病药组合）──
    bingyao = pr_dict.get("bingyao_combos", [])
    if bingyao:
        top = bingyao[0]
        package["全局最高指令"] = f"{top['combo']}：{top['directive']}"
        if len(bingyao) > 1:
            package["次要病药"] = [
                f"{c['combo']}：{c['directive'][:150]}..." for c in bingyao[1:]
            ]

    # ── 核心性格标签（清洗古籍引用）──
    traits = []
    dm_core = pr_dict.get("day_master_core", "")
    if dm_core:
        first_line = _clean_ancient_refs(dm_core.split("\n")[0] if "\n" in dm_core else dm_core[:120])
        if first_line:
            traits.append(first_line)

    dominant = pr_dict.get("dominant_ten_god", "")
    if dominant:
        traits.append(_clean_ancient_refs(dominant))

    pattern_info = pr_dict.get("pattern_influence", "")
    if pattern_info:
        traits.append(_clean_ancient_refs(pattern_info))

    strength_label = pr_dict.get("strength_label", "")
    if strength_label:
        traits.append(_clean_ancient_refs(strength_label))

    area_traits = pr_dict.get("traits", {})
    for area, desc in area_traits.items():
        if desc:
            cleaned = _clean_ancient_refs(desc[:200])
            if cleaned:
                traits.append(f"[{area}] {cleaned}")

    special_combos = pr_dict.get("special_combos", [])
    for combo in special_combos[:5]:  # 最多5条，避免过多噪音
        cleaned = _clean_ancient_refs(combo[:200])
        if cleaned:
            traits.append(cleaned)

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

    # ── 六维度引擎数据（清洗后传给 LLM）──
    package["六维度引擎数据"] = {
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
