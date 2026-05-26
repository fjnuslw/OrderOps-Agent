from functools import lru_cache
import os
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    environment: str = "local"
    app_name: str = "OrderOps Agent API"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_reload: bool = True
    database_url: str = "postgresql://orderops:orderops@localhost:15432/orderops"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "orderops_policies"
    embedding_provider: str = "hashing"
    embedding_model: str = "hashing-token-v1"
    embedding_dimension: int = 384
    embedding_api_base_url: str = ""
    embedding_api_key: str = ""
    embedding_api_path: str = "/v1/embeddings"
    embedding_query_prefix: str = ""
    embedding_document_prefix: str = ""
    rerank_provider: str = "lexical"
    rerank_model: str = "lexical-token-overlap-v1"
    rerank_api_base_url: str = ""
    rerank_api_key: str = ""
    rerank_api_path: str = "/rerank"


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def settings_from_env(env: Mapping[str, str]) -> Settings:
    return Settings(
        environment=env.get("ORDEROPS_ENV", "local"),
        app_name=env.get("ORDEROPS_APP_NAME", "OrderOps Agent API"),
        api_host=env.get("ORDEROPS_API_HOST", "127.0.0.1"),
        api_port=int(env.get("ORDEROPS_API_PORT", "8000")),
        api_reload=_env_bool(env.get("ORDEROPS_API_RELOAD"), True),
        database_url=env.get(
            "ORDEROPS_DATABASE_URL",
            "postgresql://orderops:orderops@localhost:15432/orderops",
        ),
        redis_url=env.get("ORDEROPS_REDIS_URL", "redis://localhost:6379/0"),
        qdrant_url=env.get("ORDEROPS_QDRANT_URL", "http://localhost:6333"),
        qdrant_collection=env.get(
            "ORDEROPS_QDRANT_COLLECTION",
            "orderops_policies",
        ),
        embedding_provider=env.get("ORDEROPS_EMBEDDING_PROVIDER", "hashing"),
        embedding_model=env.get("ORDEROPS_EMBEDDING_MODEL", "hashing-token-v1"),
        embedding_dimension=int(env.get("ORDEROPS_EMBEDDING_DIMENSION", "384")),
        embedding_api_base_url=env.get("ORDEROPS_EMBEDDING_API_BASE_URL", ""),
        embedding_api_key=env.get("ORDEROPS_EMBEDDING_API_KEY", ""),
        embedding_api_path=env.get("ORDEROPS_EMBEDDING_API_PATH", "/v1/embeddings"),
        embedding_query_prefix=env.get("ORDEROPS_EMBEDDING_QUERY_PREFIX", ""),
        embedding_document_prefix=env.get("ORDEROPS_EMBEDDING_DOCUMENT_PREFIX", ""),
        rerank_provider=env.get("ORDEROPS_RERANK_PROVIDER", "lexical"),
        rerank_model=env.get("ORDEROPS_RERANK_MODEL", "lexical-token-overlap-v1"),
        rerank_api_base_url=env.get("ORDEROPS_RERANK_API_BASE_URL", ""),
        rerank_api_key=env.get("ORDEROPS_RERANK_API_KEY", ""),
        rerank_api_path=env.get("ORDEROPS_RERANK_API_PATH", "/rerank"),
    )


@lru_cache
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return settings_from_env(os.environ)
