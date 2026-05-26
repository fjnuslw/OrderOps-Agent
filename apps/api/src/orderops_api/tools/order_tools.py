from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from math import ceil
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field

from orderops_api.core.config import get_settings
from orderops_api.tools.logging import ToolError, elapsed_ms, insert_tool_call_log


ToolStatus = Literal["success", "not_found", "error"]


class GetOrderSummaryInput(BaseModel):
    order_id: str = Field(min_length=1)
    trace_id: str | None = None


class OrderTimeline(BaseModel):
    purchase_at: datetime | None = None
    approved_at: datetime | None = None
    delivered_carrier_at: datetime | None = None
    delivered_customer_at: datetime | None = None
    estimated_delivery_at: datetime | None = None


class OrderItemSummary(BaseModel):
    order_item_id: int
    product_id: str | None = None
    seller_id: str | None = None
    price: float = 0.0
    freight_value: float = 0.0


class PaymentSummary(BaseModel):
    payment_sequential: int
    payment_type: str | None = None
    payment_installments: int | None = None
    payment_value: float = 0.0


class ReviewSummary(BaseModel):
    review_id: str | None = None
    review_score: int | None = None
    review_comment_title: str | None = None
    review_comment_message: str | None = None
    review_creation_date: datetime | None = None


class TicketSummary(BaseModel):
    ticket_id: str
    scenario: str | None = None
    priority: str | None = None
    status: str | None = None
    risk_level: str | None = None
    title: str | None = None


class OrderSummaryOutput(BaseModel):
    status: ToolStatus
    order_id: str
    customer_id: str | None = None
    order_status: str | None = None
    timeline: OrderTimeline | None = None
    items: list[OrderItemSummary] = Field(default_factory=list)
    payments: list[PaymentSummary] = Field(default_factory=list)
    latest_review: ReviewSummary | None = None
    support_tickets: list[TicketSummary] = Field(default_factory=list)
    seller_ids: list[str] = Field(default_factory=list)
    total_item_value: float = 0.0
    total_freight_value: float = 0.0
    total_payment_value: float = 0.0
    delivered_late: bool = False
    late_days: int | None = None
    error: ToolError | None = None


def calculate_late_days(
    delivered_customer_at: datetime | None,
    estimated_delivery_at: datetime | None,
) -> int | None:
    if delivered_customer_at is None or estimated_delivery_at is None:
        return None
    late_seconds = (delivered_customer_at - estimated_delivery_at).total_seconds()
    if late_seconds <= 0:
        return 0
    return ceil(late_seconds / 86400)


