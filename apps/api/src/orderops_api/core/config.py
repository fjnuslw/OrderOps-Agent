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
    database_url: str = "postgresql://orderops:orderops@localhost:5432/orderops"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "orderops_policies"


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
            "postgresql://orderops:orderops@localhost:5432/orderops",
        ),
        redis_url=env.get("ORDEROPS_REDIS_URL", "redis://localhost:6379/0"),
        qdrant_url=env.get("ORDEROPS_QDRANT_URL", "http://localhost:6333"),
        qdrant_collection=env.get(
            "ORDEROPS_QDRANT_COLLECTION",
            "orderops_policies",
        ),
    )


@lru_cache
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return settings_from_env(os.environ)
