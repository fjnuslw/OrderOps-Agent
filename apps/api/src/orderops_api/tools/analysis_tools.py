from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from orderops_api.core.config import get_settings
from orderops_api.tools.logging import ToolError, elapsed_ms, try_insert_tool_call_log
from orderops_api.tools.order_tools import to_float


RiskLevel = Literal["low", "medium", "high"]
ToolStatus = Literal["success", "not_found", "error"]


class SellerQualityInput(BaseModel):
    seller_id: str = Field(min_length=1)
    time_window_days: int = Field(default=90, ge=1, le=730)
    as_of: datetime | None = None
    trace_id: str | None = None


class SellerQualityOutput(BaseModel):
    status: ToolStatus
    seller_id: str
    time_window_days: int
    total_orders: int = 0
    delivered_orders: int = 0
    late_orders: int = 0
    low_review_orders: int = 0
    support_ticket_count: int = 0
    late_rate: float = 0.0
    low_review_rate: float = 0.0
    refund_ticket_rate: float = 0.0
    risk_level: RiskLevel = "low"
    top_issue_categories: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    error: ToolError | None = None


def rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def seller_risk_level(total_orders: int, late_rate: float, low_review_rate: float) -> RiskLevel:
    if total_orders >= 10 and late_rate > 0.20 and low_review_rate > 0.15:
        return "high"
    if total_orders >= 5 and (late_rate > 0.20 or low_review_rate > 0.15):
        return "medium"
    return "low"


def seller_issue_categories(late_rate: float, low_review_rate: float, refund_ticket_rate: float) -> list[str]:
    categories: list[str] = []
    if late_rate > 0.20:
        categories.append("late_delivery")
    if low_review_rate > 0.15:
        categories.append("low_review")
    if refund_ticket_rate > 0.10:
        categories.append("support_ticket_pressure")
    return categories


def seller_suggested_actions(risk_level: RiskLevel, issue_categories: list[str]) -> list[str]:
    if risk_level == "low":
        return ["monitor"]
    actions = ["manual_review"]
    if "late_delivery" in issue_categories:
        actions.append("review_fulfillment_sla")
    if "low_review" in issue_categories:
        actions.append("request_seller_response")
    if risk_level == "high":
        actions.append("reduce_exposure")
    return actions


def analyze_seller_quality(
    request: SellerQualityInput,
    database_url: str | None = None,
) -> SellerQualityOutput:
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
                    WITH seller_orders AS (
                        SELECT DISTINCT
                            o.order_id,
                            o.order_status,
                            o.order_purchase_timestamp,
                            o.order_delivered_customer_date,
                            o.order_estimated_delivery_date
                        FROM order_items oi
                        JOIN orders o ON o.order_id = oi.order_id
                        WHERE oi.seller_id = %(seller_id)s
                    ),
                    bounds AS (
                        SELECT COALESCE(%(as_of)s::timestamp, MAX(order_purchase_timestamp)) AS as_of
                        FROM seller_orders
                    ),
                    scoped_orders AS (
                        SELECT so.*
                        FROM seller_orders so
                        CROSS JOIN bounds b
                        WHERE b.as_of IS NOT NULL
                          AND so.order_purchase_timestamp >= (
                              b.as_of - (%(time_window_days)s::text || ' days')::interval
                          )
                    ),
                    review_flags AS (
                        SELECT DISTINCT r.order_id
                        FROM reviews r
                        JOIN scoped_orders so ON so.order_id = r.order_id
                        WHERE r.review_score <= 2
                    )
                    SELECT
                        COUNT(DISTINCT so.order_id)::int AS total_orders,
                        COUNT(DISTINCT so.order_id) FILTER (
                            WHERE so.order_status = 'delivered'
                        )::int AS delivered_orders,
                        COUNT(DISTINCT so.order_id) FILTER (
                            WHERE so.order_status = 'delivered'
                              AND so.order_delivered_customer_date >
                                  so.order_estimated_delivery_date + INTERVAL '2 days'
                        )::int AS late_orders,
                        COUNT(DISTINCT rf.order_id)::int AS low_review_orders
                    FROM scoped_orders so
                    LEFT JOIN review_flags rf ON rf.order_id = so.order_id
                    """,
                    {
                        "seller_id": request.seller_id,
                        "time_window_days": request.time_window_days,
                        "as_of": request.as_of,
                    },
                )
                metrics = cursor.fetchone()
                total_orders = int(metrics["total_orders"] or 0)
                if total_orders == 0:
                    result = SellerQualityOutput(
                        status="not_found",
                        seller_id=request.seller_id,
                        time_window_days=request.time_window_days,
                        error=ToolError(
                            code="SellerNotFound",
                            message="No seller orders found in the requested window.",
                        ),
                    )
                    log_seller_result(database_url, request, result, started_at)
                    return result

                cursor.execute(
                    """
                    SELECT COUNT(*)::int AS support_ticket_count
                    FROM support_tickets
                    WHERE seller_id = %(seller_id)s
                      AND scenario IN ('delivery_delay', 'low_review', 'canceled_order')
                    """,
                    {"seller_id": request.seller_id},
                )
                support_ticket_count = int(cursor.fetchone()["support_ticket_count"] or 0)

        delivered_orders = int(metrics["delivered_orders"] or 0)
        late_orders = int(metrics["late_orders"] or 0)
        low_review_orders = int(metrics["low_review_orders"] or 0)
        late_rate = rate(late_orders, delivered_orders)
        low_review_rate = rate(low_review_orders, total_orders)
        refund_ticket_rate = rate(support_ticket_count, total_orders)
        risk_level = seller_risk_level(total_orders, late_rate, low_review_rate)
        categories = seller_issue_categories(late_rate, low_review_rate, refund_ticket_rate)
        result = SellerQualityOutput(
            status="success",
            seller_id=request.seller_id,
            time_window_days=request.time_window_days,
            total_orders=total_orders,
            delivered_orders=delivered_orders,
            late_orders=late_orders,
            low_review_orders=low_review_orders,
            support_ticket_count=support_ticket_count,
            late_rate=to_float(late_rate),
            low_review_rate=to_float(low_review_rate),
            refund_ticket_rate=to_float(refund_ticket_rate),
            risk_level=risk_level,
            top_issue_categories=categories,
            suggested_actions=seller_suggested_actions(risk_level, categories),
        )
        log_seller_result(database_url, request, result, started_at)
        return result
    except Exception as exc:
        result = SellerQualityOutput(
            status="error",
            seller_id=request.seller_id,
            time_window_days=request.time_window_days,
            error=ToolError(code=exc.__class__.__name__, message=str(exc)),
        )
        log_seller_result(database_url, request, result, started_at)
        return result


def log_seller_result(
    database_url: str,
    request: SellerQualityInput,
    result: SellerQualityOutput,
    started_at: float,
) -> None:
    try_insert_tool_call_log(
        database_url,
        trace_id=request.trace_id,
        tool_name="seller_quality_analysis",
        args=request,
        result=result,
        status=result.status,
        latency_ms=elapsed_ms(started_at),
        error_type=result.error.code if result.error else None,
    )
