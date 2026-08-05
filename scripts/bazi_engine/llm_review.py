"""LLM 推理层 (v0.9.0) — Hybrid 模式：规则引擎主跑 + LLM 边界年份二次判断

设计原则:
- 规则引擎不变，继续产生 1-3★ 信号
- LLM 只介入"规则引擎判定为弱信号或无信号"的年份
- LLM 接收结构化特征（不是原始八字），做多弱信号综合推理
- LLM 输出置信度低于规则引擎（标记 source="llm"）

集成: DeepSeek API (同步调用，非流式)
"""

import json
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Any

import httpx

from ._deepseek_config import (
    DEEPSEEK_API_URL,
    DEEPSEEK_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_REVIEW_MODEL,
    LLM_REVIEW_ENABLED,
    get_timeout,
    is_available,
)
from ._http import shared_client
from ._token_budget import prepare_messages_for_request

logger = logging.getLogger(__name__)


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
    review_status: str = "有信号"  # "有信号"|"无明显信号"|"未完成"


# ═══════════════════════════════════════════════════════════════
# 边界判定：哪些年份需要 LLM 介入
# ═══════════════════════════════════════════════════════════════

# LLM 介入的目标类别（固定顺序用于逐类审阅矩阵）
_REVIEW_CATEGORIES = ("婚嫁", "桃花", "事业", "财运", "健康", "搬迁")
_REVIEW_CATEGORY_SET = set(_REVIEW_CATEGORIES)
_VALID_REVIEW_CATEGORIES = _REVIEW_CATEGORY_SET | {"人际", "状态"}
_VALID_REVIEW_DIRECTIONS = {"正面", "负面", "中性"}
_PREDICTION_MAX_CHARS = 120
_REASONING_MAX_CHARS = 240
_TRIGGER_MAX_CHARS = 120
_SENTENCE_ENDINGS = "。！？!?."
_CLAUSE_ENDINGS = "，,；;、"
_LLM_TRIGGER_PREFIX = "[LLM推理] "
_ANNUAL_REVIEW_MAX_OUTPUT_TOKENS = max(
    512, int(os.getenv("BAZI_LLM_REVIEW_MAX_OUTPUT_TOKENS", "2048"))
)
_ANNUAL_BATCH_MAX_OUTPUT_TOKENS = max(
    _ANNUAL_REVIEW_MAX_OUTPUT_TOKENS,
    int(os.getenv("BAZI_LLM_BATCH_MAX_OUTPUT_TOKENS", "3072")),
)


def should_invoke_llm(events: list, year: int, age: int,
                       target_categories: set[str] | None = None) -> bool:
    """判断某一年是否需要 LLM 二次判断。

    条件：年龄在合理范围内，且目标类别中仍有规则层未覆盖的类别。
    规则层只覆盖部分类别时，交给 LLM 做跨类别的补充审阅；当所有
    目标类别都已有 ≥2★ 规则信号时，规则结果已经足够，不再重复调用。

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

    # 检查目标类别中哪些有 ≥2★。类别覆盖不足本身就是边界信号，不能
    # 只统计 1★ 事件：同类事件在后续合并前，弱信号可能暂时还未出现。
    strong_in_target = set()
    for e in events:
        if e.category in target_categories and e.strength >= 2:
            strong_in_target.add(e.category)

    # 如果目标类别全部都有 ≥2★ 信号，不需要 LLM；否则让 LLM 补充
    # 规则层没有覆盖或仅有弱信号的类别。
    return not strong_in_target >= target_categories


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
    relationship_state: str = "unknown",
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
        "decision_policy": base.get("decision_policy", {}),
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
    ctx["relationship_context"] = {
        "state": relationship_state if relationship_state in {
            "single", "dating", "married", "unknown",
        } else "unknown",
        "window": "",
        "phase": "",
        "peak_year": None,
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
            "evidence": [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in e.evidence[:5]
            ],
            "conflicts": e.conflicts[:5],
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
    policy = natal.get("decision_policy", {})
    if policy:
        effective = policy.get("effective", {})
        prompt_parts.append(
            "喜忌裁决: "
            f"优先级={' > '.join(policy.get('precedence', []))} | "
            f"当前有效喜={effective.get('favorable', natal['favorable'])} | "
            f"当前有效忌={effective.get('harmful', natal['harmful'])}"
        )
        if policy.get("conflicts"):
            prompt_parts.append(f"喜忌冲突记录: {'; '.join(policy['conflicts'][:4])}")
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

    relationship_context = ctx.get("relationship_context", {})
    state_label = {
        "single": "单身",
        "dating": "交往中",
        "married": "已婚",
        "unknown": "未提供",
    }.get(relationship_context.get("state", "unknown"), "未提供")
    prompt_parts.append(
        f"婚恋解释上下文: 当前状态={state_label} | "
        f"窗口={relationship_context.get('window') or '无连续窗口'} | "
        f"阶段={relationship_context.get('phase') or '单年判断'} | "
        f"峰值年={relationship_context.get('peak_year') or '未定'}"
    )

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
                f" | 证据={s.get('evidence', [])[:2]}"
                f" | 冲突={s.get('conflicts', [])[:2]}"
            )
        prompt_parts.append("规则引擎信号:\n" + "\n".join(sig_lines))
    else:
        prompt_parts.append("规则引擎信号: 无")

    context_text = "\n".join(prompt_parts)

    prompt = f"""你是八字命理多因子综合推理器。以下是某命主在特定流年的结构化特征数据。

