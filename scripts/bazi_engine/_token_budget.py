"""Token 预算估算器 — 轻量级，不依赖 tiktoken。

使用简单的中文 token 估算（中文约 1 字 ≈ 1 token，英文约 1 词 ≈ 1.3 token）。
误差约 ±20%，但对于预算控制足够了。
import re
"""

# DeepSeek 模型上下文窗口
MODEL_CONTEXT_WINDOWS = {
    "deepseek-chat": 64000,
    "deepseek-v4-flash": 64000,
    "deepseek-v4-pro": 64000,
    "deepseek-reasoner": 64000,
}


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
    if estimate_tokens(text) <= max_tokens:
        return text

    # 二分查找截断位置
    lo, hi = 0, len(text)
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if estimate_tokens(text[:mid]) > max_tokens:
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

    return text[:cutoff] + "\n\n[上下文过长，已截断]"


def check_token_budget(messages: list[dict], model: str, max_output: int = 4096) -> tuple[bool, int, int]:
    """检查是否在 token 预算内。

    Returns:
        (fits, estimated_input_tokens, available_budget)
    """
    context_window = MODEL_CONTEXT_WINDOWS.get(model, 64000)
    input_tokens = estimate_messages_tokens(messages)
    available = context_window - max_output
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
    context_window = MODEL_CONTEXT_WINDOWS.get(model, 64000)
    budget = context_window - max_output

    # 计算 system prompt token
    system_tokens = 0
    for i, msg in enumerate(messages):
        if msg.get("role") == "system":
            system_tokens = estimate_tokens(msg["content"])
            break

    # 如果 system prompt 本身就超过预算（极端情况），截断 system prompt
    if system_tokens > budget * 0.8 and preserve_system:
        system_idx = next(i for i, m in enumerate(messages) if m["role"] == "system")
        truncated_system = truncate_text(messages[system_idx]["content"], budget // 2)
        messages = list(messages)
        messages[system_idx] = {"role": "system", "content": truncated_system}
        return messages

    # 从后往前保留消息（保留最新的上下文）
    result = []
    remaining = budget
    for msg in reversed(messages):
        msg_tokens = estimate_tokens(msg["content"]) + 4
        if msg.get("role") == "system":
            # system prompt 必须保留
            result.append(msg)
            remaining -= msg_tokens
        elif remaining >= msg_tokens:
            result.insert(0, msg)
            remaining -= msg_tokens
        else:
            # 截断最后一条 user message
            truncated = truncate_text(msg["content"], remaining - 4)
            if truncated:
                msg["content"] = truncated
                result.insert(0, msg)
            break

    return result
