"""AI 八字追问 — DeepSeek V4-Pro 集成 + 激活码管理"""

import json
import os
import re
import time
from pathlib import Path
from typing import AsyncGenerator

import httpx

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

from ._deepseek_config import DEEPSEEK_API_URL, DEEPSEEK_KEY, DEEPSEEK_MODEL, get_timeout

_ACTIVATION_FILE = Path(__file__).resolve().parent / "activation_codes.json"

# ═══════════════════════════════════════════════════════════════
# System Prompt
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_BASE = """你是八字命理文化解说助手，基于《渊海子平》《滴天髓》《三命通会》《穷通宝鉴》等经典为用户解读八字。

## 核心规则（必须遵守）

1. **不预测生死、疾病、灾祸**——被问到此类问题时，礼貌拒绝并说明命理不能替代医疗/法律/安全判断
2. **不提供投资/博彩建议**——不推荐具体股票、彩票号码、赌博策略
3. **不用确定性断言**——用"倾向于""可能""传统命理认为""古典文献记载"等表述，不说"你一定会…""你命中有…"
4. **文化参考定位**——每条回复末尾追加: 「（以上内容由 AI 生成，基于传统命理文化，仅供娱乐参考，不替代专业建议）」
5. **不编造权威出处**——引用经典时必须是真正存在的原文，不确定时只说"传统命理认为"
6. **鼓励正向思考**——解读运势时强调人的主观能动性，不制造焦虑
7. **重复问题提示**——如果用户提出的问题与对话历史中已问过的相似，先简短总结之前的回答，再补充新的角度，并提醒用户"这个问题之前探讨过，你可以追问更具体的细节"

## 岁运交战（概念速查）

当用户问及"大运和流年的关系""岁运交战""天克地冲""征太岁"时，参考以下知识：

- **定义**：大运干支与流年干支天干相克+地支相冲（天克地冲），古籍称"反吟""征太岁"
- **君臣关系**：太岁(流年)为君，大运为臣；臣冲克君→多主动荡是非破财
- **运伐岁**(大运天干克流年天干)：下犯上，凶性较重
- **岁伐运**(流年天干克大运天干)：上制下，凶性稍减
- **天战**(天干相克)：表层影响事业人际/口舌
- **地战**(地支相冲)：底层动摇环境健康家庭，比天战严重1.5-2倍
- **看喜忌**：冲克喜用神→破财伤病官非分手离职；冲克忌神→转机换运去旧迎新
- **共性**：无论吉凶，波动大、变数多、易有大事发生
- **化解**：原局有合/生/制则减凶；现实层面→稳守、少投资、不冒险、低调行事
- **经典出处**：《三命通会》"大运不宜与太岁相克相冲，尤忌运克岁"；古诀"反吟伏吟泪淋淋，不伤自己损他人"

## 用户命盘数据

"""


def build_chat_context(chart_data: dict) -> str:
    """从完整命盘 JSON 提取关键数据，生成 system prompt 上下文"""
    from ._chart_context import extract_base_context
    base = extract_base_context(chart_data)

    personality = chart_data.get("personality", {})
    family = chart_data.get("family", {})

    parts = []

    # 基本信息
    parts.append(f"【命主】{chart_data.get('name', '')}，{chart_data.get('gender', '')}")
    parts.append(f"【日主】{base['day_master']}")
    parts.append(f"【格局】{base['pattern']}")
    parts.append(f"【身强弱】{base['strength']}（{base['score']}分）")

    # 喜用
    if base["favorable"]:
        parts.append(f"【喜用十神】{'、'.join(base['favorable'])}")
    if base["harmful"]:
        parts.append(f"【忌神】{'、'.join(base['harmful'])}")

    # 大运
    parts.append(f"【大运方向】{base['dayun_direction']}，起运 {base['dayun_start_age']} 岁")
    if base["dayun_periods"]:
        parts.append("【大运列表】")
        for dp in base["dayun_periods"][:6]:
            parts.append(f"  {dp['order']}→{dp['age']}岁: {dp['stem']}{dp['branch']}")

    # 性格
    if base["personality_profile"]:
        parts.append(f"【性格画像】{base['personality_profile']}")
    if base["personality_traits"]:
        for k, v in base["personality_traits"].items():
            parts.append(f"  {k}: {v}")

    # 特殊组合
    if personality.get("special_combos"):
        combos_short = [c.split("→")[0].strip() for c in personality["special_combos"][:8]]
        parts.append(f"【关键组合】{'；'.join(combos_short)}")

    # 家境
    if base.get("family"):
        parts.append(f"【家境】等级{base['family']['level']}，{base['family']['father']}，{base['family']['mother']}")

    # 神煞
    if base["spirit_names"]:
        parts.append(f"【神煞】{'、'.join(base['spirit_names'])}")

    # 干支关系
    if base["key_interactions"]:
        parts.append(f"【地支关系】{'；'.join(base['key_interactions'][:5])}")

    return "\n".join(parts)