{context_text}{_suiyun_knowledge(ctx)}

## 任务

规则引擎已经跑过但可能遗漏"多弱信号叠加"型的事件。根据流年特征做综合推理：

LLM 只能解释和整合已提供的结构化证据，不得自行重算三合、藏干、强弱或喜忌；
若证据冲突或来源不足，应降低置信度并在 reasoning 中说明，不得覆盖规则层结论。

必须逐项审阅婚嫁、桃花、事业、财运、健康、搬迁六类，不得跳项。先在 category_matrix
中对六类分别标记 1（有信号）或 0（无明显信号），再仅为标记 1 的类别输出事件详情。

1. 婚嫁检测: 婚嫁类别只能解释规则层已经给出的婚嫁信号（至少2星）；
   夫妻宫、桃花、红鸾/天喜单独或叠加，只能标记桃花/关系活跃，不能自行升级为订婚或结婚。
2. 桃花检测: 桃花入命 + 红鸾 + 配偶星透干 + 流年合日主
3. 事业检测: 官/印星 + 驿马 + 大运官印相生 → 晋升/跳槽
4. 财运检测: 财星 + 食伤生财 + 驿马+财
5. 吉处藏凶: 用神流年被合/冲/空 → 好事打折
6. 凶中有救: 忌神流年被制/化 → 坏事有转机
7. 岁运交战: 若有岁运天克地冲→所有信号需结合喜忌重判，正负面可能反转

### 婚恋状态与连续窗口（必须遵守）

- 婚恋窗口中的连续年份是同一段关系进程；只有峰值年可以描述“关系定型候选”，其余年份写认识、升温、延续或磨合。
- 当前状态为“已婚”时，婚嫁预测必须改写为配偶、共同生活或家庭安排，不得出现“脱单、订婚、结婚、再婚”。
- 当前状态未知时必须使用条件句，例如“未婚可关注……，已婚则对应……”，不得把婚礼写成确定事件。
- 不得输出“结婚概率”或把 confidence 当成真实概率；它只是模型内部的审阅质量字段。

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
  "category_matrix": {{"婚嫁": 0, "桃花": 1, "事业": 0, "财运": 0, "健康": 0, "搬迁": 0}},
  "events": [
    {{
      "category": "婚嫁/事业/财运/健康/搬迁/桃花",
      "direction": "正面/负面/中性",
      "strength": 1或2,
      "prediction": "一句话(≤30字)",
      "reasoning": "推理(≤80字): 哪几个特征叠加→为何成立"
    }}
  ]
}}

