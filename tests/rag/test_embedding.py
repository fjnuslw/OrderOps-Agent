from orderops_api.rag.embedding import HashingEmbeddingProvider, tokenize_for_embedding


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