def to_float(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def build_order_summary(
    order: dict,
    items: list[dict],
    payments: list[dict],
    latest_review: dict | None,
    tickets: list[dict],
) -> OrderSummaryOutput:
    timeline = OrderTimeline(
        purchase_at=order.get("order_purchase_timestamp"),
        approved_at=order.get("order_approved_at"),
        delivered_carrier_at=order.get("order_delivered_carrier_date"),
        delivered_customer_at=order.get("order_delivered_customer_date"),
        estimated_delivery_at=order.get("order_estimated_delivery_date"),
    )
    late_days = calculate_late_days(
        timeline.delivered_customer_at,
        timeline.estimated_delivery_at,
    )
    item_summaries = [
        OrderItemSummary(
            order_item_id=int(item["order_item_id"]),
            product_id=item.get("product_id"),
            seller_id=item.get("seller_id"),
            price=to_float(item.get("price")),
            freight_value=to_float(item.get("freight_value")),
        )
        for item in items
    ]
    payment_summaries = [
        PaymentSummary(
            payment_sequential=int(payment["payment_sequential"]),
            payment_type=payment.get("payment_type"),
            payment_installments=payment.get("payment_installments"),
            payment_value=to_float(payment.get("payment_value")),
        )
        for payment in payments
    ]
    seller_ids = sorted({item.seller_id for item in item_summaries if item.seller_id})
    review = None
    if latest_review is not None:
        review = ReviewSummary(
            review_id=latest_review.get("review_id"),
            review_score=latest_review.get("review_score"),
            review_comment_title=latest_review.get("review_comment_title"),
            review_comment_message=latest_review.get("review_comment_message"),
            review_creation_date=latest_review.get("review_creation_date"),
        )

    return OrderSummaryOutput(
        status="success",
        order_id=order["order_id"],
        customer_id=order.get("customer_id"),
        order_status=order.get("order_status"),
        timeline=timeline,
        items=item_summaries,
        payments=payment_summaries,
        latest_review=review,
        support_tickets=[
            TicketSummary(
                ticket_id=ticket["ticket_id"],
                scenario=ticket.get("scenario"),
                priority=ticket.get("priority"),
                status=ticket.get("status"),
                risk_level=ticket.get("risk_level"),
                title=ticket.get("title"),
            )
            for ticket in tickets
        ],
        seller_ids=seller_ids,
        total_item_value=sum(item.price for item in item_summaries),
        total_freight_value=sum(item.freight_value for item in item_summaries),
        total_payment_value=sum(payment.payment_value for payment in payment_summaries),
        delivered_late=late_days is not None and late_days > 0,
        late_days=late_days,
    )


def get_order_summary(
    request: GetOrderSummaryInput,
    database_url: str | None = None,
) -> OrderSummaryOutput:
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
                    SELECT
                        order_id,
                        customer_id,
                        order_status,
                        order_purchase_timestamp,
                        order_approved_at,
                        order_delivered_carrier_date,
                        order_delivered_customer_date,
                        order_estimated_delivery_date
                    FROM orders
                    WHERE order_id = %(order_id)s
                    """,
                    {"order_id": request.order_id},
                )
                order = cursor.fetchone()
                if order is None:
                    result = OrderSummaryOutput(status="not_found", order_id=request.order_id)
                    insert_tool_call_log(
                        cursor,
                        trace_id=request.trace_id,
                        tool_name="get_order_summary",
                        args=request,
                        result=result,
                        status=result.status,
                        latency_ms=elapsed_ms(started_at),
                    )
                    conn.commit()
                    return result

                cursor.execute(
                    """
                    SELECT order_item_id, product_id, seller_id, price, freight_value
                    FROM order_items
                    WHERE order_id = %(order_id)s
                    ORDER BY order_item_id
                    """,
                    {"order_id": request.order_id},
                )
                items = list(cursor.fetchall())

                cursor.execute(
                    """
                    SELECT
                        payment_sequential,
                        payment_type,
                        payment_installments,
                        payment_value
                    FROM payments
                    WHERE order_id = %(order_id)s
                    ORDER BY payment_sequential
                    """,
                    {"order_id": request.order_id},
                )
                payments = list(cursor.fetchall())

                cursor.execute(
                    """
                    SELECT
                        review_id,
                        review_score,
                        review_comment_title,
                        review_comment_message,
                        review_creation_date
                    FROM reviews
                    WHERE order_id = %(order_id)s
                    ORDER BY review_creation_date DESC NULLS LAST
                    LIMIT 1
                    """,
                    {"order_id": request.order_id},
                )
                latest_review = cursor.fetchone()

                cursor.execute(
                    """
                    SELECT ticket_id, scenario, priority, status, risk_level, title
                    FROM support_tickets
                    WHERE order_id = %(order_id)s
                    ORDER BY created_at DESC NULLS LAST, ticket_id
                    """,
                    {"order_id": request.order_id},
                )
                tickets = list(cursor.fetchall())

                result = build_order_summary(order, items, payments, latest_review, tickets)
                insert_tool_call_log(
                    cursor,
                    trace_id=request.trace_id,
                    tool_name="get_order_summary",
                    args=request,
                    result=result,
                    status=result.status,
                    latency_ms=elapsed_ms(started_at),
                )
            conn.commit()
        return result
    except Exception as exc:
        return OrderSummaryOutput(
            status="error",
            order_id=request.order_id,
            error=ToolError(code=exc.__class__.__name__, message=str(exc)),
        )