约束: category_matrix 必须包含六类且每类只能为0或1；strength≤2★；无事件时 events 返回空数组；
严格根据数据推理不编造，陈述事实不渲染不吓人"""

    return prompt


# ═══════════════════════════════════════════════════════════════
# LLM 调用
# ═══════════════════════════════════════════════════════════════

def call_llm_review(
    ctx: dict,
    on_token=None,
    cancel_event: threading.Event | None = None,
) -> list[LLMReviewResult]:
    """调用 DeepSeek API（流式），解析响应。

    v0.11.1: 改用流式 API（stream=True），边收token边攒，首token延迟更低。
    v0.11.2: 支持 on_token 回调，供前端逐字渲染推理过程。

    Returns:
        LLMReviewResult 列表。API 失败或 LLM 无发现时返回空列表。
    """
    if not DEEPSEEK_KEY or _cancelled(cancel_event):
        return []

    prompt = build_review_prompt(ctx)

    messages = [
        {"role": "system", "content": "你是一个精确的八字命理推理器。只输出 JSON，不输出其他内容。"},
        {"role": "user", "content": prompt},
    ]
    max_output_tokens = _ANNUAL_REVIEW_MAX_OUTPUT_TOKENS
    messages = prepare_messages_for_request(
        messages,
        DEEPSEEK_REVIEW_MODEL,
        max_output_tokens,
        operation="liunian_review",
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_REVIEW_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": 0.3,
        "max_tokens": max_output_tokens,
    }

    try:
        if _cancelled(cancel_event):
            return []
        _timeout = get_timeout(DEEPSEEK_REVIEW_MODEL)
        full_text_parts: list[str] = []
        finish_reason = None
        with (
            shared_client(_timeout) as client,
            client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers) as resp,
        ):
            if resp.status_code != 200:
                return []

            for line in resp.iter_lines():
                if _cancelled(cancel_event):
                    return []
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
                        finish_reason = choices[0].get("finish_reason") or finish_reason
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_text_parts.append(content)
                            if on_token and not _cancelled(cancel_event):
                                on_token(content)
                except json.JSONDecodeError:
                    continue

        content = "".join(full_text_parts)
        logger.info(
            "LLM annual review completed year=%s model=%s finish_reason=%s content_length=%s",
            ctx.get("liunian", {}).get("year"),
            DEEPSEEK_REVIEW_MODEL,
            finish_reason or "unknown",
            len(content),
        )
        if finish_reason == "length":
            logger.warning(
                "LLM annual review hit output limit year=%s",
                ctx.get("liunian", {}).get("year"),
            )
        if not content or _cancelled(cancel_event):
            return []

        parsed = _parse_review_response(content, ctx["liunian"]["year"])
        return _enforce_relationship_review_policy(parsed, ctx)

    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return []


# ═══════════════════════════════════════════════════════════════
# 响应解析
# ═══════════════════════════════════════════════════════════════

def _parse_review_response(content: str, year: int) -> list[LLMReviewResult]:
    """解析 LLM 的 JSON 响应"""
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

    return _parse_category_review_payload(data, year)


def _coerce_matrix_value(value) -> bool | None:
    """将模型可能使用的布尔、数字或中文状态统一为三态。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "有", "有信号", "明显"}:
            return True
        if normalized in {"0", "false", "no", "无", "无信号", "无明显信号"}:
            return False
    return None


def _trim_review_text(value, max_chars: int) -> str:
    """Limit review prose without silently cutting through a complete sentence."""
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text

    prefix = text[:max_chars]
    sentence_end = max(prefix.rfind(mark) for mark in _SENTENCE_ENDINGS)
    if sentence_end >= 0:
        return prefix[:sentence_end + 1].rstrip()

    hard_prefix = text[:max_chars - 1]
    clause_end = max(hard_prefix.rfind(mark) for mark in _CLAUSE_ENDINGS)
    if clause_end >= max_chars // 2:
        hard_prefix = hard_prefix[:clause_end + 1].rstrip(_CLAUSE_ENDINGS + " ")
    return hard_prefix.rstrip() + "…"


def _parse_positive_review_event(evt: dict, year: int) -> LLMReviewResult | None:
    if not isinstance(evt, dict):
        return None
    category = evt.get("category", "")
    if category not in _VALID_REVIEW_CATEGORIES:
        return None

    direction = evt.get("direction", "中性")
    if direction not in _VALID_REVIEW_DIRECTIONS:
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
        return None

    prediction = _trim_review_text(evt.get("prediction", ""), _PREDICTION_MAX_CHARS)
    reasoning = _trim_review_text(evt.get("reasoning", ""), _REASONING_MAX_CHARS)
    trigger_budget = _TRIGGER_MAX_CHARS - len(_LLM_TRIGGER_PREFIX)
    trigger_reasoning = _trim_review_text(reasoning, trigger_budget)
    return LLMReviewResult(
        year=year,
        category=category,
        direction=direction,
        strength=strength,
        prediction=prediction,
        reasoning=reasoning,
        triggers=[f"{_LLM_TRIGGER_PREFIX}{trigger_reasoning}"] if reasoning else [],
        confidence=confidence,
        source="llm",
        review_status="有信号",
    )


def _status_only_review(year: int, category: str, status: str) -> LLMReviewResult:
    prediction = "未发现明显信号" if status == "无明显信号" else "AI未完成该类别审阅"
    return LLMReviewResult(
        year=year,
        category=category,
        direction="中性",
        strength=0,
        prediction=prediction,
        reasoning="",
        triggers=[],
        confidence=0.0,
        source="llm",
        review_status=status,
    )


