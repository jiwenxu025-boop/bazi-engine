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

# ═══════════════════════════════════════════════════════════════
# 按人生阶段的示例（注入到 user prompt，不放在 system prompt 里占 token）
# ═══════════════════════════════════════════════════════════════

LIFESTAGE_EXAMPLES = {
    "中学": """（以下是针对中学生身份的输出示例，注意建议围绕学业、专业方向、家庭关系展开。）

示例输出：
对未知事物的好奇心远超对人际关系的兴趣。不是不合群，是思维跑得太快，同龄人的话题跟不上你的频率。这个矛盾会贯穿高中时代——越往后走，越能找到同类。

## 社交
在陌生的多人场合能量消耗很快，但在信任的小圈子里反而能带头。拘谨不是缺陷——它让你少说废话，开口时信息密度更高。代价是初次接触容易被低估，优势是一旦建立信任，关系的深度远超泛泛之交。

## 感情
夫妻宫平稳。偏内敛+高分析度意味着你倾向于观察对方很久才表态——这会错过一些窗口，但也帮你筛选掉不合适的对象。现阶段以学业为重，但理解你在同龄关系中可能感到比其他人慢半拍——这不是劣势。

## 内心
精神世界自成体系。独处是充电方式。需要警惕的是长期独处后与现实的脱节——内在逻辑自洽不等于外界按你的逻辑运转。偶尔找一个能挑战你想法的朋友对话，比看十本书有用。

## 决策
分析度极高，每个决定都需要足够信息支撑。这不是犹豫——你在意的是决定的可靠性，不是速度。一旦信息够了，行动比谁都快。但有些决策没有完美答案，等到"足够确定"的时机可能已经过了。

## 事业
学术+技术双驱，不适合纯社交型工作。选专业时优先考虑能发挥深度钻研优势的领域。社交内敛≠避开团队——找个能替你对外沟通的合作者，比强迫自己变得外向更现实。

## 财富观
对钱没有执念，但也不排斥。这让你不会被消费主义裹挟，代价是对财务规划不够警觉。现阶段了解基本理财概念即可，不需要过度焦虑。

## 立刻能做的事
1. 你分析度极高但直觉度偏低。下次课堂上老师提问时，在完全想清楚之前先举手——把"中间答案"说出来，训练用直觉做第一次反应。
2. 找一个跟你互补的同学——他负责跟外部世界打交道，你负责深度思考。不是要你社交，是找那个"对外接口"。""",

    "大学": """（以下是针对大学生身份的输出示例，注意建议围绕专业选择、实习方向、社交圈建设展开。）

示例输出：
既有学术深度又对实际回报敏感——不做无用功，但也容易因此跳过值得沉淀但短期内看不到收益的事情。大学生涯本质上是在这两者之间找到平衡点。

## 社交
选择性社交。大场合应付得来但不享受，小圈子深度交流才是你的主场。在大学里这意味着社团活动可能不太吸引你，但课题组、竞赛队这样的小团队反而让你如鱼得水。代价是社交圈偏窄，但圈子的质量和深度远超泛泛之交。

## 感情
夫妻宫合，异性缘不差但容易受外界影响。你倾向于在确定关系前反复衡量——这让你的感情质量偏高，但也让有些机会擦肩而过。大学阶段不用急着给关系下定义，多接触不同类型的人比早点定下来更重要。

## 内心
华盖入命，有独立的精神追求。这让你在学术和深度思考上有天然优势，但警惕把"独处舒服"变成"回避交流"——大学是最后一个能低成本试错社交方式的阶段了。

## 决策
分析后决策型。这意味着你在选课、选导师、选实习方向时不会踩大坑——但可能花太多时间在分析上。大三选实习的时候注意：第一份实习不需要完美匹配，更重要的是排除你不喜欢的方向。

## 事业
混合型方向。大学期间不用急着限定一条路——在主修方向上保持竞争力，同时选修第二方向的课，大三实习时两边的机会都投，让反馈帮你做决定。

## 财富观
对钱有欲望但不极端。大学阶段是建立财务习惯的窗口——不用急着赚钱，但要开始记账。知道钱花在哪了，毕业后才不容易被第一份工资绑架。

## 立刻能做的事
1. 你的分析度极高。这学期选一门"看起来有意思但跟专业无关"的选修课——不是为了学分，是为了测试自己是不是错过了另一个方向。
2. 找一位比你高两届的师兄师姐聊聊他的职业选择。你的社交圈不广，但这种一对一的深度对话正是你的强项。""",

    "职场": """（以下是针对职场人士的输出示例，注意建议围绕职业发展、人际关系、工作生活平衡展开。）

示例输出：
能力不差但存在感偏低——做得多、说得少，在职场里最容易被人低估的类型。不是要你变成社交达人，但需要建立一个让别人知道你做了什么的最小机制。

## 社交
内敛且拘谨。在会议上不太主动发言，但一旦开口，内容质量通常高于平均水平。优势是信息密度高、废话少；代价是存在感不够——老板和同事可能不知道你在做什么。不需要改变性格，但需要有一个可见的输出渠道：周报写清楚、关键节点主动同步、让工作替你说话。

## 感情
责任感极强，在关系中重承诺。这让你在长期关系里非常靠谱，但也让你在感情出问题时扛太多——不一定是你的错，但你倾向于先检讨自己。注意：伴侣不是你展示责任感的另一个场所，关系需要的是分担而非承担。

## 内心
精神世界丰富，有自己的逻辑体系。这让你不容易被职场焦虑裹挟，保持独立思考。但注意财破印的信号——短期利益和长期积累的拉扯在你身上很真实。跳槽加薪的诱惑 vs 在一个领域深耕的复利，没有标准答案，但你需要意识到这个拉扯的存在。

## 决策
分析后决策型，平常想得多，关键时刻敢出手。在职场里这是很稀缺的组合——不会被日常噪音带跑，面对危机时又能果断。唯一需要注意的：有时候你的"关键时刻"阈值得太高了，等到你出手时，机会窗口已经比别人窄了。

## 事业
体制/管理+混合型。这意味着你在需要专业深度的管理岗上发挥最好——不是纯管人，而是"懂业务的管理者"。如果现在做的是纯执行岗，考虑往项目管理的方向靠。

## 财富观
财破印——短期诱惑冲击长期积累。这在职场上是一个需要持续管理的张力。不是不理财，是容易盯短期回报。把一部分资金放在"懒得动"的长期账户里，减少主动操作的冲动。

## 立刻能做的事
1. 从本周开始，每周五下午花15分钟写一份给自己看的周报——这周做了什么、下周计划、遇到什么问题。不是为了交差，是建立"让别人看到你"的最小机制。三个月后回看，你会发现自己做了多少没有被注意到的活。
2. 如果当前岗位的成长曲线开始平了，约一位在做你想做的事的人喝杯咖啡——不了解行情比跳槽本身更危险。""",

    "晚年": """（以下是针对晚年人士的输出示例，注意建议围绕健康、家庭关系、退休生活、传承展开。）

示例输出：
一生积累了丰富的内在资源，晚年的核心不是"做什么"，而是"怎么让已有的东西继续发光"。

## 社交
社交圈收窄但关系更深。这不是问题——到了这个阶段，质量比数量重要得多。保持几个定期联系的老朋友，比维护一大圈点头之交有意义得多。

## 感情
夫妻宫平。这个阶段的感情不是激情而是陪伴。如果有伴侣，注意日常的小互动比大事件更重要；如果单身，坦然接受——独立生活的能力本身就是一种自由。

## 内心
精神世界丰富是你的底牌。到了这个阶段，内在充实的人衰老得更慢。把一部分精力放在整理和输出上——写回忆录、教后辈、做义工，让你的经验继续发挥作用。

## 决策
审慎型。重大决定前给自己设一个期限即可——你不需要别人的催促，但需要防止"再想想"变成无限期的回避。

## 事业
不是追求新高度，是找到可持续的节奏。如果你愿意，顾问、指导、公益都是让经验和能力继续发挥价值的方向。不追求职位，追求影响。

## 财富观
稳健为主。这个阶段的需求不是增值是保值和合理使用。提前做好安排，让自己安心、家人清楚——不是不吉利，是负责任。

## 立刻能做的事
1. 如果还有一件事你一直想做但觉得"过了年纪"，找三个做过的人聊一聊——你会发现年龄限制更多是心理限制。
2. 每年做一次全面体检，健康信号在这个阶段值得格外重视。不是怕生病，是早发现早处理。""",
}


