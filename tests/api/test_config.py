from orderops_api.core.config import settings_from_env


def test_settings_use_local_defaults() -> None:
    settings = settings_from_env({})

    assert settings.environment == "local"
    assert settings.app_name == "OrderOps Agent API"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.api_reload is True
    assert settings.database_url == "postgresql://orderops:orderops@localhost:15432/orderops"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection == "orderops_policies"
    assert settings.embedding_provider == "hashing"
    assert settings.embedding_model == "hashing-token-v1"
    assert settings.embedding_dimension == 384
    assert settings.rerank_provider == "lexical"
    assert settings.rerank_model == "lexical-token-overlap-v1"


def test_settings_can_be_overridden_by_environment_values() -> None:
    settings = settings_from_env(
        {
            "ORDEROPS_ENV": "test",
            "ORDEROPS_APP_NAME": "Test API",
            "ORDEROPS_API_HOST": "0.0.0.0",
            "ORDEROPS_API_PORT": "9000",
            "ORDEROPS_API_RELOAD": "0",
            "ORDEROPS_DATABASE_URL": "postgresql://user:pass@db:5432/app",
            "ORDEROPS_REDIS_URL": "redis://redis:6379/1",
            "ORDEROPS_QDRANT_URL": "http://qdrant:6333",
            "ORDEROPS_QDRANT_COLLECTION": "test_collection",
            "ORDEROPS_EMBEDDING_PROVIDER": "openai_compatible",
            "ORDEROPS_EMBEDDING_MODEL": "text-embedding-3-small",
            "ORDEROPS_EMBEDDING_DIMENSION": "1536",
            "ORDEROPS_EMBEDDING_API_BASE_URL": "https://api.example.test",
            "ORDEROPS_EMBEDDING_API_KEY": "secret",
            "ORDEROPS_EMBEDDING_QUERY_PREFIX": "query: ",
            "ORDEROPS_EMBEDDING_DOCUMENT_PREFIX": "passage: ",
            "ORDEROPS_RERANK_PROVIDER": "http",
            "ORDEROPS_RERANK_MODEL": "bge-reranker",
            "ORDEROPS_RERANK_API_BASE_URL": "https://rerank.example.test",
        }
    )

    assert settings.environment == "test"
    assert settings.app_name == "Test API"
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 9000
    assert settings.api_reload is False
    assert settings.database_url == "postgresql://user:pass@db:5432/app"
    assert settings.redis_url == "redis://redis:6379/1"
    assert settings.qdrant_url == "http://qdrant:6333"
    assert settings.qdrant_collection == "test_collection"
    assert settings.embedding_provider == "openai_compatible"
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.embedding_dimension == 1536
    assert settings.embedding_api_base_url == "https://api.example.test"
    assert settings.embedding_api_key == "secret"
    assert settings.embedding_query_prefix == "query: "
    assert settings.embedding_document_prefix == "passage: "
    assert settings.rerank_provider == "http"
    assert settings.rerank_model == "bge-reranker"
    assert settings.rerank_api_base_url == "https://rerank.example.test"
