from orderops_api.core.config import settings_from_env


def test_settings_use_local_defaults() -> None:
    settings = settings_from_env({})

    assert settings.environment == "local"
    assert settings.app_name == "OrderOps Agent API"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.api_reload is True
    assert settings.database_url == "postgresql://orderops:orderops@localhost:5432/orderops"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection == "orderops_policies"


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
