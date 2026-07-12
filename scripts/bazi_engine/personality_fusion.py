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

from ._deepseek_config import (
    DEEPSEEK_API_URL,
    DEEPSEEK_KEY,
    DEEPSEEK_MODEL,
)
from ._http import shared_client

# ═══════════════════════════════════════════════════════════════
# 系统提示词
# ═══════════════════════════════════════════════════════════════

FUSION_SYSTEM_PROMPT = """把一份结构化命理数据写成一份给人看的性格分析。不学术、不鸡汤、不装。

# 禁止
- 八字术语（比劫、官杀、印星、食伤、财星、格局、身强身弱、调候、用神忌神等）
- 开场白和收尾语。直接从全局诊断开始写，写完立刻能做的事就结束
- "你是一个...的人""骨子里就是..."这类句式——直接说事，别总结
- 给概念加引号（"耗电""卡住""压力处理器"）
- 每句话都追求金句效果——正常说话不需要句句精彩

# 怎么写
陈述事实，不表演。短句为主。可以指出矛盾，但不刻意制造戏剧性。
**双面原则：没有绝对的好或坏。每个特质都要同时指出正面和反面——比如"果断"的优势是行动快，代价是可能冲动；"内敛"的优势是思考深，代价是社交耗能。不给任何特质贴上纯粹正面或纯粹负面的标签。**
**跨维度联动：写完一个维度后，如果它跟其他维度有明显互动关系，点一笔。** 比如"社交偏内敛+决策果断"可能意味着团队中你容易独断——别人来不及了解你的想法，你已经拍板了。

# 输出结构

全局诊断（核心矛盾 + 一句解释为什么是关键。比如"责任感极强但表达欲偏低——对承诺极度认真，但不喜欢张扬地证明这一点，容易被低估"）

## 社交
## 感情
## 内心
## 决策
## 事业
## 财富观
## 家境（如有数据）
## 立刻能做的事

每节以覆盖所有关键信号为优先，不设句数上限。
**覆盖度要求：每个维度必须覆盖所有数值明显偏离中位的信号（≥7或≤3），不能只盯着最高分那一个写。** 比如社交维度同时收到"表达欲7"和"内敛度8"，两件事都要提到，并解释它们如何共存。

**立刻能做的事要求：1-2条具体动作，必须基于三条信息交汇：[当前人生阶段] + [全局最突出矛盾] + [该维度最弱/最强的信号]。不能泛泛说"多社交""早规划"——要说具体场景下的具体行动。** 比如"你的分析度极高但直觉度偏低。下次小组讨论时，在完全想清楚之前先开口说'我还需要再想想，但目前倾向是X'——把中间结论暴露出来，而不是等完美答案。"

# 数据使用
- [全局主要矛盾]是全盘最高指令，所有板块要跟它一致
- [当前人生阶段]决定建议范围：中学生说学业，大学生说专业/实习，职场人说职业
- [六维度信号] 是结构化数值，不是描述文字。你需要自己解读这些数字之间的关系和矛盾，写出具体的性格表现。数值含义：0=极弱 3=偏弱 5=中等 7=偏强 10=极强。注意矛盾组合（如表达欲高+内敛度高=需要安全感才释放的表达者）
- [粒度性格特质] 是引擎从十神藏干和地支关系提取的具体行为倾向。每条特质有"所属维度"标签，你必须把该维度标注的特质融入对应章节，**但不限于此——标注特质是起点，不是边界。你还需要根据十神组合、地支驱动、六维度数值信号等数据，推导出标注列表中没有覆盖到的性格表现**。四柱藏干特质是底层性格驱动力（来自地支藏干），十神加权特质是外在行为倾向。**和六维度信号的关系：六维度信号给数值框架（强度高低），粒度特质给具体描述（怎么表现）。两者不是二选一——每个章节必须同时使用数值信号和粒度特质，缺一不可。** 粒度特质数量不同是正常的（如感情只有几条，内心有很多），数量少不等于该维度不重要——用六维度信号补充数值强度
- 表面矛盾要融合（如又爱学术又想搞钱→"知识付费赛道比纯学术更适合你"）
- 古代概念做现代翻译：参考[古今差异提示]
- 禁止古代职业建议、古代婚恋观、古代健康判词
- **禁止在报告中输出任何原始分数**：如"表达欲9.0"、"拘谨度8.7"等。分数是你用来判断高低的依据，不是输出内容。用"偏高""偏强""偏低""偏弱"代替，或者直接用"擅长""不太擅长"这类自然语言。

# 多信号叠合（重要）
**不允许只看一个信号写结论。每个维度的描述必须同时覆盖该维度内所有偏离中位的信号（≥7或≤3），及与其他维度的互动关系。**
具体方法：
1. **维度内叠合**：同一维度的多个信号一起看。如社交维度同时有"表达欲7"和"内敛度8"→写出两种倾向如何共存，什么场景下哪一种占主导。
2. **跨维度叠合**：不同维度之间相互影响。如"社交表达欲低"+"决策果断"→团队中可能独断不想解释；"内心情绪敏感"+"感情表达欲低"→心里有事但不说的类型。
3. **十神驱动解读**：每个维度的高/低信号不是孤立的，背后有十神组合在驱动。比如"决策维度的冒险倾向高"可能源于偏财+七杀组合，说明冒险不是冲动而是有计算过的。在分析中把这种驱动关系点出来。
4. **粒度特质印证**：粒度特质出现的场景就是该信号在现实生活中的表现方式。如果六维度信号显示"内敛度8"+粒度特质有"不善表达情感"，那这两个肯定是一个意思——在描述中要合并说，不要当两件事分开说。
5. **当代场景落地**：每个维度写完，要让读者能在脑海中对应到一个具体的日常场景——不是"你很内向"，而是"在聚会上你会找角落站着，但如果有一个人主动来找你聊专业话题，你会说很久"。
- **如果一个维度的全部信号都处于中位（4-6），不需要硬写，一句话带过即可。**"""

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
        "不喜冲突": ["社交"], "讲义气": ["社交", "感情"], "护短": ["社交", "感情"],
        "独处需求": ["社交", "内心"], "依赖性强": ["社交", "内心", "感情"],
        "不善表达情感": ["社交", "内心", "感情"], "好面子": ["社交", "内心"],
        "乐观豁达": ["社交", "内心"], "懒得争执": ["社交", "内心"],
        # 内心维度
        "深度思考": ["内心"], "钻牛角尖": ["内心"], "冷门兴趣": ["内心"],
        "直觉洞察": ["内心"], "情绪敏感": ["内心", "感情"],
        "多疑敏感": ["内心", "社交", "感情"], "完美主义": ["内心", "决策"],
        "审美挑剔": ["内心"], "自我意识强": ["内心", "决策"],
        "固执己见": ["内心", "决策"], "保守求稳": ["内心", "决策", "感情"],
        "心理压力": ["内心"], "心宽体胖": ["内心"],
        "爱读书思考": ["内心"], "仁慈包容": ["内心", "社交"],
        "贵人运": ["内心", "事业"], "重名誉": ["内心", "事业"],
        "博而不精": ["内心"], "安于现状": ["内心", "财富观"],
        "争强好胜": ["内心", "决策"],
        # 决策维度
        "果断勇猛": ["决策"], "急躁冲动": ["决策"],
        "冲动行事": ["决策", "感情"], "冒险精神": ["决策", "财富观"],
        "灵活变通": ["决策"], "危机嗅觉": ["决策"],
        "竞争意识": ["决策", "事业"], "反叛性": ["决策", "事业"],
        "不服权威": ["决策", "事业"], "报复心": ["决策", "社交"],
        "独立自主": ["决策", "事业"],
        # 事业维度
        "商业头脑": ["事业", "财富观"], "稳定追求": ["事业", "财富观"],
        "责任感": ["事业"], "处事周全": ["事业"], "守规矩": ["事业"],
        # 感情维度
        "情感丰富": ["感情"], "家庭观念": ["感情", "财富观"],
        "慷慨大方": ["财富观", "感情"],
        # 财富观维度
        "务实节俭": ["财富观"],
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
        # 排名旁标注"偏高""偏低"替代原始分数
        for item in package["十神强度排行"]:
            s = item["强度"]
            item["相对强度"] = "偏高" if s >= 5 else ("正常" if s >= 2 else "偏低")
            if s >= 3:
                item.pop("强度", None)  # 只传定性不传定量
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
                if isinstance(v, (int, float)) and (v >= 7 or v <= 3):
                    _hints.append(f"{k}={v}" + ("(偏高)" if v >= 7 else "(偏低)"))
            for k, v in raw.items():
                if (isinstance(v, list) and v) or (isinstance(v, str) and v and v not in ("平稳", "中和", "强", "弱")):
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

        text = "".join(full_text_parts)
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
            return content or None

    except Exception:
        return None
