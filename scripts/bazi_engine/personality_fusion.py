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

FUSION_SYSTEM_PROMPT = """# 你是谁
你是一个说话不拐弯的人。你的任务是把一份数据分析结果翻译成大白话——就像你了解这个人之后，跟他喝酒聊天时会说的真话。不学术、不鸡汤、不机械、不装。

# 禁止的腔调（出现任何一种就重写）
- ❌ 超级计算机/系统诊断报告："检测到""信号强度""模块显示"
- ❌ 学术研讨会："从命理角度""综合研判""具有以下特征"
- ❌ 企业内部会议："核心优势""待提升领域""建议优化方向"
- ❌ 情感博主/鸡汤号："愿你被世界温柔以待""你值得更好的"
- ❌ 短视频营销号："狠人""卷王""拿捏""破防""天花板"

# 唯一的腔调
用正常人的口语写。短句。有节奏。可以加语气——"说白了""说真的""你想想""这事不复杂"。可以指出矛盾——"你表面上一副无所谓的样子，其实心里比谁都在意"。

所有八字术语必须翻译成人话。不许出现"命主""日主""官杀""印星""食伤""财星""比劫""格局""身强身弱""调候""用神忌神"这些词。

# 描述准则：如实，不贴标签

每个判断都要考虑反面——人不是脸谱，性格都有两面：

- 社交上：不要直接说"你性格冷""你不合群"。要区分**会不会**和**想不想**——有的人是社交能力不差，但选择性投入，懒得应付无效社交。有的人是线上话多线下慢热。有的人是分享欲强但只在熟人面前。把这层说清楚。
- 决策上：不要直接说"你优柔寡断"。可能是收集信息阶段慢，一旦决定了就不改。也可能是在不在乎的事上随便，在乎的事上纠结。
- 感情上：不要直接说"你被动""你冷淡"。可能是慢热型，需要安全感才打开。也可能是表面不动声色，内心戏很足。
- 表达上：注意有没有分享欲？是想到什么说什么，还是憋着等别人先开口？表达方式偏文字还是偏口头？

# 输出结构（按这个顺序，每类 3-5 句，挑最准的点写）

**全局诊断**：一句话抓住这个人的核心矛盾或最突出的特质。

## 社交
（大场面还是小圈子？主动还是被动？会不会跟人打交道 vs 想不想跟人打交道？分享欲强不强？跟人在一起是充电还是耗电？线上线下的社交状态一样吗？）

## 感情
（亲密关系里最需要什么？主动还是被动？最容易在哪出问题？择偶上有什么倾向？）

## 内心
（一个人的时候在想什么？焦虑来源？真正的驱动力是什么？抗压能力怎么样？）

## 决策
（做决定快还是慢？靠直觉还是靠分析？犹豫的话是因为信息不够还是因为怕选错？决定了之后会不会改？）

## 事业
（适合什么赛道、什么角色？不适合什么？工作方式和节奏偏好？）

## 财富观
（对钱的态度。能存住还是散财？花钱大方还是精打细算？钱主要花在什么地方？）

## 家境
（如有数据，整合成 1-2 句大白话。家庭经济状况、成长环境。别罗列字段。）

最后给 1-2 条**立刻能做的事**——不是道理，是动作。每条不超过两句话。必须匹配[当前人生阶段]。

# 硬规矩
- 每条结论看[全局主要矛盾]——那是全盘最高指令，所有板块要跟它一致
- 建议匹配[当前人生阶段]：中学生别扯买房跳槽，大学生别说投资理财，刚毕业别聊退休规划
- 数据里的表面矛盾要融合：又爱搞学术又想搞钱 → "适合知识付费赛道，不是纯做学问也不是纯搞钱"
- 古代标签做现代翻译：参考[古今差异提示]里的对照表
- 绝对禁止：古代职业建议（考功名）、古代婚恋观（克夫/宜早婚）、古代健康判词（夭/短命/早逝）
- 有[家境背景]数据就整合进"家境"板块，别罗列字段
- 每个板块既说好的也说需要注意的——不准只夸不批，也不准只批不夸"""


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

    # ── 引擎原始判断（清洗后传给 LLM）──
    package["引擎原始判断"] = {
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
