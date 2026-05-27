from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, Field

from orderops_api.core.config import get_settings
from orderops_api.tools.logging import ToolError, elapsed_ms, try_insert_tool_call_log
from orderops_api.tools.sql_guard import SqlGuardError, add_limit_if_missing


ToolStatus = Literal["success", "blocked", "error"]


class SqlAnalysisInput(BaseModel):
    sql: str = Field(min_length=1)
    limit: int = Field(default=100, ge=1, le=500)
    timeout_ms: int = Field(default=3000, ge=100, le=30000)
    trace_id: str | None = None


class SqlAnalysisOutput(BaseModel):
    status: ToolStatus
    guarded_sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error: ToolError | None = None


def jsonable_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def jsonable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: jsonable_value(value) for key, value in row.items()}


def run_sql_analysis(
    request: SqlAnalysisInput,
    database_url: str | None = None,
) -> SqlAnalysisOutput:
    settings = get_settings()
    database_url = database_url or settings.database_url
    started_at = perf_counter()

    try:
        guarded_sql = add_limit_if_missing(request.sql, request.limit)
    except SqlGuardError as exc:
        result = SqlAnalysisOutput(
            status="blocked",
            error=ToolError(code="SqlGuardError", message=str(exc)),
        )
        log_sql_result(database_url, request, result, started_at)
        return result

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(f"SET LOCAL statement_timeout = {int(request.timeout_ms)}")
                cursor.execute(guarded_sql)
                raw_rows = list(cursor.fetchall())
                rows = [jsonable_row(dict(row)) for row in raw_rows]
                columns = list(rows[0].keys()) if rows else [column.name for column in cursor.description]
            conn.rollback()

        result = SqlAnalysisOutput(
            status="success",
            guarded_sql=guarded_sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
        )
        log_sql_result(database_url, request, result, started_at)
        return result
    except Exception as exc:
        result = SqlAnalysisOutput(
            status="error",
            guarded_sql=guarded_sql,
            error=ToolError(code=exc.__class__.__name__, message=str(exc)),
        )
        log_sql_result(database_url, request, result, started_at)
        return result


def log_sql_result(
    database_url: str,
    request: SqlAnalysisInput,
    result: SqlAnalysisOutput,
    started_at: float,
) -> None:
    try_insert_tool_call_log(
        database_url,
        trace_id=request.trace_id,
        tool_name="sql_analysis",
        args=request,
        result=result,
        status=result.status,
        latency_ms=elapsed_ms(started_at),
        error_type=result.error.code if result.error else None,
    )