def _parse_category_review_payload(data: dict, year: int) -> list[LLMReviewResult]:
    """解析逐类矩阵；旧版仅含 events 的响应仍按原语义兼容。"""
    events = data.get("events", [])
    if not isinstance(events, list):
        events = []
    parsed_events = [
        parsed
        for event in events
        if (parsed := _parse_positive_review_event(event, year)) is not None
    ]

    matrix = data.get("category_matrix")
    if not isinstance(matrix, dict):
        return parsed_events

    by_category: dict[str, list[LLMReviewResult]] = {}
    for event in parsed_events:
        by_category.setdefault(event.category, []).append(event)

    results: list[LLMReviewResult] = []
    for category in _REVIEW_CATEGORIES:
        if by_category.get(category):
            results.extend(by_category[category])
            continue
        matrix_value = _coerce_matrix_value(matrix.get(category))
        status = "无明显信号" if matrix_value is False else "未完成"
        results.append(_status_only_review(year, category, status))

    return results


def _enforce_relationship_review_policy(
    results: list[LLMReviewResult], ctx: dict,
) -> list[LLMReviewResult]:
    """在解析边界再拦截 AI 的婚嫁升级，避免提示词漂移改变规则语义。"""
    rule_signals = ctx.get("rule_signals", [])
    has_rule_hunjia = any(
        signal.get("category") == "婚嫁" and signal.get("strength", 0) >= 2
        for signal in rule_signals
    )
    relationship_context = ctx.get("relationship_context", {})
    state = relationship_context.get("state", "unknown")
    phase = relationship_context.get("phase", "")

    normalized: list[LLMReviewResult] = []
    for result in results:
        if result.category != "婚嫁" or result.review_status != "有信号":
            normalized.append(result)
            continue

        if not has_rule_hunjia:
            normalized.append(_status_only_review(result.year, "婚嫁", "无明显信号"))
            continue

        if state == "married":
            result.prediction = "婚姻关系被引动，重点看配偶、共同生活或家庭安排，不代表再次结婚"
        elif state == "unknown":
            result.prediction = "未婚可关注关系定型，已婚则对应配偶与家庭事项；不作确定婚期判断"
        elif phase and phase != "peak":
            result.prediction = "婚恋窗口处于推进或磨合阶段，重点看关系进程，不等于当年结婚"
        elif state == "dating":
            result.prediction = "交往关系存在定型机会，是否订婚或结婚仍取决于现实进展"
        normalized.append(result)
    return normalized


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
    max_output_tokens = 4096
    messages = prepare_messages_for_request(
        messages,
        DEEPSEEK_MODEL,
        max_output_tokens,
        operation="dayun_interpretation",
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": max_output_tokens,
    }

    try:
        with shared_client(60.0) as client:
            resp = client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.warning("dayun LLM request failed status=%s", resp.status_code)
                return []
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                logger.warning("dayun LLM response had empty content")
                return []
            parsed = _parse_dayun_response(content, len(dayun_modulations))
            if not parsed:
                logger.warning("dayun LLM response could not be parsed")
            return parsed
    except Exception as error:
        logger.warning("dayun LLM request failed type=%s", type(error).__name__)
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
        if sfav is True:
            fav_note += "天干为喜"
        elif sfav is False:
            fav_note += "天干为忌"
        if bfav is True:
            fav_note += " 地支为喜"
        elif bfav is False:
            fav_note += " 地支为忌"
        if not fav_note:
            fav_note = "喜忌中性"

        parts.append(
            f"  [{m['period_index']}] {stem}{branch}运 {age} | "
            f"主题:{theme} | 十年基调:{direction} | {fav_note} | 与原局: {inters}"
        )

    # ── RAG 知识检索（v0.18.0）──
    try:
        from .rag import format_snippets, retrieve_for_generation
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

def call_llm_batch_review(
    ctxs: list[dict],
    on_token=None,
    cancel_event: threading.Event | None = None,
) -> list[list[LLMReviewResult]]:
    """小批量合并 API 调用，共享原局/大运上下文。

    Args:
        ctxs: 多个年份的 review context（来自 build_review_context）
        on_token: 可选 token 回调

    Returns:
        [[results for year_1], [results for year_2], ...]
    """
    if not ctxs or not is_available() or _cancelled(cancel_event):
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
        relationship_context = ctx.get("relationship_context", {})
        section.append(
            f"婚恋上下文: 状态={relationship_context.get('state', 'unknown')} | "
            f"窗口={relationship_context.get('window') or '无连续窗口'} | "
            f"阶段={relationship_context.get('phase') or '单年判断'} | "
            f"峰值年={relationship_context.get('peak_year') or '未定'}"
        )

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
每个年份都必须逐项审阅婚嫁、桃花、事业、财运、健康、搬迁六类，并在
category_matrix 中完整返回六个 0/1 状态；events 只写状态为 1 的类别详情。

