"""LLM 推理层 (v0.9.0) — Hybrid 模式：规则引擎主跑 + LLM 边界年份二次判断

设计原则:
- 规则引擎不变，继续产生 1-3★ 信号
- LLM 只介入"规则引擎判定为弱信号或无信号"的年份
- LLM 接收结构化特征（不是原始八字），做多弱信号综合推理
- LLM 输出置信度低于规则引擎（标记 source="llm"）

集成: DeepSeek API (同步调用，非流式)
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

# ── API 配置（复用 chat.py 的环境变量）──
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# ── LLM Review 开关 ──
LLM_REVIEW_ENABLED = os.getenv("BAZI_LLM_REVIEW", "0") == "1"


@dataclass
class LLMReviewResult:
    """LLM 推理结果"""
    year: int
    category: str         # "婚嫁"|"事业"|"财运"|"健康"|"搬迁"|"人际"|"状态"
    direction: str         # "正面"|"负面"|"中性"
    strength: int          # 1-2 (LLM 结果置信度上限为 2★)
    prediction: str
    reasoning: str         # LLM 的推理过程
    triggers: list[str] = field(default_factory=list)
    confidence: float = 0.6  # LLM 置信度 (0-1)
    source: str = "llm"


# ═══════════════════════════════════════════════════════════════
# 边界判定：哪些年份需要 LLM 介入
# ═══════════════════════════════════════════════════════════════

# LLM 介入的目标类别（与校准数据对齐）
_REVIEW_CATEGORIES = {"婚嫁", "事业", "财运", "健康", "搬迁", "桃花"}


def should_invoke_llm(events: list, year: int, age: int,
                       target_categories: set[str] | None = None) -> bool:
    """判断某一年是否需要 LLM 二次判断。

    条件：
    1. 目标类别中没有任何 ≥2★ 的信号
    2. 年龄在合理范围内
    3. 或检测到多个 1★ 弱信号需要叠加判断

    如果 target_categories 为 None，默认检查所有关键类别。
    """
    if not LLM_REVIEW_ENABLED:
        return False
    if not DEEPSEEK_KEY:
        return False
    if age < 15 or age > 70:
        return False

    if target_categories is None:
        target_categories = {"婚嫁", "桃花", "事业", "财运", "健康"}

    # 检查目标类别中哪些有 ≥2★
    strong_in_target = set()
    weak_in_target = set()
    for e in events:
        if e.category in target_categories:
            if e.strength >= 2:
                strong_in_target.add(e.category)
            elif e.strength == 1:
                weak_in_target.add(e.category)

    # 如果目标类别全部都有 ≥2★ 信号，不需要 LLM
    if strong_in_target >= target_categories:
        return False

    # 至少有一个目标类别完全无信号，或只有弱信号 → 触发 LLM
    missing_or_weak = target_categories - strong_in_target
    return len(missing_or_weak) > 0


# ═══════════════════════════════════════════════════════════════
# 结构化上下文提取
# ═══════════════════════════════════════════════════════════════

def build_review_context(
    chart_data: dict,
    year: int,
    age: int,
    liunian_stem: str,
    liunian_branch: str,
    dayun_stem: str | None,
    dayun_branch: str | None,
    rule_events: list,
    dayun_mod: dict | None = None,
    tansheng_wangke: list[dict] | None = None,
    year_features: dict | None = None,
    personality_text: str = "",
) -> dict:
    """从一个特定年份提取结构化 LLM 审查上下文。

    year_features: 流年级特征（十神/神煞/冲合关系等），由 scan_years 传入。
                   这些是信号检测函数内部计算但未触发规则的"近失"特征。
    """
    ctx: dict[str, Any] = {}

    # ── 1. 原局概要 ──
    dm = chart_data.get("day_master", {})
    yongshen = chart_data.get("yongshen", {})
    tiaohou = chart_data.get("tiaohou", {})
    pattern = chart_data.get("pattern", "")

    pillars = chart_data.get("pillars", {})
    pillar_strs = []
    for key in ["year", "month", "day", "hour"]:
        p = pillars.get(key, {})
        if p:
            pillar_strs.append(f"{p.get('stem','')}{p.get('branch','')}")
    natal_str = " ".join(pillar_strs)
    day_branch = pillars.get("day", {}).get("branch", "")

    ctx["natal"] = {
        "pillars": natal_str,
        "day_master": f"{dm.get('stem','')}({dm.get('wuxing','')}·{dm.get('yinyang','')})",
        "pattern": pattern,
        "strength": yongshen.get("strength", "中和"),
        "favorable": yongshen.get("favorable", []),
        "harmful": yongshen.get("harmful", []),
        "favorable_wuxing": yongshen.get("favorable_wuxing", []),
        "harmful_wuxing": yongshen.get("harmful_wuxing", []),
        "day_branch": day_branch,
        "tiaohou": {
            "climate": tiaohou.get("climate", "中和"),
            "is_fei_ju": tiaohou.get("is_fei_ju", False),
            "tiaohou_wuxing": tiaohou.get("tiaohou_wuxing", []),
        },
    }

    # ── 2. 原局关键关系 ──
    interactions = chart_data.get("interactions", {})
    natal_interactions = []
    for inter_type in ["天干五合", "地支六合", "三合", "六冲", "相刑", "相害"]:
        for it in interactions.get(inter_type, []):
            natal_interactions.append(f"{inter_type}: {it}")
    ctx["natal"]["key_interactions"] = natal_interactions[:10]

    # 贪生忘克
    if tansheng_wangke:
        ctx["natal"]["tansheng_wangke"] = [
            {"path": gg["path"], "note": gg["note"]} for gg in tansheng_wangke
        ]

    # ── 3. 当前大运 ──
    ctx["dayun"] = {
        "stem": dayun_stem,
        "branch": dayun_branch,
    }
    if dayun_mod:
        ctx["dayun"].update({
            "stem_is_favorable": dayun_mod.get("stem_is_favorable"),
            "branch_is_favorable": dayun_mod.get("branch_is_favorable"),
            "baseline_offset": dayun_mod.get("baseline_offset", 0),
            "theme": dayun_mod.get("theme", ""),
            "stem_interactions": dayun_mod.get("stem_interactions", []),
            "branch_interactions": dayun_mod.get("branch_interactions", []),
        })

    # ── 4. 当前流年 ──
    ctx["liunian"] = {
        "year": year,
        "age": age,
        "stem": liunian_stem,
        "branch": liunian_branch,
    }

    # ── 4b. 流年近失特征（v0.9.1: LLM需要这些才能判断婚嫁/桃花）──
    if year_features:
        ctx["year_features"] = year_features

    # ── 5. 性格画像（v0.11.1: LLM需要知道命主是什么样的人）──
    if personality_text:
        ctx["personality"] = personality_text

    # ── 6. 已知事件 ──
    known = chart_data.get("known_events", {})
    if known:
        ctx["known_events"] = known

    # ── 7. 规则引擎信号（包括弱信号）──
    ctx["rule_signals"] = [
        {
            "category": e.category,
            "direction": e.direction,
            "strength": e.strength,
            "triggers": e.triggers[:5],
        }
        for e in rule_events
    ]

    return ctx


# ═══════════════════════════════════════════════════════════════
# Prompt 构建
# ═══════════════════════════════════════════════════════════════

def build_review_prompt(ctx: dict) -> str:
    """从结构化上下文构建 LLM 审查 prompt。

    关键设计：
    - LLM 角色是"多因子综合推理器"，不是"算命先生"
    - 输入全是已经计算好的结构化特征
    - 输出是 JSON，方便解析
    - 要求 LLM 给出推理链（reasoning）+ 结论
    """
    natal = ctx["natal"]
    dayun = ctx.get("dayun", {})
    liunian = ctx["liunian"]
    rule_signals = ctx.get("rule_signals", [])

    # ── 把结构化数据序列化成紧凑文本 ──
    prompt_parts = []

    # 原局
    prompt_parts.append(f"八字: {natal['pillars']}")
    prompt_parts.append(f"日主: {natal['day_master']} | 格局: {natal['pattern']} | 强弱: {natal['strength']}")
    prompt_parts.append(f"喜用五行: {natal['favorable_wuxing']} | 忌神五行: {natal['harmful_wuxing']}")
    prompt_parts.append(f"喜用十神: {natal['favorable']} | 忌十神: {natal['harmful']}")
    if natal.get("key_interactions"):
        prompt_parts.append(f"原局关键关系: {'; '.join(natal['key_interactions'][:8])}")

    # 调候
    th = natal.get("tiaohou", {})
    prompt_parts.append(f"调候: 气候{th.get('climate','中和')} | {'废局' if th.get('is_fei_ju') else '非废局'} | 需{th.get('tiaohou_wuxing',[])}")

    # 贪生忘克
    if natal.get("tansheng_wangke"):
        for ts in natal["tansheng_wangke"]:
            prompt_parts.append(f"[贪生忘克] {'→'.join(ts['path'])} → {ts.get('note','')[:120]}")

    # 性格画像（v0.11.1: 命主是什么样的人——影响所有事件的解读）
    personality_text = ctx.get("personality", "")
    if personality_text:
        prompt_parts.append(f"命主性格: {personality_text}")

    # 大运
    dy_theme = dayun.get("theme", "")
    dy_offset = dayun.get("baseline_offset", 0)
    dy_offset_text = "吉" if dy_offset > 0 else ("凶" if dy_offset < 0 else "平")
    prompt_parts.append(f"大运: {dayun.get('stem','')}{dayun.get('branch','')} | 主题'{dy_theme}' | 十年基调偏{dy_offset_text}")
    if dayun.get("stem_interactions"):
        prompt_parts.append(f"大运与原局: {'; '.join(dayun['stem_interactions'] + dayun.get('branch_interactions',[]))}")

    # 流年
    prompt_parts.append(f"流年: {liunian['year']}年 {liunian['stem']}{liunian['branch']} | 命主{liunian['age']}岁")

    # 流年近失特征（规则引擎内算但未触发——LLM的推理原料）
    yr_feat = ctx.get("year_features", {})
    if yr_feat:
        feat_lines = [f"  {k}: {v}" for k, v in yr_feat.items()]
        prompt_parts.append(f"流年特征:\n" + "\n".join(feat_lines))

    # 规则引擎结果
    if rule_signals:
        sig_lines = []
        for s in rule_signals:
            sig_lines.append(
                f"  {s['category']}/{s['direction']}/{s['strength']}★"
            )
        prompt_parts.append(f"规则引擎信号:\n" + "\n".join(sig_lines))
    else:
        prompt_parts.append("规则引擎信号: 无")

    context_text = "\n".join(prompt_parts)

    prompt = f"""你是八字命理多因子综合推理器。以下是某命主在特定流年的结构化特征数据。

