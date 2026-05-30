# Bazi Engine — 共享 LLM API 配置
# 所有 LLM 模块（llm_review / chat / personality_fusion）统一从这里导入
import os

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
LLM_REVIEW_ENABLED = os.getenv("BAZI_LLM_REVIEW", "0") == "1"
FUSION_ENABLED = os.getenv("BAZI_FUSION_ENGINE", "0") == "1"

# 超时配置（v4-pro 超大型模型需要更长时间）
def get_timeout() -> float:
    return 90.0 if "v4" in DEEPSEEK_MODEL.lower() else 30.0


def is_available() -> bool:
    return bool(DEEPSEEK_KEY)
