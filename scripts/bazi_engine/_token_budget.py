"""Token 预算估算器 — 轻量级，不依赖 tiktoken。

使用简单的中文 token 估算（中文约 1 字 ≈ 1 token，英文约 1 词 ≈ 1.3 token）。
误差约 ±20%，但对于预算控制足够了。
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

DEFAULT_MODEL_CONTEXT_WINDOW = 64_000
DEFAULT_APPLICATION_CONTEXT_WINDOW = 1_000_000
APPLICATION_CONTEXT_LIMIT_ENV = "BAZI_LLM_CONTEXT_LIMIT"

# DeepSeek 模型上下文窗口

MODEL_CONTEXT_WINDOWS = {
    "deepseek-chat": 64_000,
    "deepseek-v4-flash": 1_000_000,
    "deepseek-v4-pro": 64_000,
    "deepseek-reasoner": 64_000,
}


def get_model_context_window(model: str) -> int:
    """Return the provider context capacity registered for a model."""
    return MODEL_CONTEXT_WINDOWS.get(model, DEFAULT_MODEL_CONTEXT_WINDOW)


def get_application_context_window(model: str) -> int:
    """Return the configured application budget, capped by model capacity."""
    model_window = get_model_context_window(model)
    raw_limit = os.getenv(APPLICATION_CONTEXT_LIMIT_ENV, "").strip()
    if not raw_limit:
        return min(DEFAULT_APPLICATION_CONTEXT_WINDOW, model_window)

    try:
        configured_limit = int(raw_limit)
    except ValueError:
        logger.warning(
            "invalid %s; using default=%s",
            APPLICATION_CONTEXT_LIMIT_ENV,
            DEFAULT_APPLICATION_CONTEXT_WINDOW,
        )
        configured_limit = DEFAULT_APPLICATION_CONTEXT_WINDOW

    if configured_limit <= 0:
        logger.warning(
            "%s must be positive; using default=%s",
            APPLICATION_CONTEXT_LIMIT_ENV,
            DEFAULT_APPLICATION_CONTEXT_WINDOW,
        )
        configured_limit = DEFAULT_APPLICATION_CONTEXT_WINDOW

    return min(configured_limit, model_window)


def estimate_tokens(text: str) -> int:
    """快速估算文本的 token 数量。

    规则：
    - 中文字符 ≈ 1 token
    - 英文单词 ≈ 1.3 token
    - 数字和标点 ≈ 0.5 token
    """

    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    digits_punct = len(re.findall(r'[0-9\W]', text)) - english_words

    return int(chinese_chars * 1.0 + english_words * 1.3 + digits_punct * 0.5)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """估算一组 messages 的总 token 数。"""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
        total += estimate_tokens(msg.get("role", ""))
        total += 4  # message overhead
    return total


def truncate_text(text: str, max_tokens: int) -> str:
    """按 token 预算截断文本，保留前部。

    以句号/换行为截断点，避免截断词语中间。
    """
    if max_tokens <= 0:
        return ""
    if estimate_tokens(text) <= max_tokens:
        return text

    marker = "\n\n[上下文过长，已截断]"
    content_budget = max_tokens - estimate_tokens(marker)
    if content_budget <= 0:
        return ""

    # 二分查找截断位置
    lo, hi = 0, len(text)
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if estimate_tokens(text[:mid]) > content_budget:
            hi = mid
        else:
            lo = mid

    # 回退到最近的分隔符
    cutoff = lo
    for sep in ("。", "\n", "；", "，", " ", "\t"):
        last_sep = text[:cutoff].rfind(sep)
        if last_sep > cutoff * 0.6:  # 不截太多
            cutoff = last_sep + len(sep)
            break

    return text[:cutoff] + marker


def check_token_budget(messages: list[dict], model: str, max_output: int = 4096) -> tuple[bool, int, int]:
    """检查是否在 token 预算内。

    Returns:
        (fits, estimated_input_tokens, available_budget)
    """
    context_window = get_application_context_window(model)
    input_tokens = estimate_messages_tokens(messages)
    available = max(0, context_window - max_output)
    return input_tokens <= available, input_tokens, available


def truncate_messages(messages: list[dict], model: str, max_output: int = 4096,
                       preserve_system: bool = True) -> list[dict]:
    """截断 messages 以适应 token 预算，优先保留 system prompt 和最新的消息。

    Args:
        messages: 原始 messages 列表
        model: 模型名称
        max_output: 预留的输出 token 数
        preserve_system: 是否保护 system prompt 不被截断

    Returns:
        截断后的 messages 列表
    """
    context_window = get_application_context_window(model)
    budget = max(0, context_window - max_output)
    if not messages or budget <= 0:
        return []

    copied_messages = [dict(message) for message in messages]
    if preserve_system:
        system_messages = [message for message in copied_messages if message.get("role") == "system"]
        non_system_messages = [message for message in copied_messages if message.get("role") != "system"]
    else:
        system_messages = []
        non_system_messages = copied_messages

    system_tokens = estimate_messages_tokens(system_messages)
    if system_messages and system_tokens > budget * 0.8:
        first_system = system_messages[0]
        overhead = estimate_tokens(str(first_system.get("role", ""))) + 4
        first_system["content"] = truncate_text(
            str(first_system.get("content", "")),
            max(0, budget // 2 - overhead),
        )
        system_messages = [first_system] if first_system["content"] else []
        system_tokens = estimate_messages_tokens(system_messages)

    remaining = max(0, budget - system_tokens)
    selected_messages: list[dict] = []
    for message in reversed(non_system_messages):
        message_tokens = estimate_messages_tokens([message])
        if message_tokens <= remaining:
            selected_messages.append(message)
            remaining -= message_tokens
            continue

        overhead = estimate_tokens(str(message.get("role", ""))) + 4
        truncated = truncate_text(str(message.get("content", "")), remaining - overhead)
        if truncated:
            message["content"] = truncated
            selected_messages.append(message)
        break

    selected_messages.reverse()
    return system_messages + selected_messages


def prepare_messages_for_request(
    messages: list[dict],
    model: str,
    max_output: int,
    *,
    operation: str,
) -> list[dict]:
    """Apply the shared budget and emit privacy-safe numeric telemetry."""
    fits, estimated_before, available = check_token_budget(messages, model, max_output)
    prepared = messages if fits else truncate_messages(messages, model, max_output)
    estimated_after = estimate_messages_tokens(prepared)

    log_budget = logger.info if fits else logger.warning
    log_budget(
        "llm_token_budget operation=%s model=%s model_context_window=%s "
        "application_context_window=%s max_output_tokens=%s available_input_tokens=%s "
        "estimated_input_tokens_before=%s estimated_input_tokens_after=%s truncated=%s",
        operation,
        model,
        get_model_context_window(model),
        get_application_context_window(model),
        max_output,
        available,
        estimated_before,
        estimated_after,
        not fits,
    )
    return prepared