{context_text}

## 岁运交战知识（关键参考）

岁运交战=大运与流年天克地冲(天干相克+地支相冲同时出现)，是流年层面最剧烈的冲突形态。

- 岁=流年(太岁为君)，运=大运(为臣)。臣冲克君→主动荡是非破财变动
- 运伐岁(大运天干克流年天干)：下犯上，凶性重
- 岁伐运(流年天干克大运天干)：上制下，凶性稍减
- 天战(天干冲)：表层影响，事业/人际/口舌
- 地战(地支冲)：底层动摇，环境/健康/家庭，比天战严重1.5-2倍
- 冲克喜用神→破财伤病官非分手离职
- 冲克忌神→转机换运去旧迎新
- 原局有合/生/制→减凶；无救→波动加剧
- 古诀：反吟伏吟泪淋淋，不伤自己损他人
- 现实中：稳守、少投资、不冒险、低调行事

## 任务

规则引擎已经跑过但可能遗漏"多弱信号叠加"型的事件。根据流年特征做综合推理：

1. 婚嫁检测: 流年十神=配偶星 + 夫妻宫引动 + 红鸾/天喜 + 大运与夫妻宫互动 → 叠加即可能
2. 桃花检测: 桃花入命 + 红鸾 + 配偶星透干 + 流年合日主
3. 事业检测: 官/印星 + 驿马 + 大运官印相生 → 晋升/跳槽
4. 财运检测: 财星 + 食伤生财 + 驿马+财
5. 吉处藏凶: 用神流年被合/冲/空 → 好事打折
6. 凶中有救: 忌神流年被制/化 → 坏事有转机
7. 岁运交战: 若有岁运天克地冲→所有信号需结合喜忌重判，正负面可能反转