def build_messages(chart_data: dict, user_question: str,
                   history: list[dict] | None = None) -> list[dict]:
    """构建完整的 messages 数组"""
    context = build_chat_context(chart_data)
    system_prompt = SYSTEM_PROMPT_BASE + context

    # ── RAG 知识检索（v0.17.0）──
    try:
        from .rag import retrieve_for_chat, format_snippets
        rag_snippets = retrieve_for_chat(chart_data, user_question, top_k=4)
        if rag_snippets:
            rag_text = format_snippets(rag_snippets, max_chars=1200)
            system_prompt += "\n\n" + rag_text
    except Exception:
        pass  # RAG 静默降级

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        messages.extend(history[-20:])  # 最多保留最近20轮对话

    messages.append({"role": "user", "content": user_question})
    return messages


# ═══════════════════════════════════════════════════════════════
# 敏感词过滤
# ═══════════════════════════════════════════════════════════════

SENSITIVE_RULES = [
    # (正则, 类型, 拒绝回复)
    (r"自杀|不想活[了啦]?|结束生命|自残|割腕|跳楼|轻生|寻死|不想活|活不下去了",
     "自伤",
     "这类问题我无法回答。如果你正在经历困难，请拨打心理援助热线：**400-161-9995**（24小时）。你不需要独自面对。"),
    (r"怎么死|什么时候死|能活多久|还有多少[年岁]|寿命|阳寿|死期|大限",
     "死亡预测",
     "命理不能预测寿命。与其纠结时限，不如关注如何活得更有质量。如有健康疑虑，请就医检查。"),
    (r"得[了什么]?癌|癌症|肿瘤|绝症|白血病|会不?会死[于亡]",
     "疾病预测",
     "命理不能替代医学诊断。如有健康疑虑，请及时就医检查。"),
    (r"股票|炒股|涨停|跌停|A股|港股|美股|基金代码|币[圈种]|BTC|ETH|NFT",
     "投资建议",
     "本服务不提供投资建议。理财决策请咨询持牌专业人士。"),
    (r"彩票|双色球|大乐透|中奖|赌博|赌[场博钱]|梭哈|all\s*in|倍投|下注|博彩",
     "博彩",
     "不提供博彩相关内容。财富靠积累，不是靠运气。"),
    (r"违[法禁]|犯罪|毒品|洗钱|走私|诈骗|黑客|攻击网站|D[Dd]oS",
     "违法",
     "无法回答此类问题。"),
    (r"买.*[股币].*推荐|哪[只个].*[股币票]|推荐.*[股币票]",
     "投资推荐",
     "不推荐具体投资标的。"),
]


def filter_sensitive(text: str) -> tuple[bool, str]:
    """敏感词检测。返回 (通过?, 拒绝理由)"""
    for pattern, category, reply in SENSITIVE_RULES:
        if re.search(pattern, text):
            return False, reply
    return True, ""


# ═══════════════════════════════════════════════════════════════
# DeepSeek API 调用
# ═══════════════════════════════════════════════════════════════

DISCLAIMER_SUFFIX = "\n\n（以上内容由 AI 生成，基于传统命理文化，仅供娱乐参考，不替代专业建议）"


async def call_deepseek_stream(messages: list[dict]) -> AsyncGenerator[str, None]:
    """调用 DeepSeek API，流式返回"""
    if not DEEPSEEK_KEY:
        yield "data: [ERROR] DeepSeek API Key 未配置\n\n"
        return

    # Token 预算检查
    from ._token_budget import check_token_budget, truncate_messages
    if not check_token_budget(messages, DEEPSEEK_MODEL, 2048)[0]:
        messages = truncate_messages(messages, DEEPSEEK_MODEL, 2048)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", DEEPSEEK_API_URL,
                                     json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    yield f"data: [ERROR] DeepSeek API {resp.status_code}: {body.decode()[:200]}\n\n"
                    return

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'token': content})}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        # 追加免责后缀
        yield f"data: {json.dumps({'token': DISCLAIMER_SUFFIX})}\n\n"
        yield "data: [DONE]\n\n"

    except httpx.TimeoutException:
        yield "data: [ERROR] 请求超时，请稍后重试\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)[:200]}\n\n"


