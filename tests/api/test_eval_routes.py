from fastapi.testclient import TestClient
import pytest

from orderops_api.core.config import get_settings
from orderops_api.llm.client import build_cached_llm_client
from orderops_api.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_real_llm(monkeypatch) -> None:
    monkeypatch.setenv("ORDEROPS_LLM_PROVIDER", "disabled")
    monkeypatch.delenv("ORDEROPS_LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    build_cached_llm_client.cache_clear()


def test_eval_run_route_executes_seed_case_without_live_llm_or_writes() -> None:
    response = client.post(
        "/api/evals/run",
        json={"case_ids": ["EVAL-008"], "write_reports": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["live_llm"] is False
    assert payload["allow_writes"] is False
    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["task_success_rate"] == 1.0
    assert payload["cases"][0]["actual_tools"] == []


def test_eval_run_route_rejects_unknown_case_id() -> None:
    response = client.post(
        "/api/evals/run",
        json={"case_ids": ["EVAL-DOES-NOT-EXIST"], "write_reports": False},
    )

    assert response.status_code == 400
    assert "Unknown eval case" in response.json()["detail"]
