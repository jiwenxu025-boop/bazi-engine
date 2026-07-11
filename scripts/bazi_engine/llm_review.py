"""LLM 推理层 (v0.9.0) — Hybrid 模式：规则引擎主跑 + LLM 边界年份二次判断

设计原则:
- 规则引擎不变，继续产生 1-3★ 信号
- LLM 只介入"规则引擎判定为弱信号或无信号"的年份
- LLM 接收结构化特征（不是原始八字），做多弱信号综合推理
- LLM 输出置信度低于规则引擎（标记 source="llm"）

集成: DeepSeek API (同步调用，非流式)
"""

from ._http import shared_client
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

from ._deepseek_config import (
    DEEPSEEK_API_URL, DEEPSEEK_KEY, DEEPSEEK_MODEL,
    LLM_REVIEW_ENABLED, get_timeout, is_available,
)


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
    false_generations: list[dict] | None = None,
    year_features: dict | None = None,
    personality_text: str = "",
) -> dict:
    """从一个特定年份提取结构化 LLM 审查上下文。

    year_features: 流年级特征（十神/神煞/冲合关系等），由 scan_years 传入。
                   这些是信号检测函数内部计算但未触发规则的"近失"特征。
    """
    from ._chart_context import extract_base_context
    base = extract_base_context(chart_data)

    ctx: dict[str, Any] = {}

    # ── 1. 原局概要 ──
    ctx["natal"] = {
        "pillars": base["pillars_str"],
        "day_master": base["day_master"],
        "pattern": base["pattern"],
        "strength": base["strength"],
        "favorable": base["favorable"],
        "harmful": base["harmful"],
        "favorable_wuxing": base["favorable_wuxing"],
        "harmful_wuxing": base["harmful_wuxing"],
        "day_branch": base["day_branch"],
        "tiaohou": base.get("tiaohou", {}),
        "key_interactions": base["key_interactions"][:10],
    }

    # 贪生忘克
    if tansheng_wangke:
        ctx["natal"]["tansheng_wangke"] = [
            {"path": gg["path"], "note": gg["note"]} for gg in tansheng_wangke
        ]

    # 假生陷阱（v0.13.0）
    if false_generations:
        ctx["natal"]["false_generations"] = [
            {"subject": fg["subject"], "condition": fg["condition"],
             "effect": fg["effect"], "severity": fg["severity"]}
            for fg in false_generations
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

_SUIYUN_KNOWLEDGE = """
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
"""


def _suiyun_knowledge(ctx: dict) -> str:
    """仅当流年特征中检测到岁运交战才附加知识库。"""
    yr_feat = ctx.get("year_features", {})
    if not yr_feat:
        return ""
    # 检查流年特征中是否有岁运交战相关信号
    suiyun_str = str(yr_feat)
    if "天战" in suiyun_str or "地战" in suiyun_str or "岁运相冲" in suiyun_str or "岁运交战" in suiyun_str:
        return _SUIYUN_KNOWLEDGE
    return ""


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

    # 假生陷阱（v0.13.0）
    if natal.get("false_generations"):
        for fg in natal["false_generations"]:
            prompt_parts.append(f"[假生陷阱] {fg['subject']}: {fg['condition']} → {fg['effect']}")

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
        prompt_parts.append("流年特征:\n" + "\n".join(feat_lines))

    # 规则引擎结果
    if rule_signals:
        sig_lines = []
        for s in rule_signals:
            sig_lines.append(
                f"  {s['category']}/{s['direction']}/{s['strength']}★"
            )
        prompt_parts.append("规则引擎信号:\n" + "\n".join(sig_lines))
    else:
        prompt_parts.append("规则引擎信号: 无")

    context_text = "\n".join(prompt_parts)

    prompt = f"""你是八字命理多因子综合推理器。以下是某命主在特定流年的结构化特征数据。

{context_text}{_suiyun_knowledge(ctx)}

## 任务

规则引擎已经跑过但可能遗漏"多弱信号叠加"型的事件。根据流年特征做综合推理：

1. 婚嫁检测: 流年十神=配偶星 + 夫妻宫引动 + 红鸾/天喜 + 大运与夫妻宫互动 → 叠加即可能
2. 桃花检测: 桃花入命 + 红鸾 + 配偶星透干 + 流年合日主
3. 事业检测: 官/印星 + 驿马 + 大运官印相生 → 晋升/跳槽
4. 财运检测: 财星 + 食伤生财 + 驿马+财
5. 吉处藏凶: 用神流年被合/冲/空 → 好事打折
6. 凶中有救: 忌神流年被制/化 → 坏事有转机
7. 岁运交战: 若有岁运天克地冲→所有信号需结合喜忌重判，正负面可能反转

### 当代翻译要求（重要）

对每个信号的 prediction 和 reasoning，必须翻译成命主能看懂的当代现实场景，不能停留在八字术语上。**用非命理语言说出具体可能发生的事情**。
**禁止在 prediction 中出现原始分数或★级别**。命主不需要知道★2或置信度，只需要知道"今年财运压力大"这种能看懂的话。

参考对照（按类别）：
- 婚嫁/桃花 → 脱单/热恋/同居/订婚/结婚/分手/冷战/感情疲惫/出轨/吃回头草
- 事业 → 跳槽/晋升/转行/创业/被裁员/职场霸凌/项目压力/贵人提携/权力斗争
- 财运 → 涨薪/奖金/副业收入/投资亏损/大额支出/借贷纠纷/被借钱/退税/分红
- 健康 → 失眠/焦虑/抑郁/过劳/慢性病发作/体检异常/过敏/肠胃问题/手术
- 搬迁 → 租房/买房/换城市/留学/移民/离家/装修/办公室换址
- 人际 → 被孤立/遇知己/社交焦虑/团队矛盾/师友反目/和解/建立人脉
- 状态 → 迷茫期/动力低谷/觉醒/坚持/放弃/自我怀疑/找到方向/创造欲

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

约束: strength≤2★, 无事件返回{{"events":[]}}, 严格根据数据推理不编造, 陈述事实不渲染不吓人"""

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

    # Token 预算检查
    from ._token_budget import check_token_budget, truncate_messages
    if not check_token_budget(messages, DEEPSEEK_MODEL, payload["max_tokens"])[0]:
        messages = truncate_messages(messages, DEEPSEEK_MODEL, payload["max_tokens"])

    try:
        _timeout = get_timeout()
        full_text_parts: list[str] = []
        with shared_client(_timeout) as client:
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
    false_generations: list[dict] | None = None,
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
        false_generations=false_generations,
        year_features=year_features,
        personality_text=personality_text,
    )
    return call_llm_review(ctx)


