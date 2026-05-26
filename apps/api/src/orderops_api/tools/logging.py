from __future__ import annotations

from time import perf_counter
from typing import Any, Protocol

from pydantic import BaseModel


class ToolError(BaseModel):
    code: str
    message: str


class ToolResult(Protocol):
    status: str

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        ...


def elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


def dump_jsonable(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def insert_tool_call_log(
    cursor,
    *,
    trace_id: str | None,
    tool_name: str,
    args: BaseModel | dict[str, Any],
    result: BaseModel | dict[str, Any],
    status: str,
    latency_ms: int,
    error_type: str | None = None,
) -> None:
    from psycopg.types.json import Jsonb

    cursor.execute(
        """
        INSERT INTO tool_call_logs (
            trace_id,
            tool_name,
            args_json,
            result_json,
            status,
            latency_ms,
            error_type
        )
        VALUES (
            %(trace_id)s,
            %(tool_name)s,
            %(args_json)s,
            %(result_json)s,
            %(status)s,
            %(latency_ms)s,
            %(error_type)s
        )
        """,
        {
            "trace_id": trace_id,
            "tool_name": tool_name,
            "args_json": Jsonb(dump_jsonable(args)),
            "result_json": Jsonb(dump_jsonable(result)),
            "status": status,
            "latency_ms": latency_ms,
            "error_type": error_type,
        },
    )


def try_insert_tool_call_log(
    database_url: str,
    *,
    trace_id: str | None,
    tool_name: str,
    args: BaseModel | dict[str, Any],
    result: BaseModel | dict[str, Any],
    status: str,
    latency_ms: int,
    error_type: str | None = None,
) -> None:
    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                insert_tool_call_log(
                    cursor,
                    trace_id=trace_id,
                    tool_name=tool_name,
                    args=args,
                    result=result,
                    status=status,
                    latency_ms=latency_ms,
                    error_type=error_type,
                )
            conn.commit()
    except Exception:
        return
