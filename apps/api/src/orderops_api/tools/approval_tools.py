from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from orderops_api.core.config import get_settings
from orderops_api.tools.logging import ToolError, elapsed_ms, insert_tool_call_log


ApprovalAction = Literal["approve", "reject"]
ToolStatus = Literal["success", "not_found", "conflict", "error"]


class DecideApprovalInput(BaseModel):
    approval_id: str = Field(min_length=1)
    action: ApprovalAction
    decided_by: str = Field(default="human_reviewer", min_length=1)
    decision_reason: str = Field(default="", max_length=1000)
    trace_id: str | None = None


class ApprovalDecisionOutput(BaseModel):
    status: ToolStatus
    approval_id: str
    ticket_id: str | None = None
    approval_status: str | None = None
    ticket_status: str | None = None
    decided_at: datetime | None = None
    error: ToolError | None = None


def now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def ticket_status_for_approval(action: ApprovalAction) -> str:
    return "open" if action == "approve" else "rejected"


def approval_status_for_action(action: ApprovalAction) -> str:
    return "approved" if action == "approve" else "rejected"


def build_decision_reason(existing_reason: str | None, request: DecideApprovalInput) -> str:
    base = existing_reason or "Manual approval decision."
    suffix = f" Decision by {request.decided_by}: {request.action}."
    if request.decision_reason:
        suffix += f" Reason: {request.decision_reason}"
    return f"{base}{suffix}"


def decide_approval(
    request: DecideApprovalInput,
    database_url: str | None = None,
) -> ApprovalDecisionOutput:
    settings = get_settings()
    database_url = database_url or settings.database_url
    started_at = perf_counter()

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT approval_id, ticket_id, status, reason
                    FROM approvals
                    WHERE approval_id = %(approval_id)s
                    FOR UPDATE
                    """,
                    {"approval_id": request.approval_id},
                )
                approval = cursor.fetchone()
                if approval is None:
                    result = ApprovalDecisionOutput(
                        status="not_found",
                        approval_id=request.approval_id,
                        error=ToolError(code="ApprovalNotFound", message="Approval was not found."),
                    )
                    insert_tool_call_log(
                        cursor,
                        trace_id=request.trace_id,
                        tool_name="decide_approval",
                        args=request,
                        result=result,
                        status=result.status,
                        latency_ms=elapsed_ms(started_at),
                        error_type=result.error.code,
                    )
                    conn.commit()
                    return result

                if approval["status"] != "pending":
                    result = ApprovalDecisionOutput(
                        status="conflict",
                        approval_id=request.approval_id,
                        ticket_id=approval["ticket_id"],
                        approval_status=approval["status"],
                        error=ToolError(
                            code="ApprovalAlreadyDecided",
                            message=f"Approval is already {approval['status']}.",
                        ),
                    )
                    insert_tool_call_log(
                        cursor,
                        trace_id=request.trace_id,
                        tool_name="decide_approval",
                        args=request,
                        result=result,
                        status=result.status,
                        latency_ms=elapsed_ms(started_at),
                        error_type=result.error.code,
                    )
                    conn.commit()
                    return result

                decided_at = now_utc_naive()
                approval_status = approval_status_for_action(request.action)
                ticket_status = ticket_status_for_approval(request.action)
                cursor.execute(
                    """
                    UPDATE approvals
                    SET status = %(status)s,
                        reason = %(reason)s,
                        decided_at = %(decided_at)s
                    WHERE approval_id = %(approval_id)s
                    """,
                    {
                        "approval_id": request.approval_id,
                        "status": approval_status,
                        "reason": build_decision_reason(approval["reason"], request),
                        "decided_at": decided_at,
                    },
                )
                cursor.execute(
                    """
                    UPDATE support_tickets
                    SET status = %(status)s
                    WHERE ticket_id = %(ticket_id)s
                    """,
                    {"ticket_id": approval["ticket_id"], "status": ticket_status},
                )
                result = ApprovalDecisionOutput(
                    status="success",
                    approval_id=request.approval_id,
                    ticket_id=approval["ticket_id"],
                    approval_status=approval_status,
                    ticket_status=ticket_status,
                    decided_at=decided_at,
                )
                insert_tool_call_log(
                    cursor,
                    trace_id=request.trace_id,
                    tool_name="decide_approval",
                    args=request,
                    result=result,
                    status=result.status,
                    latency_ms=elapsed_ms(started_at),
                )
            conn.commit()
        return result
    except Exception as exc:
        return ApprovalDecisionOutput(
            status="error",
            approval_id=request.approval_id,
            error=ToolError(code=exc.__class__.__name__, message=str(exc)),
        )
