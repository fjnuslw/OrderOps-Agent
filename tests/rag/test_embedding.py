from orderops_api.core.config import settings_from_env
from orderops_api.rag.embedding import (
    HashingEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
    extract_openai_embedding,
    tokenize_for_embedding,
)


def test_tokenizer_keeps_latin_tokens_and_chinese_bigrams() -> None:
    tokens = tokenize_for_embedding("延迟送达如何补偿 order_id")

    assert "order_id" in tokens
    assert "延" in tokens
    assert "延迟" in tokens
    assert "送达" in tokens


def test_hashing_embedding_is_deterministic_and_normalized() -> None:
    provider = HashingEmbeddingProvider(dimension=32)

    first = provider.embed("延迟送达如何补偿")
    second = provider.embed("延迟送达如何补偿")

    assert first == second
    assert len(first) == 32
    assert sum(value * value for value in first) == 1.0


def test_hashing_embedding_supports_query_and_document_inputs() -> None:
    provider = HashingEmbeddingProvider(dimension=32)

    assert provider.embed_text("延迟送达", input_type="query") == provider.embed_text(
        "延迟送达",
        input_type="document",
    )


def test_default_embedding_provider_factory_uses_hashing() -> None:
    provider = build_embedding_provider(settings_from_env({}))

    assert isinstance(provider, HashingEmbeddingProvider)
    assert provider.dimension == 384


def test_openai_compatible_embedding_provider_factory() -> None:
    settings = settings_from_env(
        {
            "ORDEROPS_EMBEDDING_PROVIDER": "openai_compatible",
            "ORDEROPS_EMBEDDING_MODEL": "text-embedding-3-small",
            "ORDEROPS_EMBEDDING_DIMENSION": "1536",
            "ORDEROPS_EMBEDDING_API_BASE_URL": "https://api.example.test",
            "ORDEROPS_EMBEDDING_API_KEY": "secret",
        }
    )

    provider = build_embedding_provider(settings)

    assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
    assert provider.dimension == 1536


def test_extract_openai_embedding_response() -> None:
    embedding = extract_openai_embedding({"data": [{"embedding": [1, "2.5", 3]}]})

    assert embedding == [1.0, 2.5, 3.0]