# ═══════════════════════════════════════════════════════════════
# 大运解读（v0.14.0）
# ═══════════════════════════════════════════════════════════════

def interpret_dayun(natal: dict, dayun_modulations: list[dict],
                    personality_text: str = "",
                    false_generations: list[dict] | None = None,
                    tansheng_wangke: list[dict] | None = None) -> list[dict]:
    """批量解读大运：将 8 步大运 + 原局数据一次发给 LLM，返回每步解读。

    Returns:
        [{"index": 0, "interpretation": "...", "key_age": "..."}, ...]
    """
    if not DEEPSEEK_KEY or not LLM_REVIEW_ENABLED:
        return []

    prompt = _build_dayun_prompt(
        natal, dayun_modulations, personality_text,
        false_generations, tansheng_wangke,
    )

    messages = [
        {"role": "system", "content": "你是八字命理大运分析专家。分析每步大运对命主的影响，输出简洁直接的解读。只输出 JSON，不输出其他内容。"},
        {"role": "user", "content": prompt},
    ]

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    try:
        with shared_client(60.0) as client:
            resp = client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"[dayun_llm] status={resp.status_code} body={resp.text[:300]}",
                      file=sys.stderr)
                return []
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                print(f"[dayun_llm] empty content body={str(data)[:500]}",
                      file=sys.stderr)
                return []
            parsed = _parse_dayun_response(content, len(dayun_modulations))
            if not parsed:
                print(f"[dayun_llm] parse empty content={content[:800]}",
                      file=sys.stderr)
            return parsed
    except Exception as e:
        print(f"[dayun_llm] exception={type(e).__name__}: {e}", file=sys.stderr)
        return []


