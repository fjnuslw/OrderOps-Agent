from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Callable
from urllib import request
from urllib.error import URLError

from orderops_api.core.config import get_settings
from orderops_api.main import app
from orderops_api.rag.policies import load_policy_chunks


@dataclass(frozen=True)
class CheckResult:
    phase: str
    name: str
    status: str
    detail: str


def ok(phase: str, name: str, detail: str) -> CheckResult:
    return CheckResult(phase=phase, name=name, status="pass", detail=detail)


def fail(phase: str, name: str, detail: str) -> CheckResult:
    return CheckResult(phase=phase, name=name, status="fail", detail=detail)


def warn(phase: str, name: str, detail: str) -> CheckResult:
    return CheckResult(phase=phase, name=name, status="warn", detail=detail)


def check_required_paths() -> list[CheckResult]:
    phase = "Phase 0"
    required_paths = [
        "README.md",
        ".gitignore",
        ".env.example",
        "docs/BUILD_PLAN.md",
        "docs/PHASE_STATUS.md",
        "apps/api/pyproject.toml",
    ]
    missing = [path for path in required_paths if not Path(path).exists()]
    if missing:
        return [fail(phase, "repository_baseline", f"Missing: {', '.join(missing)}")]
    return [ok(phase, "repository_baseline", "Core repository files are present.")]


def check_fastapi_routes() -> list[CheckResult]:
    phase = "Phase 1"
    routes = {route.path for route in app.routes}
    required_routes = {
        "/health",
        "/api/tools/order-summary",
        "/api/tools/policy-search",
        "/api/tools/delivery-compensation",
        "/api/tools/refund-eligibility",
        "/api/tools/support-ticket-draft",
        "/api/tools/approval-decision",
        "/api/tools/sql-analysis",
        "/api/tools/seller-quality",
    }
    missing = sorted(required_routes.difference(routes))
    if missing:
        return [fail(phase, "fastapi_routes", f"Missing routes: {', '.join(missing)}")]
    return [ok(phase, "fastapi_routes", f"{len(required_routes)} required routes registered.")]


def check_local_infra() -> list[CheckResult]:
    phase = "Phase 2"
    settings = get_settings()
    results: list[CheckResult] = []

    try:
        with request.urlopen(f"{settings.qdrant_url}/readyz", timeout=5) as response:
            body = response.read().decode("utf-8")
        if "ready" in body.lower():
            results.append(ok(phase, "qdrant_ready", body.strip()))
        else:
            results.append(warn(phase, "qdrant_ready", body.strip()))
    except URLError as exc:
        results.append(fail(phase, "qdrant_ready", str(exc)))

    try:
        import psycopg

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        results.append(ok(phase, "postgres_ready", "PostgreSQL connection succeeded."))
    except Exception as exc:
        results.append(fail(phase, "postgres_ready", str(exc)))

    return results


def check_database_counts() -> list[CheckResult]:
    phase = "Phase 3"
    settings = get_settings()
    required_tables = {
        "orders": 1,
        "order_items": 1,
        "payments": 1,
        "reviews": 1,
        "products": 1,
        "sellers": 1,
        "customers": 1,
    }
    try:
        import psycopg

        counts: dict[str, int] = {}
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                for table_name in required_tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    counts[table_name] = int(cursor.fetchone()[0])
        low_tables = [
            table_name
            for table_name, minimum in required_tables.items()
            if counts.get(table_name, 0) < minimum
        ]
        if low_tables:
            return [fail(phase, "olist_tables", f"Empty tables: {', '.join(low_tables)}")]
        detail = ", ".join(f"{table}={count}" for table, count in sorted(counts.items()))
        return [ok(phase, "olist_tables", detail)]
    except Exception as exc:
        return [fail(phase, "olist_tables", str(exc))]


def check_support_tickets() -> list[CheckResult]:
    phase = "Phase 4"
    settings = get_settings()
    try:
        import psycopg

        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT scenario, COUNT(*)
                    FROM support_tickets
                    GROUP BY scenario
                    ORDER BY scenario
                    """
                )
                counts = {scenario: int(count) for scenario, count in cursor.fetchall()}
        required = {"delivery_delay", "low_review", "canceled_order", "high_value_order"}
        missing = sorted(required.difference(counts))
        if missing:
            return [fail(phase, "support_tickets", f"Missing scenarios: {', '.join(missing)}")]
        detail = ", ".join(f"{scenario}={count}" for scenario, count in counts.items())
        return [ok(phase, "support_tickets", detail)]
    except Exception as exc:
        return [fail(phase, "support_tickets", str(exc))]


def check_policy_rag() -> list[CheckResult]:
    phase = "Phase 5"
    settings = get_settings()
    results: list[CheckResult] = []

    chunks = load_policy_chunks(Path("data/policies"))
    if len(chunks) >= 20:
        results.append(ok(phase, "policy_chunks", f"{len(chunks)} policy chunks loaded."))
    else:
        results.append(warn(phase, "policy_chunks", f"Only {len(chunks)} policy chunks loaded."))

    try:
        url = f"{settings.qdrant_url}/collections/{settings.qdrant_collection}"
        with request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = payload["result"]
        points_count = int(result["points_count"])
        vector_size = int(result["config"]["params"]["vectors"]["size"])
        if points_count >= len(chunks) and vector_size == settings.embedding_dimension:
            results.append(
                ok(
                    phase,
                    "qdrant_policy_index",
                    f"points={points_count}, vector_size={vector_size}",
                )
            )
        else:
            results.append(
                fail(
                    phase,
                    "qdrant_policy_index",
                    f"points={points_count}, vector_size={vector_size}, expected_dim={settings.embedding_dimension}",
                )
            )
    except Exception as exc:
        results.append(fail(phase, "qdrant_policy_index", str(exc)))

    return results


def check_business_tools() -> list[CheckResult]:
    phase = "Phase 6"
    settings = get_settings()
    try:
        import psycopg

        required_tool_logs = {
            "get_order_summary",
            "search_policy",
            "check_delivery_compensation",
            "check_refund_eligibility",
            "create_support_ticket_draft",
            "decide_approval",
            "sql_analysis",
            "seller_quality_analysis",
        }
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT tool_name FROM tool_call_logs")
                seen = {row[0] for row in cursor.fetchall()}
        missing = sorted(required_tool_logs.difference(seen))
        if missing:
            return [warn(phase, "tool_call_logs", f"No local log yet for: {', '.join(missing)}")]
        return [ok(phase, "tool_call_logs", f"{len(required_tool_logs)} tool families logged.")]
    except Exception as exc:
        return [fail(phase, "tool_call_logs", str(exc))]


def run_checks() -> list[CheckResult]:
    checks: list[Callable[[], list[CheckResult]]] = [
        check_required_paths,
        check_fastapi_routes,
        check_local_infra,
        check_database_counts,
        check_support_tickets,
        check_policy_rag,
        check_business_tools,
    ]
    results: list[CheckResult] = []
    for check in checks:
        results.extend(check())
    return results


def print_markdown(results: list[CheckResult]) -> None:
    print("# Phase Smoke Check")
    print()
    for result in results:
        icon = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[result.status]
        print(f"- {icon} {result.phase} / {result.name}: {result.detail}")


def print_json(results: list[CheckResult]) -> None:
    payload = [result.__dict__ for result in results]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = ArgumentParser(description="Run smoke checks for completed OrderOps phases.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    results = run_checks()
    if args.json:
        print_json(results)
    else:
        print_markdown(results)

    if any(result.status == "fail" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
