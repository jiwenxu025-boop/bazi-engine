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
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
FUSION_ENABLED = os.getenv("BAZI_FUSION_ENGINE", "0") == "1"

# ═══════════════════════════════════════════════════════════════
# 系统提示词
# ═══════════════════════════════════════════════════════════════

FUSION_SYSTEM_PROMPT = """把结构化命理数据写成一份给人看的性格分析。输出格式和风格参照下面的示例。

# 示例输出（给一个理论型+社交内敛的中学生的例子）

对未知事物的好奇心远超对人际关系的兴趣。不是不合群，是思维跑得太快，同龄人的话题跟不上你的频率。这个矛盾会贯穿学生时代——越往后走，越能找到同类。

## 社交

在陌生的多人场合能量消耗很快，但在信任的小圈子里反而能带头。拘谨不是性格缺陷——它让你少说废话，开口时信息密度更高。代价是初次接触容易被低估，优势是一旦建立信任，关系的深度远超泛泛之交。

注：如果[全局主要矛盾]涉及社交，该维度写得稍微展开一点，因为它是全盘联动的主轴。

## 感情

夫妻宫平稳，感情模式不极端。偏内敛+高分析度意味着你倾向于观察对方很久才表态——这会错过一些窗口，但也帮你筛选掉不合适的对象。不是你被动，是你在确认。确认了就会全力以赴，这是优势也是压力——对方可能还没准备好接受这种强度。

## 内心

精神世界自成体系。独处不是孤独，是你的充电方式。需要警惕的不是独处本身，而是长期独处后与现实的脱节——内在逻辑自洽不等于外界会按你的逻辑运转。偶尔找一个能挑战你想法的朋友对话，比看十本书有用。

## 决策

分析度极高，每个决定都需要足够的信息支撑。这不是犹豫——你在意的不是做决定的速度，而是决定的可靠性。一旦信息够了，行动比谁都快。但要注意：有些决策没有完美答案，等到"足够确定"的时机可能已经过去了。跟直觉度偏低联动：试着在只有六成把握时做小决定，练习相信直觉。

## 事业

学术+技术双驱，不适合纯社交型或纯管理型工作。能在需要深度钻研的领域找到最优路径。但需要注意：不管你走什么方向，团队协作是绕不开的。社交内敛≠可以完全避开人——找个能替你对外沟通的合作者，比强迫自己变得外向更现实。

## 财富观

对钱没有执念，但也不排斥。更喜欢把钱当成工具而非目标。这让你不会被消费主义裹挟，代价是对财务规划不够警觉。不需要变成精打细算的人，但至少要知道钱花在哪了。

## 立刻能做的事

1. 你分析度极高但直觉度偏低。下次课堂上老师提问时，在完全想清楚之前先举手——把你的"中间答案"说出来。不是要完美的回答，是训练用直觉做第一次反应。
2. 找一个跟你互补的人——他负责跟外部世界打交道，你负责深度思考。不是要你社交，是要你找到那个"对外接口"。

---

# 你的规则

严格仿照上面的格式和叙事方式。核心要素：
- 每个特质必说两面（好+坏），不说绝对的好或坏
- 每节覆盖所有偏离中位的信号（≥7或≤3的数值各至少一句）
- 写完一节后如果跟其他维度有互动，顺手点一笔
- 禁止八字术语（比劫、官杀、印星、食伤、财星、格局、身强身弱等）
- 不开场白不收尾，直接从全局诊断开始
- 立刻能做的事必须基于 [当前人生阶段]+[全局最突出矛盾]+[最强/最弱信号] 三者的交汇来写，给具体场景

# 数据使用
- [全局主要矛盾]是全盘最高指令，所有板块要跟它一致
- [当前人生阶段]决定建议范围
- [六维度信号] 数值含义：0=极弱 3=偏弱 5=中等 7=偏强 10=极强。信号之间的矛盾组合比单个数值更重要，优先解读矛盾
- 古代概念做现代翻译，参考[古今差异提示]
- 禁止古代职业建议、古代婚恋观"""
<｜｜DSML｜｜parameter name="replace_all" string="false">false


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

    except Exception:
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

    except Exception:
        return None