def _build_dayun_prompt(natal: dict, modulations: list[dict],
                        personality_text: str,
                        false_generations: list[dict] | None,
                        tansheng_wangke: list[dict] | None) -> str:
    """构建大运解读 prompt"""
    parts = []

    # 原局概要
    parts.append(f"八字: {natal.get('pillars', '')}")
    parts.append(f"日主: {natal.get('day_master', '')} | 格局: {natal.get('pattern', '')} | 强弱: {natal.get('strength', '')}")
    fav_wx = natal.get('favorable_wuxing', [])
    harm_wx = natal.get('harmful_wuxing', [])
    parts.append(f"喜用五行: {fav_wx} | 忌神五行: {harm_wx}")
    parts.append(f"喜用十神: {natal.get('favorable', [])} | 忌十神: {natal.get('harmful', [])}")

    # 调候
    th = natal.get("tiaohou", {})
    if th:
        parts.append(f"调候: 气候{th.get('climate','中和')} | {'废局' if th.get('is_fei_ju') else '非废局'}")

    # 假生陷阱
    if false_generations:
        for fg in false_generations:
            parts.append(f"[假生] {fg['subject']}: {fg['condition']} → {fg['effect']}")

    # 贪生忘克
    if tansheng_wangke:
        for ts in tansheng_wangke:
            parts.append(f"[贪生忘克] {'→'.join(ts['path'])} → {ts.get('note','')[:120]}")

    # 性格
    if personality_text:
        parts.append(f"命主性格: {personality_text}")

    # 大运列表
    parts.append(f"\n共{len(modulations)}步大运，请逐一解读:")
    for m in modulations:
        stem = m.get("dayun_stem", "")
        branch = m.get("dayun_branch", "")
        age = m.get("age_range", "")
        theme = m.get("theme", "")
        offset = m.get("baseline_offset", 0)
        direction = "吉" if offset > 0 else ("凶" if offset < 0 else "平")
        si = m.get("stem_interactions", [])
        bi = m.get("branch_interactions", [])
        inters = "; ".join(si + bi) if (si or bi) else "无特殊冲合"
        sfav = m.get("stem_is_favorable")
        bfav = m.get("branch_is_favorable")
        fav_note = ""
        if sfav is True: fav_note += "天干为喜"
        elif sfav is False: fav_note += "天干为忌"
        if bfav is True: fav_note += " 地支为喜"
        elif bfav is False: fav_note += " 地支为忌"
        if not fav_note: fav_note = "喜忌中性"

        parts.append(
            f"  [{m['period_index']}] {stem}{branch}运 {age} | "
            f"主题:{theme} | 十年基调:{direction} | {fav_note} | 与原局: {inters}"
        )

    # ── RAG 知识检索（v0.18.0）──
    try:
        from .rag import retrieve_for_generation, format_snippets
        ctx = {"natal": natal, "modulations": modulations}
        rag_snippets = retrieve_for_generation("dayun", ctx, top_k=4)
        if rag_snippets:
            rag_text = format_snippets(rag_snippets, max_chars=1200)
            parts.append("\n\n" + rag_text)
    except Exception:
        pass

    parts.append("""
## 任务
为每步大运写一句60字以内的解读，要点：
1. 十神主题对命主的具体影响（结合性格）
2. 与原局合冲刑害的关键含义
3. 陈述事实，不渲染不吓人
4. 忌神运说"需注意XX"，不说"有灾/要命/难逃"等恐吓词
5. 假生陷阱和贪生忘克在相关大运中如何演变
6. 用白话，不堆术语

## 输出JSON
{"periods": [
  {"index": 0, "interpretation": "甲子正财运（25-34岁）: ..."},
  ...
]}
""")
    return "\n".join(parts)