# ═══════════════════════════════════════════════════════════════
# 系统提示词
# ═══════════════════════════════════════════════════════════════

FUSION_SYSTEM_PROMPT = """把结构化命理数据写成一份给人看的性格分析。严格参照 user prompt 中提供的[格式示例]来写——包括叙事风格、结构、每节的写法。注意示例中适配的目标人群（中学/大学/职场/晚年）可能跟当前用户不同，你需要基于当前用户的[当前人生阶段]调整建议的具体场景。

# 核心要求
- 每个特质必说两面（好+坏），不说绝对的好或坏
- 每节覆盖所有偏离中位的信号（≥7或≤3的数值各至少一句）
- 写完一节后如果跟其他维度有互动，顺手点一笔
- 禁止八字术语（比劫、官杀、印星、食伤、财星、格局、身强身弱等）
- 不开场白不收尾，直接从全局诊断开始
- 立刻能做的事基于 [当前人生阶段]+[全局最突出矛盾]+[最强/最弱信号] 三者的交汇来写，给具体场景
- 禁止古代职业建议、古代婚恋观

# 数据使用
- [全局主要矛盾]是全盘最高指令，所有板块要跟它一致
- [当前人生阶段]决定建议范围
- [六维度信号] 数值含义：0=极弱 3=偏弱 5=中等 7=偏强 10=极强。信号之间的矛盾组合比单个数值更重要，优先解读矛盾
- 古代概念做现代翻译，参考[古今差异提示]"""
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
    """构建发给 LLM 的 User Prompt，包含适配当前人生阶段的格式示例。"""
    life_stage = data_package.get("当前人生阶段", "职场")
    example = LIFESTAGE_EXAMPLES.get(life_stage, LIFESTAGE_EXAMPLES["职场"])

    return f"""请根据以下 Python 引擎提取的全盘底层数据，生成一份综合融合报告。

[格式示例]——请参照这个格式和叙事风格来写，但内容必须基于当前用户的实际数据：
{example}

[当前用户数据]：
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
