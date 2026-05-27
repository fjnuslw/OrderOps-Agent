from orderops_api.core.config import settings_from_env
from orderops_api.llm.client import (
    DisabledLLMClient,
    OpenAICompatibleLLMClient,
    build_llm_client,
    extract_chat_json_content,
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
    assert client.thinking_enabled


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