def _parse_dayun_response(content: str, expected_count: int) -> list[dict]:
    """解析大运解读 JSON 响应"""
    import json as _json
    import re as _re

    def _normalise_periods(raw) -> list:
        if isinstance(raw, dict):
            for key in ("periods", "dayun", "大运", "大运解读", "items", "results"):
                value = raw.get(key)
                if isinstance(value, list):
                    return value
            return []
        if isinstance(raw, list):
            return raw
        return []

    def _coerce_result(periods: list) -> list[dict]:
        result = []
        for idx, p in enumerate(periods[:expected_count]):
            if isinstance(p, str):
                interpretation = p.strip()
                index = idx
            elif isinstance(p, dict):
                index = p.get("index", p.get("period_index", p.get("序号", idx)))
                interpretation = (
                    p.get("interpretation")
                    or p.get("text")
                    or p.get("summary")
                    or p.get("解读")
                    or p.get("内容")
                    or ""
                )
            else:
                continue
            interpretation = str(interpretation).strip()
            if interpretation:
                result.append({"index": index, "interpretation": interpretation})
        return result

    def _json_candidates(text: str) -> list[str]:
        cleaned = text.strip()
        cleaned = _re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = _re.sub(r"\s*```$", "", cleaned)
        candidates = [cleaned]

        fenced = _re.findall(r"```(?:json)?\s*([\s\S]*?)```", text)
        candidates.extend(block.strip() for block in fenced)

        object_match = _re.search(r'\{[\s\S]*\}', text)
        if object_match:
            candidates.append(object_match.group(0))
        array_match = _re.search(r'\[[\s\S]*\]', text)
        if array_match:
            candidates.append(array_match.group(0))

        # 去重但保持顺序
        unique = []
        seen = set()
        for item in candidates:
            if item and item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    try:
        for candidate in _json_candidates(content):
            try:
                data = _json.loads(candidate)
            except _json.JSONDecodeError:
                continue
            result = _coerce_result(_normalise_periods(data))
            if result:
                return result
    except KeyError:
        pass
    return []


# ═══════════════════════════════════════════════════════════════
# 批量多年审查（v0.15.1: 节省 60% 重复 boilerplate）
# ═══════════════════════════════════════════════════════════════

