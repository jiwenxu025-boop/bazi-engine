"""视觉 OCR — 从命盘截图/照片中提取出生信息

支持任意 OpenAI-compatible vision API（GPT-4o / Claude Vision / Qwen-VL 等）。

用法:
    from ._vision_ocr import ocr_birth_info
    info = ocr_birth_info(image_url="https://...")
    info = ocr_birth_info(image_base64="base64string...")
    # → {"name": "...", "gender": "男", "year": 2007, "month": 8, "day": 26, "hour": 20, "raw": "..."}

环境变量:
    VISION_API_URL   — 默认 https://api.openai.com/v1/chat/completions
    VISION_MODEL     — 默认 gpt-4o
    VISION_API_KEY   — API 密钥
"""
import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

from ._http import shared_client

VISION_API_URL = os.getenv("VISION_API_URL", "https://api.mimo.xiaomi.com/v1/chat/completions")
VISION_MODEL = os.getenv("VISION_MODEL", "mimo-v2.5")
VISION_KEY = os.getenv("VISION_API_KEY", "")

OCR_PROMPT = """你是一个 OCR 助手，从这张八字命盘截图中提取出生信息。

请严格按照以下 JSON 格式返回（只返回 JSON，不要其他文字）：
{
  "name": "姓名",
  "gender": "男或女",
  "year": 2000,
  "month": 1,
  "day": 1,
  "hour": 12,
  "raw": "图中所有可见的文字内容"
}

规则：
- 年份必须是 1900-2100 之间的整数
- 月份 1-12，日期 1-31
- 小时 0-23（24小时制）
- 性别只能是"男"或"女"
- raw 字段是图中全部可见文字，一字不差地抄下来
- 如果某个字段无法确定，填 null"""


def _encode_image(image_path: str | None = None, image_bytes: bytes | None = None) -> str:
    """将图片文件或字节转为 base64 data URL。"""
    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
    elif image_path:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")
        b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    else:
        raise ValueError("需要 image_path 或 image_bytes")

    # 推断 MIME 类型
    ext = Path(image_path).suffix.lower() if image_path else ".png"
    mime_map = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".webp": "webp", ".gif": "gif"}
    mime = mime_map.get(ext, "png")
    return f"data:image/{mime};base64,{b64}"


def ocr_birth_info(
    image_url: str | None = None,
    image_path: str | None = None,
    image_base64: str | None = None,
    image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """从命盘图片 OCR 提取出生信息。

    Args:
        image_url:   图片 URL
        image_path:  本地图片路径
        image_base64: base64 编码字符串（不含 data: 前缀）
        image_bytes:  图片字节数据

    Returns:
        {"name": str|None, "gender": str, "year": int, "month": int, "day": int, "hour": int, "raw": str}
    """
    if not VISION_KEY:
        raise RuntimeError("VISION_API_KEY 或 OPENAI_API_KEY 未设置")

    # 构建图片 URL/base64
    if image_url:
        img = {"type": "image_url", "image_url": {"url": image_url}}
    elif image_path or image_bytes:
        data_url = _encode_image(image_path=image_path, image_bytes=image_bytes)
        img = {"type": "image_url", "image_url": {"url": data_url}}
    elif image_base64:
        data_url = f"data:image/png;base64,{image_base64}"
        img = {"type": "image_url", "image_url": {"url": data_url}}
    else:
        raise ValueError("需要一个图片来源: image_url / image_path / image_base64 / image_bytes")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": OCR_PROMPT},
                img,
            ],
        }
    ]

    headers = {
        "Authorization": f"Bearer {VISION_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": VISION_MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.0,
    }

    try:
        with shared_client(60.0) as client:
            resp = client.post(VISION_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Vision API {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except httpx.TimeoutException as e:
        raise RuntimeError("Vision API 超时") from e
    except Exception as e:
        raise RuntimeError(f"Vision API 调用失败: {e}") from e

    if not content:
        raise RuntimeError("Vision API 返回空")

    # 提取 JSON
    json_match = re.search(r'\{[\s\S]*\}', content)
    if not json_match:
        return {"raw": content, "error": "无法解析 JSON"}

    try:
        info = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return {"raw": content, "error": "JSON 解析失败"}

    # 标准化
    result = {
        "name": info.get("name") or None,
        "gender": info.get("gender", ""),
        "year": info.get("year"),
        "month": info.get("month"),
        "day": info.get("day"),
        "hour": info.get("hour"),
        "raw": info.get("raw", content),
    }

    # 校验
    if result["gender"] not in ("男", "女"):
        result["gender"] = ""
    for key in ("year", "month", "day", "hour"):
        v = result[key]
        if v is not None and not isinstance(v, int):
            try:
                result[key] = int(v)
            except (TypeError, ValueError):
                result[key] = None

    return result