## 输出JSON

{{
  "events": [
    {{
      "category": "婚嫁/事业/财运/健康/搬迁/桃花",
      "direction": "正面/负面/中性",
      "strength": 1或2,
      "prediction": "一句话(≤30字)",
      "reasoning": "推理(≤80字): 哪几个特征叠加→为何成立",
      "confidence": 0.5-1.0
    }}
  ]
}}

约束: strength≤2★, 无事件返回{{"events":[]}}, 严格根据数据推理不编造"""

    return prompt


# ═══════════════════════════════════════════════════════════════
# LLM 调用
# ═══════════════════════════════════════════════════════════════

def call_llm_review(ctx: dict, on_token=None) -> list[LLMReviewResult]:
    """调用 DeepSeek API（流式），解析响应。

    v0.11.1: 改用流式 API（stream=True），边收token边攒，首token延迟更低。
    v0.11.2: 支持 on_token 回调，供前端逐字渲染推理过程。

    Returns:
        LLMReviewResult 列表。API 失败或 LLM 无发现时返回空列表。
    """
    if not DEEPSEEK_KEY:
        return []

    prompt = build_review_prompt(ctx)

    messages = [
        {"role": "system", "content": "你是一个精确的八字命理推理器。只输出 JSON，不输出其他内容。"},
        {"role": "user", "content": prompt},
    ]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    try:
        _timeout = 90.0 if "v4" in DEEPSEEK_MODEL.lower() or "reasoner" in DEEPSEEK_MODEL.lower() else 30.0
        full_text_parts: list[str] = []
        with httpx.Client(timeout=_timeout) as client:
            with client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    return []

                for line in resp.iter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
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
                                if on_token:
                                    on_token(content)
                    except json.JSONDecodeError:
                        continue

        content = "".join(full_text_parts)
        if not content:
            return []

        return _parse_review_response(content, ctx["liunian"]["year"])

    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return []


# ═══════════════════════════════════════════════════════════════
# 响应解析
# ═══════════════════════════════════════════════════════════════

def _parse_review_response(content: str, year: int) -> list[LLMReviewResult]:
    """解析 LLM 的 JSON 响应"""
    results: list[LLMReviewResult] = []

    # 提取 JSON 块
    json_match = re.search(r'\{[\s\S]*"events"[\s\S]*\}', content)
    if not json_match:
        # 尝试找到任何 JSON 对象
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            return []

    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return []

    events = data.get("events", [])
    if not isinstance(events, list):
        return []

    valid_categories = {"婚嫁", "事业", "财运", "健康", "搬迁", "桃花", "人际", "状态"}
    valid_directions = {"正面", "负面", "中性"}

    for evt in events:
        cat = evt.get("category", "")
        if cat not in valid_categories:
            continue

        direction = evt.get("direction", "中性")
        if direction not in valid_directions:
            direction = "中性"

        strength = evt.get("strength", 1)
        if not isinstance(strength, (int, float)):
            strength = 1
        strength = max(1, min(2, int(strength)))  # 限制 1-2★

        confidence = evt.get("confidence", 0.6)
        if not isinstance(confidence, (int, float)):
            confidence = 0.6
        confidence = max(0.0, min(1.0, float(confidence)))

        if confidence < 0.5:
            continue

        results.append(LLMReviewResult(
            year=year,
            category=cat,
            direction=direction,
            strength=strength,
            prediction=evt.get("prediction", "")[:60],
            reasoning=evt.get("reasoning", "")[:120],
            triggers=[f"[LLM推理] {evt.get('reasoning', '')[:60]}"],
            confidence=confidence,
            source="llm",
        ))

    return results


# ═══════════════════════════════════════════════════════════════
# 便捷入口
# ═══════════════════════════════════════════════════════════════

def review_year_if_needed(
    chart_data: dict,
    year: int,
    age: int,
    liunian_stem: str,
    liunian_branch: str,
    dayun_stem: str | None,
    dayun_branch: str | None,
    rule_events: list,
    dayun_mod: dict | None = None,
    tansheng_wangke: list[dict] | None = None,
    year_features: dict | None = None,
    personality_text: str = "",
) -> list[LLMReviewResult]:
    """便捷入口：判断是否需要 LLM，需要则调用来审查。

    Returns:
        LLMReviewResult 列表（可能为空）。
    """
    # 从目标类别中找出需要审视的
    target = {"婚嫁", "桃花", "事业", "财运", "健康"} - {
        e.category for e in rule_events if e.strength >= 2
    }
    if not should_invoke_llm(rule_events, year, age, target if target else None):
        return []

    ctx = build_review_context(
        chart_data, year, age,
        liunian_stem, liunian_branch,
        dayun_stem, dayun_branch,
        rule_events, dayun_mod, tansheng_wangke,
        year_features=year_features,
        personality_text=personality_text,
    )
    return call_llm_review(ctx)