def call_llm_batch_review(ctxs: list[dict], on_token=None) -> list[list[LLMReviewResult]]:
    """多年合并为一次 API 调用，共享原局/大运上下文。

    8 次独立调用 → 1 次合并调用，省去每份中重复的原局描述。

    Args:
        ctxs: 多个年份的 review context（来自 build_review_context）
        on_token: 可选 token 回调

    Returns:
        [[results for year_1], [results for year_2], ...]
    """
    if not ctxs or not is_available():
        return [[] for _ in ctxs]

    # 共享上下文从第一份 ctx 里提取原局/大运
    first = ctxs[0]
    natal = first["natal"]

    # 构建共享 + 各年特有的 prompt
    shared_parts = [
        f"八字: {natal['pillars']}",
        f"日主: {natal['day_master']} | 格局: {natal['pattern']} | 强弱: {natal['strength']}",
        f"喜用五行: {natal['favorable_wuxing']} | 忌神五行: {natal['harmful_wuxing']}",
        f"喜用十神: {natal['favorable']} | 忌十神: {natal['harmful']}",
    ]
    th = natal.get("tiaohou", {})
    shared_parts.append(f"调候: 气候{th.get('climate','中和')} | {'废局' if th.get('is_fei_ju') else '非废局'}")

    # 贪生忘克 / 假生陷阱
    for ts in natal.get("tansheng_wangke", []):
        shared_parts.append(f"[贪生忘克] {'→'.join(ts['path'])}")
    for fg in natal.get("false_generations", []):
        shared_parts.append(f"[假生陷阱] {fg['subject']}: {fg['condition']} → {fg['effect']}")

    shared_text = "\n".join(shared_parts)

    # 构建各年特有的信息
    year_sections = []
    for i, ctx in enumerate(ctxs):
        liunian = ctx["liunian"]
        dayun = ctx.get("dayun", {})
        signals = ctx.get("rule_signals", [])
        yr_feat = ctx.get("year_features", {})

        section = [f"## 年份{i+1}: {liunian['year']}年 {liunian['stem']}{liunian['branch']} | {liunian['age']}岁"]
        section.append(f"大运: {dayun.get('stem','')}{dayun.get('branch','')} | 主题'{dayun.get('theme','')}' | 十年基调偏{'吉' if dayun.get('baseline_offset',0) > 0 else '凶' if dayun.get('baseline_offset',0) < 0 else '平'}")

        if signals:
            sigs = "; ".join(f"{s['category']}/{s['direction']}/{s['strength']}★" for s in signals)
            section.append(f"规则信号: {sigs}")
        else:
            section.append("规则信号: 无")

        if yr_feat:
            section.append("流年特征:")
            for k, v in yr_feat.items():
                section.append(f"  {k}: {v}")

        # 岁运交战检测
        suiyun_str = str(yr_feat)
        if "天战" in suiyun_str or "地战" in suiyun_str:
            section.append("⚠ 本年存在岁运交战")

        year_sections.append("\n".join(section))

    prompt = f"""你是八字命理多因子综合推理器。以下是命主原局信息 + {len(ctxs)}个年份的流年数据。

## 原局（所有年份共享）
{shared_text}

{chr(10).join(year_sections)}

## 任务
为每个年份做综合推理。规则引擎已跑但可能遗漏"多弱信号叠加"型事件。

### 当代翻译要求（重要）
对每个信号的 prediction 和 reasoning，必须翻译成命主能看懂的当代现实场景，不能停留在八字术语上。用非命理语言说出具体可能发生的事情。

参考（按类别）：
- 婚嫁/桃花 → 脱单/热恋/同居/订婚/结婚/分手/冷战/出轨
- 事业 → 跳槽/晋升/转行/创业/被裁员/项目压力/贵人提携
- 财运 → 涨薪/奖金/副业/投资亏损/大额支出/被借钱
- 健康 → 失眠/焦虑/过劳/慢性病/体检异常/过敏
- 搬迁 → 租房/买房/换城市/留学/移民/装修
- 人际 → 被孤立/遇知己/社交焦虑/团队矛盾/和解
- 状态 → 迷茫/低谷/觉醒/放弃/找到方向/创造欲

**禁止在 prediction 中出现原始分数或八字术语**：如"★2""正财透干""比劫夺财"等。命主看到的是"今年财运有压力"而不是"★2"。

### 输出JSON格式
{{"years": [
  {{"year": {ctxs[0]['liunian']['year']}, "events": [
    {{"category": "...", "direction": "...", "strength": 1或2, "prediction": "...", "reasoning": "...", "confidence": 0.5-1.0}}
  ]}},
  ...
]}}

约束: strength≤2★, 无事件返回空events数组, 严格根据数据推理不编造"""

    messages = [
        {"role": "system", "content": "你是一个精确的八字命理推理器。只输出 JSON，不输出其他内容。"},
        {"role": "user", "content": prompt},
    ]

    # Token 预算
    from ._token_budget import check_token_budget, truncate_messages
    if not check_token_budget(messages, DEEPSEEK_MODEL, 4096)[0]:
        messages = truncate_messages(messages, DEEPSEEK_MODEL, 4096)

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
        _timeout = get_timeout() * 2  # 多年批量调用给更多时间
        full_text_parts: list[str] = []
        with shared_client(_timeout) as client:
            with client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    return [[] for _ in ctxs]
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
            return [[] for _ in ctxs]

        return _parse_batch_response(content, ctxs)

    except Exception:
        return [[] for _ in ctxs]


