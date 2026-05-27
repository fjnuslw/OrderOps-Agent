from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from typing import Any, Protocol
from urllib import request

from orderops_api.core.config import Settings


class LLMUnavailable(RuntimeError):
    pass


class LLMClient(Protocol):
    model: str

    def chat_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class DisabledLLMClient:
    model: str = "disabled"

    def chat_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        raise LLMUnavailable("LLM provider is disabled or missing an API key.")


@dataclass(frozen=True)
class OpenAICompatibleLLMClient:
    base_url: str
    api_key: str
    model: str
    api_path: str = "/chat/completions"
    temperature: float = 0.0
    max_tokens: int = 1200
    timeout_seconds: int = 60
    thinking_enabled: bool = False
    reasoning_effort: str = "medium"

    def chat_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        if self.thinking_enabled:
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = self.reasoning_effort

        response = post_json(
            f"{self.base_url.rstrip('/')}{self.api_path}",
            payload,
            bearer_token=self.api_key,
            timeout_seconds=self.timeout_seconds,
            extra_headers={"X-OrderOps-Trace-Id": trace_id or ""},
        )
        return extract_chat_json_content(response)


def build_llm_client(settings: Settings) -> LLMClient:
    return build_cached_llm_client(
        provider=settings.llm_provider,
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        api_path=settings.llm_api_path,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
        thinking_enabled=settings.llm_thinking_enabled,
        reasoning_effort=settings.llm_reasoning_effort,
    )


@lru_cache(maxsize=8)
def build_cached_llm_client(
    provider: str,
    base_url: str,
    api_key: str,
    api_path: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
    thinking_enabled: bool,
    reasoning_effort: str,
) -> LLMClient:
    provider = provider.strip().lower()
    if provider in {"", "none", "disabled", "off"} or not api_key:
        return DisabledLLMClient()
    if provider in {"deepseek", "openai_compatible"}:
        return OpenAICompatibleLLMClient(
            base_url=base_url,
            api_key=api_key,
            api_path=api_path,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            thinking_enabled=thinking_enabled,
            reasoning_effort=reasoning_effort,
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


def extract_chat_json_content(response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Chat API response must include choices[0].message.content") from exc
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise ValueError("Chat API content must be a JSON string or object.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Chat API content was not valid JSON.") from exc


def post_json(
    url: str,
    payload: dict[str, Any],
    bearer_token: str,
    timeout_seconds: int,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {bearer_token}"}
    if extra_headers:
        headers.update({key: value for key, value in extra_headers.items() if value})
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    with request.urlopen(req, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)