婚嫁类别只能解释该年份规则层已有的婚嫁信号（至少2星），不得用桃花、天喜或夫妻宫
单独升级出婚嫁；连续年份属于同一婚恋窗口，只有峰值年可写关系定型候选。已婚状态
只写配偶、共同生活或家庭安排，未知状态必须用“未婚/已婚分别表现”的条件句。

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
  {{"year": {ctxs[0]['liunian']['year']},
    "category_matrix": {{"婚嫁": 0, "桃花": 1, "事业": 0, "财运": 0, "健康": 0, "搬迁": 0}},
    "events": [
    {{"category": "...", "direction": "...", "strength": 1或2, "prediction": "...", "reasoning": "..."}}
  ]}},
  ...
]}}

约束: 每年 category_matrix 必须包含六类且每类只能为0或1；strength≤2★；
无事件时返回空 events 数组；严格根据数据推理不编造"""

    messages = [
        {"role": "system", "content": "你是一个精确的八字命理推理器。只输出 JSON，不输出其他内容。"},
        {"role": "user", "content": prompt},
    ]
    max_output_tokens = _ANNUAL_BATCH_MAX_OUTPUT_TOKENS
    messages = prepare_messages_for_request(
        messages,
        DEEPSEEK_REVIEW_MODEL,
        max_output_tokens,
        operation="liunian_batch_review",
    )

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_REVIEW_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": 0.3,
        "max_tokens": max_output_tokens,
    }

    try:
        if _cancelled(cancel_event):
            return [[] for _ in ctxs]
        _timeout = get_timeout(DEEPSEEK_REVIEW_MODEL) * 2
        full_text_parts: list[str] = []
        finish_reason = None
        with (
            shared_client(_timeout) as client,
            client.stream("POST", DEEPSEEK_API_URL, json=payload, headers=headers) as resp,
        ):
            if resp.status_code != 200:
                logger.warning(
                    "LLM batch review provider rejected status=%s years=%s",
                    resp.status_code,
                    len(ctxs),
                )
                return [[] for _ in ctxs]
            for line in resp.iter_lines():
                if _cancelled(cancel_event):
                    return [[] for _ in ctxs]
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
                        finish_reason = choices[0].get("finish_reason") or finish_reason
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_text_parts.append(content)
                            if on_token and not _cancelled(cancel_event):
                                on_token(content)
                except json.JSONDecodeError:
                    continue

        content = "".join(full_text_parts)
        logger.info(
            "LLM batch review completed years=%s model=%s finish_reason=%s content_length=%s",
            [ctx["liunian"]["year"] for ctx in ctxs],
            DEEPSEEK_REVIEW_MODEL,
            finish_reason or "unknown",
            len(content),
        )
        if finish_reason == "length":
            logger.warning(
                "LLM batch review hit output limit years=%s",
                [ctx["liunian"]["year"] for ctx in ctxs],
            )
        if not content or _cancelled(cancel_event):
            logger.warning("LLM batch review returned empty content years=%s", len(ctxs))
            return [[] for _ in ctxs]

        parsed = _parse_batch_response(content, ctxs)
        parsed = [
            _enforce_relationship_review_policy(year_results, ctx)
            for year_results, ctx in zip(parsed, ctxs, strict=False)
        ]
        missing_years = [
            ctxs[index]["liunian"]["year"]
            for index, year_results in enumerate(parsed)
            if not year_results
        ]
        if missing_years:
            logger.warning(
                "LLM batch review response incomplete years=%s content_length=%s",
                missing_years,
                len(content),
            )
        return parsed

    except Exception as error:
        logger.warning(
            "LLM batch review failed years=%s type=%s",
            len(ctxs),
            type(error).__name__,
        )
        return [[] for _ in ctxs]


def _cancelled(cancel_event: threading.Event | None) -> bool:
    return bool(cancel_event and cancel_event.is_set())


def _parse_batch_response(content: str, ctxs: list[dict]) -> list[list[LLMReviewResult]]:
    """解析批量审查的 JSON 响应，按年份分发结果。"""
    import json as _json
    import re as _re

    results_per_year: list[list[LLMReviewResult]] = [[] for _ in ctxs]

    match = _re.search(r'\{[\s\S]*"years"[\s\S]*\}', content)
    if not match:
        return results_per_year

    try:
        data = _json.loads(match.group(0))
        years_data = data.get("years", [])
    except _json.JSONDecodeError:
        return results_per_year

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

        results_per_year[yr_idx] = _parse_category_review_payload(yr_data, yr)

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
