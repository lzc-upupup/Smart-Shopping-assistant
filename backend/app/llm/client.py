import json
import re
from collections.abc import Sequence

from openai import OpenAI

from app.core.config import get_settings


Message = dict[str, str]


class LLMError(RuntimeError):
    pass


def is_llm_configured() -> bool:
    return get_settings().llm_enabled


def complete_text(
    messages: Sequence[Message],
    *,
    temperature: float | None = None,
    max_tokens: int = 900,
) -> str:
    settings = get_settings()
    if not settings.llm_enabled:
        raise LLMError("LLM is not configured.")

    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
    )
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=list(messages),
        temperature=settings.llm_temperature if temperature is None else temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    if not content:
        raise LLMError("LLM returned empty content.")
    return content.strip()


def complete_json(
    messages: Sequence[Message],
    *,
    temperature: float | None = None,
    max_tokens: int = 700,
) -> dict:
    settings = get_settings()
    if not settings.llm_enabled:
        raise LLMError("LLM is not configured.")

    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
    )
    request = {
        "model": settings.llm_model,
        "messages": list(messages),
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
    }

    try:
        if settings.llm_json_mode:
            response = client.chat.completions.create(
                **request,
                response_format={"type": "json_object"},
            )
        else:
            response = client.chat.completions.create(**request)
    except Exception:
        response = client.chat.completions.create(**request)

    content = response.choices[0].message.content
    if not content:
        raise LLMError("LLM returned empty JSON content.")
    return _parse_json_object(content)


def _parse_json_object(content: str) -> dict:
    cleaned = content.strip()
    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        object_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not object_match:
            raise LLMError("LLM did not return a JSON object.") from None
        parsed = json.loads(object_match.group(0))

    if not isinstance(parsed, dict):
        raise LLMError("LLM JSON response is not an object.")
    return parsed
