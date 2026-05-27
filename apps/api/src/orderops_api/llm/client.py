from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from typing import Any, Protocol
from urllib import request

from orderops_api.core.config import Settings


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_GLOBAL_BASE_URL = "https://api.siliconflow.com/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
CHAT_COMPLETIONS_PATH = "/chat/completions"

KNOWN_PROVIDER_BASE_URLS = {
    DEEPSEEK_BASE_URL,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_GLOBAL_BASE_URL,
    OPENAI_BASE_URL,
}
LEGACY_DEFAULT_MODELS = {"", "deepseek-v4-pro"}


@dataclass(frozen=True)
class LLMProviderPreset:
    provider: str
    default_base_url: str
    default_model: str
    default_api_path: str = CHAT_COMPLETIONS_PATH
    thinking_adapter: str = "none"
    allowed_base_urls: tuple[str, ...] = ()


PROVIDER_PRESETS: dict[str, LLMProviderPreset] = {
    "deepseek": LLMProviderPreset(
        provider="deepseek",
        default_base_url=DEEPSEEK_BASE_URL,
        default_model="deepseek-v4-pro",
        thinking_adapter="deepseek",
        allowed_base_urls=(DEEPSEEK_BASE_URL,),
    ),
    "siliconflow": LLMProviderPreset(
        provider="siliconflow",
        default_base_url=SILICONFLOW_BASE_URL,
        default_model="Qwen/Qwen3-32B",
        thinking_adapter="siliconflow",
        allowed_base_urls=(SILICONFLOW_BASE_URL, SILICONFLOW_GLOBAL_BASE_URL),
    ),
    "openai": LLMProviderPreset(
        provider="openai",
        default_base_url=OPENAI_BASE_URL,
        default_model="gpt-4.1-mini",
        thinking_adapter="none",
        allowed_base_urls=(OPENAI_BASE_URL,),
    ),
}


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
    provider: str
    base_url: str
    api_key: str
    model: str
    api_path: str = "/chat/completions"
    temperature: float = 0.0
    max_tokens: int = 1200
    timeout_seconds: int = 60
    thinking_enabled: bool = False
    reasoning_effort: str = "medium"
    thinking_adapter: str = "none"

    def chat_json(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        payload = self.build_payload(system_prompt, user_payload)

        response = post_json(
            f"{self.base_url.rstrip('/')}{self.api_path}",
            payload,
            bearer_token=self.api_key,
            timeout_seconds=self.timeout_seconds,
            extra_headers={"X-OrderOps-Trace-Id": trace_id or ""},
        )
        return extract_chat_json_content(response)

    def build_payload(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
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
        if self.thinking_adapter == "siliconflow":
            payload["enable_thinking"] = self.thinking_enabled
        elif self.thinking_enabled and self.thinking_adapter == "deepseek":
            payload["thinking"] = {"type": "enabled"}
            payload["reasoning_effort"] = self.reasoning_effort
        return payload


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
    config = resolve_provider_config(
        provider=provider,
        base_url=base_url,
        api_path=api_path,
        model=model,
    )
    if config["provider"] in {"", "none", "disabled", "off"} or not api_key:
        return DisabledLLMClient()
    if config["provider"] in {"deepseek", "siliconflow", "openai", "openai_compatible"}:
        return OpenAICompatibleLLMClient(
            provider=config["provider"],
            base_url=config["base_url"],
            api_key=api_key,
            api_path=config["api_path"],
            model=config["model"],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            thinking_enabled=thinking_enabled,
            reasoning_effort=reasoning_effort,
            thinking_adapter=config["thinking_adapter"],
        )
    raise ValueError(f"Unsupported LLM provider: {config['provider']}")


def resolve_provider_config(
    provider: str,
    base_url: str,
    api_path: str,
    model: str,
) -> dict[str, str]:
    normalized_provider = provider.strip().lower()
    normalized_base_url = base_url.strip().rstrip("/")
    normalized_api_path = api_path.strip() or CHAT_COMPLETIONS_PATH
    normalized_model = model.strip()

    if normalized_provider in {"", "none", "disabled", "off"}:
        return {
            "provider": normalized_provider,
            "base_url": normalized_base_url,
            "api_path": normalized_api_path,
            "model": normalized_model,
            "thinking_adapter": "none",
        }

    preset = PROVIDER_PRESETS.get(normalized_provider)
    if preset is None and normalized_provider != "openai_compatible":
        raise ValueError(f"Unsupported LLM provider: {normalized_provider}")

    if preset is None:
        if not normalized_base_url:
            raise ValueError("ORDEROPS_LLM_API_BASE_URL is required for openai_compatible providers.")
        return {
            "provider": normalized_provider,
            "base_url": normalized_base_url,
            "api_path": normalized_api_path,
            "model": normalized_model,
            "thinking_adapter": "none",
        }

    if not normalized_base_url:
        normalized_base_url = preset.default_base_url
    elif normalized_base_url in KNOWN_PROVIDER_BASE_URLS and normalized_base_url not in preset.allowed_base_urls:
        normalized_base_url = preset.default_base_url
    if normalized_model in LEGACY_DEFAULT_MODELS:
        normalized_model = preset.default_model
    if not normalized_api_path:
        normalized_api_path = preset.default_api_path

    return {
        "provider": normalized_provider,
        "base_url": normalized_base_url,
        "api_path": normalized_api_path,
        "model": normalized_model,
        "thinking_adapter": preset.thinking_adapter,
    }


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
