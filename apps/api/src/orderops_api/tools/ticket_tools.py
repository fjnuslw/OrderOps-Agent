from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from orderops_api.core.config import get_settings
from orderops_api.tools.logging import (
    ToolError,
    elapsed_ms,
    insert_tool_call_log,
    try_insert_tool_call_log,
)
from orderops_api.tools.order_tools import GetOrderSummaryInput, get_order_summary


Priority = Literal["low", "medium", "high"]
RiskLevel = Literal["low", "medium", "high"]
ToolStatus = Literal["success", "not_found", "error"]


class CreateSupportTicketDraftInput(BaseModel):
    order_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    expected_action: str = Field(min_length=1)
    priority: Priority = "medium"
    risk_level: RiskLevel = "medium"
    requested_by: str = "agent"
    policy_refs: list[str] = Field(default_factory=list)
    trace_id: str | None = None


class CreateSupportTicketDraftOutput(BaseModel):
    status: ToolStatus
    order_id: str
    ticket_id: str | None = None
    approval_id: str | None = None
    approval_required: bool = True
    approval_status: Literal["pending", "not_created"] = "not_created"
    ticket_status: str | None = None
    error: ToolError | None = None


def make_draft_ticket_id(scenario: str, order_id: str) -> str:
    digest = sha1(f"draft:{scenario}:{order_id}".encode("utf-8")).hexdigest()[:12]
    return f"DRAFT-{digest.upper()}"


def make_approval_id(ticket_id: str) -> str:
    digest = sha1(f"approval:{ticket_id}".encode("utf-8")).hexdigest()[:12]
    return f"APR-{digest.upper()}"


def ticket_created_at() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def approval_reason(request: CreateSupportTicketDraftInput) -> str:
    if not request.policy_refs:
        return "Draft support ticket requires manual approval."
    refs = ", ".join(request.policy_refs)
    return f"Draft support ticket requires manual approval. Policy refs: {refs}."


def create_support_ticket_draft(
    request: CreateSupportTicketDraftInput,
    database_url: str | None = None,
) -> CreateSupportTicketDraftOutput:
    settings = get_settings()
    database_url = database_url or settings.database_url
    started_at = perf_counter()

    order_summary = get_order_summary(
        GetOrderSummaryInput(order_id=request.order_id, trace_id=request.trace_id),
        database_url=database_url,
    )
    if order_summary.status in {"not_found", "error"}:
        result = CreateSupportTicketDraftOutput(
            status=order_summary.status,
            order_id=request.order_id,
            error=order_summary.error,
        )
        try_insert_tool_call_log(
            database_url,
            trace_id=request.trace_id,
            tool_name="create_support_ticket_draft",
            args=request,
            result=result,
            status=result.status,
            latency_ms=elapsed_ms(started_at),
            error_type=result.error.code if result.error else None,
        )
        return result

    ticket_id = make_draft_ticket_id(request.scenario, request.order_id)
    approval_id = make_approval_id(ticket_id)
    created_at = ticket_created_at()
    seller_id = order_summary.seller_ids[0] if order_summary.seller_ids else None

    try:
        import psycopg

        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO support_tickets (
                        ticket_id,
                        order_id,
                        customer_id,
                        seller_id,
                        scenario,
                        priority,
                        status,
                        created_at,
                        title,
                        description,
                        expected_action,
                        risk_level
                    )
                    VALUES (
                        %(ticket_id)s,
                        %(order_id)s,
                        %(customer_id)s,
                        %(seller_id)s,
                        %(scenario)s,
                        %(priority)s,
                        %(status)s,
                        %(created_at)s,
                        %(title)s,
                        %(description)s,
                        %(expected_action)s,
                        %(risk_level)s
                    )
                    ON CONFLICT (ticket_id) DO UPDATE SET
                        customer_id = EXCLUDED.customer_id,
                        seller_id = EXCLUDED.seller_id,
                        priority = EXCLUDED.priority,
                        status = EXCLUDED.status,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        expected_action = EXCLUDED.expected_action,
                        risk_level = EXCLUDED.risk_level
                    """,
                    {
                        "ticket_id": ticket_id,
                        "order_id": request.order_id,
                        "customer_id": order_summary.customer_id,
                        "seller_id": seller_id,
                        "scenario": request.scenario,
                        "priority": request.priority,
                        "status": "draft_pending_approval",
                        "created_at": created_at,
                        "title": request.title,
                        "description": request.description,
                        "expected_action": request.expected_action,
                        "risk_level": request.risk_level,
                    },
                )
                cursor.execute(
                    """
                    INSERT INTO approvals (
                        approval_id,
                        ticket_id,
                        requested_by,
                        status,
                        reason,
                        created_at,
                        decided_at
                    )
                    VALUES (
                        %(approval_id)s,
                        %(ticket_id)s,
                        %(requested_by)s,
                        %(status)s,
                        %(reason)s,
                        %(created_at)s,
                        NULL
                    )
                    ON CONFLICT (approval_id) DO UPDATE SET
                        requested_by = EXCLUDED.requested_by,
                        status = EXCLUDED.status,
                        reason = EXCLUDED.reason,
                        decided_at = NULL
                    """,
                    {
                        "approval_id": approval_id,
                        "ticket_id": ticket_id,
                        "requested_by": request.requested_by,
                        "status": "pending",
                        "reason": approval_reason(request),
                        "created_at": created_at,
                    },
                )
                result = CreateSupportTicketDraftOutput(
                    status="success",
                    order_id=request.order_id,
                    ticket_id=ticket_id,
                    approval_id=approval_id,
                    approval_status="pending",
                    ticket_status="draft_pending_approval",
                )
                insert_tool_call_log(
                    cursor,
                    trace_id=request.trace_id,
                    tool_name="create_support_ticket_draft",
                    args=request,
                    result=result,
                    status=result.status,
                    latency_ms=elapsed_ms(started_at),
                )
            conn.commit()
        return result
    except Exception as exc:
        result = CreateSupportTicketDraftOutput(
            status="error",
            order_id=request.order_id,
            error=ToolError(code=exc.__class__.__name__, message=str(exc)),
        )
        try_insert_tool_call_log(
            database_url,
            trace_id=request.trace_id,
            tool_name="create_support_ticket_draft",
            args=request,
            result=result,
            status=result.status,
            latency_ms=elapsed_ms(started_at),
            error_type=exc.__class__.__name__,
        )
        return result
