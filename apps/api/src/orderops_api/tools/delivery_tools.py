from __future__ import annotations

from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from orderops_api.core.config import get_settings
from orderops_api.tools.logging import ToolError, elapsed_ms, try_insert_tool_call_log
from orderops_api.tools.order_tools import GetOrderSummaryInput, OrderSummaryOutput, get_order_summary
from orderops_api.tools.policy_tools import PolicySearchInput, search_policy_tool


DeliveryDecision = Literal[
    "eligible_with_manual_approval",
    "not_eligible",
    "manual_review_required",
    "not_found",
    "error",
]
ToolStatus = Literal["success", "not_found", "error"]


class DeliveryCompensationInput(BaseModel):
    order_id: str = Field(min_length=1)
    trace_id: str | None = None
    policy_top_k: int = Field(default=3, ge=1, le=10)


class DeliveryCompensationOutput(BaseModel):
    status: ToolStatus
    order_id: str
    decision: DeliveryDecision
    approval_required: bool
    delivered_late: bool = False
    late_days: int | None = None
    rationale: str
    policy_refs: list[str] = Field(default_factory=list)
    order_summary: OrderSummaryOutput | None = None
    error: ToolError | None = None


def decide_delivery_compensation(order_summary: OrderSummaryOutput) -> tuple[DeliveryDecision, bool, str]:
    if order_summary.status == "not_found":
        return "not_found", False, "Order was not found."
    if order_summary.status == "error":
        return "error", False, "Order summary lookup failed."
    if order_summary.order_status != "delivered":
        return (
            "manual_review_required",
            True,
            "Order is not marked delivered, so delivery compensation cannot be decided from delivered date alone.",
        )
    if order_summary.late_days is None:
        return (
            "manual_review_required",
            True,
            "Delivered and estimated delivery timestamps are incomplete.",
        )
    if order_summary.late_days > 2:
        return (
            "eligible_with_manual_approval",
            True,
            "Delivered date is more than 2 natural days later than the estimated delivery date.",
        )
    return (
        "not_eligible",
        False,
        "Delivered date is not more than 2 natural days later than the estimated delivery date.",
    )


def check_delivery_compensation(
    request: DeliveryCompensationInput,
    database_url: str | None = None,
) -> DeliveryCompensationOutput:
    settings = get_settings()
    started_at = perf_counter()
    database_url = database_url or settings.database_url

    order_summary = get_order_summary(
        GetOrderSummaryInput(order_id=request.order_id, trace_id=request.trace_id),
        database_url=database_url,
    )
    decision, approval_required, rationale = decide_delivery_compensation(order_summary)
    if decision in {"not_found", "error"}:
        result = DeliveryCompensationOutput(
            status="not_found" if decision == "not_found" else "error",
            order_id=request.order_id,
            decision=decision,
            approval_required=approval_required,
            delivered_late=order_summary.delivered_late,
            late_days=order_summary.late_days,
            rationale=rationale,
            order_summary=order_summary,
            error=order_summary.error,
        )
        try_log_delivery_result(database_url, request, result, started_at)
        return result

    policy_result = search_policy_tool(
        PolicySearchInput(
            query="延迟送达如何补偿",
            doc_types=["delivery_sla_policy"],
            top_k=request.policy_top_k,
            rerank=True,
            trace_id=request.trace_id,
        )
    )
    if policy_result.status == "error":
        result = DeliveryCompensationOutput(
            status="error",
            order_id=request.order_id,
            decision="error",
            approval_required=False,
            delivered_late=order_summary.delivered_late,
            late_days=order_summary.late_days,
            rationale="Policy retrieval failed.",
            order_summary=order_summary,
            error=policy_result.error,
        )
        try_log_delivery_result(database_url, request, result, started_at)
        return result

    result = DeliveryCompensationOutput(
        status="success",
        order_id=request.order_id,
        decision=decision,
        approval_required=approval_required,
        delivered_late=order_summary.delivered_late,
        late_days=order_summary.late_days,
        rationale=rationale,
        policy_refs=[citation.ref for citation in policy_result.results],
        order_summary=order_summary,
    )
    try_log_delivery_result(database_url, request, result, started_at)
    return result


def try_log_delivery_result(
    database_url: str,
    request: DeliveryCompensationInput,
    result: DeliveryCompensationOutput,
    started_at: float,
) -> None:
    try_insert_tool_call_log(
        database_url,
        trace_id=request.trace_id,
        tool_name="check_delivery_compensation",
        args=request,
        result=result,
        status=result.status,
        latency_ms=elapsed_ms(started_at),
        error_type=result.error.code if result.error else None,
    )
