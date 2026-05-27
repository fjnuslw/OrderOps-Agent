from __future__ import annotations

from datetime import datetime
from math import ceil
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from orderops_api.core.config import get_settings
from orderops_api.tools.logging import ToolError, elapsed_ms, try_insert_tool_call_log
from orderops_api.tools.order_tools import GetOrderSummaryInput, OrderSummaryOutput, get_order_summary
from orderops_api.tools.policy_tools import PolicySearchInput, search_policy_tool


RefundReason = Literal["quality_issue", "delivery_delay", "canceled_order", "unknown"]
RefundDecision = Literal[
    "eligible_with_manual_approval",
    "manual_review_required",
    "not_eligible",
    "not_found",
    "error",
]
ToolStatus = Literal["success", "not_found", "error"]


class RefundEligibilityInput(BaseModel):
    order_id: str = Field(min_length=1)
    reason_category: RefundReason = "unknown"
    request_at: datetime | None = None
    customer_message: str = ""
    policy_top_k: int = Field(default=3, ge=1, le=10)
    trace_id: str | None = None


class RefundEligibilityOutput(BaseModel):
    status: ToolStatus
    order_id: str
    decision: RefundDecision
    approval_required: bool
    rationale: str
    days_since_delivery: int | None = None
    risk_flags: list[str] = Field(default_factory=list)
    policy_refs: list[str] = Field(default_factory=list)
    order_summary: OrderSummaryOutput | None = None
    error: ToolError | None = None


QUALITY_KEYWORDS = (
    "broken",
    "damaged",
    "defective",
    "wrong item",
    "quality",
    "破损",
    "损坏",
    "质量",
    "错发",
    "少发",
)


def days_between(later: datetime | None, earlier: datetime | None) -> int | None:
    if later is None or earlier is None:
        return None
    delta_seconds = (later - earlier).total_seconds()
    if delta_seconds < 0:
        return 0
    return ceil(delta_seconds / 86400)


def has_quality_signal(request: RefundEligibilityInput, order_summary: OrderSummaryOutput) -> bool:
    if request.reason_category == "quality_issue":
        return True
    if order_summary.latest_review and order_summary.latest_review.review_score is not None:
        if order_summary.latest_review.review_score <= 2:
            return True
    message = request.customer_message.lower()
    return any(keyword in message for keyword in QUALITY_KEYWORDS)


def refund_risk_flags(request: RefundEligibilityInput, order_summary: OrderSummaryOutput) -> list[str]:
    flags: list[str] = []
    if order_summary.total_payment_value >= 1000:
        flags.append("high_value_order")
    if request.request_at is None:
        flags.append("missing_request_timestamp")
    if request.reason_category == "unknown":
        flags.append("unknown_reason")
    if order_summary.latest_review and order_summary.latest_review.review_score is not None:
        if order_summary.latest_review.review_score <= 2:
            flags.append("low_review_score")
    return flags


def decide_refund(
    request: RefundEligibilityInput,
    order_summary: OrderSummaryOutput,
) -> tuple[RefundDecision, bool, str, int | None, list[str]]:
    if order_summary.status == "not_found":
        return "not_found", False, "Order was not found.", None, []
    if order_summary.status == "error":
        return "error", False, "Order summary lookup failed.", None, []

    flags = refund_risk_flags(request, order_summary)
    quality_signal = has_quality_signal(request, order_summary)

    if order_summary.order_status in {"canceled", "unavailable"}:
        return (
            "manual_review_required",
            True,
            "Canceled or unavailable orders require fulfillment/refund status review.",
            None,
            flags,
        )

    if order_summary.order_status != "delivered":
        return (
            "manual_review_required",
            True,
            "Order is not delivered, so refund eligibility cannot be decided from delivery-window policy alone.",
            None,
            flags,
        )

    delivered_at = order_summary.timeline.delivered_customer_at if order_summary.timeline else None
    days_since = days_between(request.request_at, delivered_at)
    if days_since is None:
        return (
            "manual_review_required",
            True,
            "Request timestamp or delivered timestamp is missing.",
            None,
            flags,
        )

    if days_since <= 7:
        return (
            "eligible_with_manual_approval",
            True,
            "Request is within 7 natural days after delivery and can enter refund review.",
            days_since,
            flags,
        )

    if quality_signal:
        return (
            "manual_review_required",
            True,
            "Request is outside the 7-day window, but quality signals require human review.",
            days_since,
            flags,
        )

    return (
        "not_eligible",
        False,
        "Request is outside the 7-day window and no quality signal is available.",
        days_since,
        flags,
    )


def check_refund_eligibility(
    request: RefundEligibilityInput,
    database_url: str | None = None,
) -> RefundEligibilityOutput:
    settings = get_settings()
    started_at = perf_counter()
    database_url = database_url or settings.database_url

    order_summary = get_order_summary(
        GetOrderSummaryInput(order_id=request.order_id, trace_id=request.trace_id),
        database_url=database_url,
    )
    decision, approval_required, rationale, days_since, flags = decide_refund(request, order_summary)
    if decision in {"not_found", "error"}:
        result = RefundEligibilityOutput(
            status="not_found" if decision == "not_found" else "error",
            order_id=request.order_id,
            decision=decision,
            approval_required=approval_required,
            rationale=rationale,
            order_summary=order_summary,
            error=order_summary.error,
        )
        log_refund_result(database_url, request, result, started_at)
        return result

    policy_refs: list[str] = []
    policy_result = search_policy_tool(
        PolicySearchInput(
            query="退款复核条件和人工审批边界",
            doc_types=["refund_policy"],
            top_k=request.policy_top_k,
            rerank=True,
            trace_id=request.trace_id,
        )
    )
    if policy_result.status == "success":
        policy_refs = [citation.ref for citation in policy_result.results]
    elif policy_result.error is not None:
        flags.append(f"policy_retrieval_error:{policy_result.error.code}")

    result = RefundEligibilityOutput(
        status="success",
        order_id=request.order_id,
        decision=decision,
        approval_required=approval_required,
        rationale=rationale,
        days_since_delivery=days_since,
        risk_flags=flags,
        policy_refs=policy_refs,
        order_summary=order_summary,
    )
    log_refund_result(database_url, request, result, started_at)
    return result


def log_refund_result(
    database_url: str,
    request: RefundEligibilityInput,
    result: RefundEligibilityOutput,
    started_at: float,
) -> None:
    try_insert_tool_call_log(
        database_url,
        trace_id=request.trace_id,
        tool_name="check_refund_eligibility",
        args=request,
        result=result,
        status=result.status,
        latency_ms=elapsed_ms(started_at),
        error_type=result.error.code if result.error else None,
    )
