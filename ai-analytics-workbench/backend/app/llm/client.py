"""LLM 客户端：封装 OpenAI 兼容接口调用。"""

import json
from typing import Any

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


def _build_client() -> OpenAI:
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def chat_completion(system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
    """调用 LLM 并返回文本内容。

    支持任意 OpenAI 兼容接口（OpenAI / DeepSeek / 通义千问等）。
    """
    client = _build_client()
    resp = client.chat.completions.create(
        model=kwargs.get("model", settings.LLM_MODEL),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=kwargs.get("temperature", 0.2),
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


def parse_json_response(content: str) -> dict:
    """安全解析 LLM 返回的 JSON。"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 兜底：提取首个 JSON 对象
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        raise