def _parse_batch_response(content: str, ctxs: list[dict]) -> list[list[LLMReviewResult]]:
    """解析批量审查的 JSON 响应，按年份分发结果。"""
    import re as _re
    import json as _json

    results_per_year: list[list[LLMReviewResult]] = [[] for _ in ctxs]

    match = _re.search(r'\{[\s\S]*"years"[\s\S]*\}', content)
    if not match:
        return results_per_year

    try:
        data = _json.loads(match.group(0))
        years_data = data.get("years", [])
    except _json.JSONDecodeError:
        return results_per_year

    valid_categories = {"婚嫁", "事业", "财运", "健康", "搬迁", "桃花", "人际", "状态"}
    valid_directions = {"正面", "负面", "中性"}

    for yr_data in years_data:
        yr = yr_data.get("year")
        # 按 year 匹配 ctx
        yr_idx = None
        for i, ctx in enumerate(ctxs):
            if ctx["liunian"]["year"] == yr:
                yr_idx = i
                break

        if yr_idx is None or yr_idx >= len(results_per_year):
            continue

        for evt in yr_data.get("events", []):
            cat = evt.get("category", "")
            if cat not in valid_categories:
                continue
            direction = evt.get("direction", "中性")
            if direction not in valid_directions:
                direction = "中性"
            strength = evt.get("strength", 1)
            if not isinstance(strength, (int, float)):
                strength = 1
            strength = max(1, min(2, int(strength)))
            confidence = evt.get("confidence", 0.6)
            if not isinstance(confidence, (int, float)):
                confidence = 0.6
            confidence = max(0.0, min(1.0, float(confidence)))
            if confidence < 0.5:
                continue

            results_per_year[yr_idx].append(LLMReviewResult(
                year=yr,
                category=cat,
                direction=direction,
                strength=strength,
                prediction=evt.get("prediction", "")[:60],
                reasoning=evt.get("reasoning", "")[:120],
                triggers=[f"[LLM推理] {evt.get('reasoning', '')[:60]}"],
                confidence=confidence,
                source="llm",
            ))

    return results_per_year


def enrich_dayun_interpretations(chart) -> list[dict]:
    """从 BaziChart 提取上下文，调用 LLM 解读大运（不阻塞 build_chart）。
    调用方负责在合适的时机调用（如 CLI 渲染时）。
    """
    if not chart.dayun_modulations:
        return []
    try:
        natal_ctx = {
            "pillars": f"{chart.year.stem.value}{chart.year.branch.value} "
                       f"{chart.month.stem.value}{chart.month.branch.value} "
                       f"{chart.day.stem.value}{chart.day.branch.value} "
                       f"{chart.hour.stem.value}{chart.hour.branch.value}",
            "day_master": f"{chart.day_master.value}({chart.day_master.wuxing.value}·{chart.day_master.yinyang})",
            "pattern": chart.pattern,
            "strength": (chart._yongshen_result or {}).get("strength", "中和"),
            "favorable_wuxing": (chart._yongshen_result or {}).get("favorable_wuxing", []),
            "harmful_wuxing": (chart._yongshen_result or {}).get("harmful_wuxing", []),
            "favorable": (chart._yongshen_result or {}).get("favorable", []),
            "harmful": (chart._yongshen_result or {}).get("harmful", []),
            "tiaohou": chart.tiaohou_result or {},
        }
        personality_text = ""
        if chart.personality_result:
            personality_text = chart.personality_result.get("raw_text", "")
        return interpret_dayun(
            natal=natal_ctx,
            dayun_modulations=chart.dayun_modulations,
            personality_text=personality_text,
            false_generations=chart.false_generations,
            tansheng_wangke=chart.tansheng_wangke,
        )
    except Exception:
        return []