# ═══════════════════════════════════════════════════════════════
# 激活码管理
# ═══════════════════════════════════════════════════════════════

_default_codes = {
    "DEMO001": {"剩余": 3, "备注": "演示码"},
    "DEMO002": {"剩余": 10, "备注": "测试码"},
}


def _load_codes() -> dict:
    """加载激活码（环境变量 + 本地文件合并，环境变量优先）"""
    codes = dict(_default_codes)

    # 本地文件（首次自动创建，gitignore 保护）
    if _ACTIVATION_FILE.exists():
        try:
            with open(_ACTIVATION_FILE, "r", encoding="utf-8") as f:
                file_codes = json.load(f)
                codes.update(file_codes)
        except (json.JSONDecodeError, OSError):
            pass
    else:
        _save_codes(codes)

    # 环境变量注入（持久化，不受部署清空影响）
    env_codes = os.getenv("ACTIVATION_CODES", "")
    if env_codes:
        try:
            codes.update(json.loads(env_codes))
        except json.JSONDecodeError:
            pass

    return codes


def _save_codes(codes: dict) -> None:
    """保存激活码文件"""
    _ACTIVATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_ACTIVATION_FILE, "w", encoding="utf-8") as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)


def validate_code(code: str) -> tuple[bool, int, str]:
    """验证激活码。返回 (有效?, 剩余次数, 消息)"""
    codes = _load_codes()
    entry = codes.get(code.strip().upper())
    if not entry:
        return False, 0, "激活码无效"
    remaining = entry.get("剩余", 0)
    if remaining <= 0:
        return False, 0, "该激活码次数已用完"
    return True, remaining, "有效"


def consume_code(code: str) -> tuple[bool, int]:
    """消耗一次激活码。返回 (成功?, 剩余次数)"""
    codes = _load_codes()
    entry = codes.get(code.strip().upper())
    if not entry or entry.get("剩余", 0) <= 0:
        return False, 0
    entry["剩余"] -= 1
    _save_codes(codes)
    return True, entry["剩余"]


# 免激活每日免费额度
FREE_DAILY_LIMIT = 3
_FREE_USAGE_FILE = Path(__file__).resolve().parent.parent / "data" / "free_usage.json"


def _hash_ip(ip: str) -> str:
    """对 IP 做单向哈希，避免磁盘存储原始 IP"""
    import hashlib
    return hashlib.sha256(f"bazi-salt-{ip}".encode()).hexdigest()[:16]


def _load_free_usage() -> dict:
    """从文件加载免费使用记录"""
    if _FREE_USAGE_FILE.exists():
        try:
            with open(_FREE_USAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_free_usage(data: dict):
    """保存免费使用记录到文件"""
    _FREE_USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_FREE_USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def check_free_quota(client_id: str) -> tuple[bool, int]:
    """检查免激活免费额度。返回 (可用?, 剩余次数)。

    使用文件持久化存储，服务重启不丢失。
    IP 经哈希处理后存储，不保留原始 IP。
    注意: NAT/代理环境下多用户共用同一 IP，一个用户用完额度其他人也会被拦。
    """
    today = time.strftime("%Y-%m-%d")
    data = _load_free_usage()
    key = _hash_ip(client_id)

    # 清理过期条目
    stale = [k for k, v in data.items() if v.get("date") != today]
    for k in stale:
        del data[k]

    entry = data.get(key)
    if not entry or entry.get("date") != today:
        data[key] = {"date": today, "count": 0}
        _save_free_usage(data)
        return True, FREE_DAILY_LIMIT

    used = entry.get("count", 0)
    remaining = FREE_DAILY_LIMIT - used
    return remaining > 0, remaining


def consume_free_quota(client_id: str) -> int:
    """消耗一次免费额度。返回剩余次数"""
    today = time.strftime("%Y-%m-%d")
    data = _load_free_usage()
    key = _hash_ip(client_id)

    entry = data.get(key)
    if not entry or entry.get("date") != today:
        data[key] = {"date": today, "count": 1}
        _save_free_usage(data)
        return FREE_DAILY_LIMIT - 1

    entry["count"] = entry.get("count", 0) + 1
    data[key] = entry
    _save_free_usage(data)
    return FREE_DAILY_LIMIT - entry["count"]
