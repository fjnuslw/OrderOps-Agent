from orderops_api.core.config import settings_from_env
from orderops_api.llm.client import (
    DisabledLLMClient,
    OpenAICompatibleLLMClient,
    build_llm_client,
    extract_chat_json_content,
    resolve_provider_config,
)


def test_llm_client_is_disabled_without_api_key() -> None:
    client = build_llm_client(settings_from_env({"ORDEROPS_LLM_PROVIDER": "deepseek"}))

    assert isinstance(client, DisabledLLMClient)


def test_deepseek_client_uses_openai_compatible_settings() -> None:
    client = build_llm_client(
        settings_from_env(
            {
                "ORDEROPS_LLM_PROVIDER": "deepseek",
                "ORDEROPS_LLM_API_KEY": "secret",
                "ORDEROPS_LLM_MODEL": "deepseek-v4-pro",
                "ORDEROPS_LLM_THINKING_ENABLED": "1",
            }
        )
    )

    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client.base_url == "https://api.deepseek.com"
    assert client.model == "deepseek-v4-pro"
    assert client.provider == "deepseek"
    assert client.thinking_adapter == "deepseek"
    assert client.thinking_enabled


def test_siliconflow_client_uses_provider_preset_with_only_provider_key_and_model() -> None:
    client = build_llm_client(
        settings_from_env(
            {
                "ORDEROPS_LLM_PROVIDER": "siliconflow",
                "ORDEROPS_LLM_API_KEY": "secret",
                "ORDEROPS_LLM_MODEL": "Qwen/Qwen2.5-72B-Instruct",
            }
        )
    )

    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client.base_url == "https://api.siliconflow.com/v1"
    assert client.model == "Qwen/Qwen2.5-72B-Instruct"
    assert client.provider == "siliconflow"
    assert client.thinking_adapter == "siliconflow"


def test_siliconflow_preset_overrides_leftover_deepseek_default_url_and_model() -> None:
    client = build_llm_client(
        settings_from_env(
            {
                "ORDEROPS_LLM_PROVIDER": "siliconflow",
                "ORDEROPS_LLM_API_BASE_URL": "https://api.deepseek.com",
                "ORDEROPS_LLM_API_KEY": "secret",
                "ORDEROPS_LLM_MODEL": "deepseek-v4-pro",
            }
        )
    )

    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client.base_url == "https://api.siliconflow.com/v1"
    assert client.model == "Qwen/Qwen3-32B"


def test_siliconflow_payload_uses_enable_thinking_flag() -> None:
    client = build_llm_client(
        settings_from_env(
            {
                "ORDEROPS_LLM_PROVIDER": "siliconflow",
                "ORDEROPS_LLM_API_KEY": "secret",
                "ORDEROPS_LLM_THINKING_ENABLED": "0",
            }
        )
    )

    assert isinstance(client, OpenAICompatibleLLMClient)
    payload = client.build_payload("system", {"message": "hello"})
    assert payload["enable_thinking"] is False
    assert "thinking" not in payload


def test_openai_compatible_requires_explicit_base_url() -> None:
    try:
        resolve_provider_config(
            provider="openai_compatible",
            base_url="",
            api_path="/chat/completions",
            model="custom-model",
        )
    except ValueError as exc:
        assert "ORDEROPS_LLM_API_BASE_URL" in str(exc)
    else:
        raise AssertionError("Expected missing base URL to fail.")


def test_extract_chat_json_content_parses_json_string() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": '{"intent": "policy_qa", "answer": "ok"}',
                }
            }
        ]
    }

    assert extract_chat_json_content(payload) == {"intent": "policy_qa", "answer": "ok"}
