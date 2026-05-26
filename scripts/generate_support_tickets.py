from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
from typing import Any, Callable, Iterable

from orderops_api.core.config import get_settings


DEFAULT_LIMIT_PER_SCENARIO = 100
HIGH_VALUE_THRESHOLD = 1000


@dataclass(frozen=True)
class TicketDraft:
    ticket_id: str
    order_id: str
    customer_id: str | None
    seller_id: str | None
    scenario: str
    priority: str
    status: str
    created_at: datetime
    title: str
    description: str
    expected_action: str
    risk_level: str


def make_ticket_id(scenario: str, order_id: str) -> str:
    digest = sha1(f"{scenario}:{order_id}".encode("utf-8")).hexdigest()[:12]
    return f"TICKET-{digest.upper()}"


def priority_for_delivery_delay(late_days: int) -> str:
    if late_days >= 7:
        return "high"
    if late_days >= 3:
        return "medium"
    return "low"


def priority_for_review_score(review_score: int) -> str:
    return "high" if review_score <= 1 else "medium"


def priority_for_order_value(total_value: float) -> str:
    return "high" if total_value >= 2000 else "medium"


def ticket_timestamp() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def build_delivery_delay_ticket(row: dict[str, Any]) -> TicketDraft:
    late_days = int(row["late_days"])
    order_id = row["order_id"]
    return TicketDraft(
        ticket_id=make_ticket_id("delivery_delay", order_id),
        order_id=order_id,
        customer_id=row.get("customer_id"),
        seller_id=row.get("seller_id"),
        scenario="delivery_delay",
        priority=priority_for_delivery_delay(late_days),
        status="open",
        created_at=ticket_timestamp(),
        title="Delivery delay compensation review",
        description=f"Order {order_id} was delivered {late_days} days after the estimated date.",
        expected_action="Check delivery SLA policy and prepare a compensation decision draft.",
        risk_level="medium" if late_days < 7 else "high",
    )


def build_low_review_ticket(row: dict[str, Any]) -> TicketDraft:
    review_score = int(row["review_score"])
    order_id = row["order_id"]
    return TicketDraft(
        ticket_id=make_ticket_id("low_review", order_id),
        order_id=order_id,
        customer_id=row.get("customer_id"),
        seller_id=row.get("seller_id"),
        scenario="low_review",
        priority=priority_for_review_score(review_score),
        status="open",
        created_at=ticket_timestamp(),
        title="Low review follow-up",
        description=f"Order {order_id} received review score {review_score}.",
        expected_action="Review customer feedback, order context, and policy before drafting a reply.",
        risk_level="medium",
    )


def build_canceled_order_ticket(row: dict[str, Any]) -> TicketDraft:
    order_id = row["order_id"]
    return TicketDraft(
        ticket_id=make_ticket_id("canceled_order", order_id),
        order_id=order_id,
        customer_id=row.get("customer_id"),
        seller_id=row.get("seller_id"),
        scenario="canceled_order",
        priority="medium",
        status="open",
        created_at=ticket_timestamp(),
        title="Canceled order refund check",
        description=f"Order {order_id} was canceled and may require refund status follow-up.",
        expected_action="Check refund policy and payment status before responding to the customer.",
        risk_level="medium",
    )


def build_high_value_order_ticket(row: dict[str, Any]) -> TicketDraft:
    total_value = float(row["total_value"])
    order_id = row["order_id"]
    return TicketDraft(
        ticket_id=make_ticket_id("high_value_order", order_id),
        order_id=order_id,
        customer_id=row.get("customer_id"),
        seller_id=row.get("seller_id"),
        scenario="high_value_order",
        priority=priority_for_order_value(total_value),
        status="open",
        created_at=ticket_timestamp(),
        title="High value order review",
        description=f"Order {order_id} has total payment value {total_value:.2f}.",
        expected_action="Review fulfillment and support history before taking high-impact actions.",
        risk_level="high" if total_value >= 2000 else "medium",
    )


SCENARIO_BUILDERS: dict[str, Callable[[dict[str, Any]], TicketDraft]] = {
    "delivery_delay": build_delivery_delay_ticket,
    "low_review": build_low_review_ticket,
    "canceled_order": build_canceled_order_ticket,
    "high_value_order": build_high_value_order_ticket,
}


SCENARIO_QUERIES: dict[str, str] = {
    "delivery_delay": """
        SELECT
            o.order_id,
            o.customer_id,
            MIN(oi.seller_id) AS seller_id,
            CEIL(EXTRACT(EPOCH FROM (
                o.order_delivered_customer_date - o.order_estimated_delivery_date
            )) / 86400.0)::int AS late_days
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.order_status = 'delivered'
          AND o.order_delivered_customer_date > o.order_estimated_delivery_date + INTERVAL '2 days'
        GROUP BY o.order_id, o.customer_id, late_days
        ORDER BY late_days DESC, o.order_id
        LIMIT %(limit)s
    """,
    "low_review": """
        WITH ranked_reviews AS (
            SELECT DISTINCT ON (r.order_id)
                r.order_id,
                o.customer_id,
                MIN(oi.seller_id) OVER (PARTITION BY r.order_id) AS seller_id,
                r.review_score,
                r.review_creation_date
            FROM reviews r
            JOIN orders o ON o.order_id = r.order_id
            LEFT JOIN order_items oi ON oi.order_id = r.order_id
            WHERE r.review_score <= 2
            ORDER BY r.order_id, r.review_score ASC, r.review_creation_date DESC NULLS LAST
        )
        SELECT order_id, customer_id, seller_id, review_score
        FROM ranked_reviews
        ORDER BY review_score ASC, review_creation_date DESC NULLS LAST, order_id
        LIMIT %(limit)s
    """,
    "canceled_order": """
        SELECT
            o.order_id,
            o.customer_id,
            MIN(oi.seller_id) AS seller_id
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.order_status = 'canceled'
        GROUP BY o.order_id, o.customer_id, o.order_purchase_timestamp
        ORDER BY o.order_purchase_timestamp DESC NULLS LAST, o.order_id
        LIMIT %(limit)s
    """,
    "high_value_order": """
        WITH payment_totals AS (
            SELECT order_id, SUM(payment_value) AS total_value
            FROM payments
            GROUP BY order_id
            HAVING SUM(payment_value) >= %(high_value_threshold)s
        )
        SELECT
            p.order_id,
            o.customer_id,
            MIN(oi.seller_id) AS seller_id,
            p.total_value
        FROM payment_totals p
        JOIN orders o ON o.order_id = p.order_id
        LEFT JOIN order_items oi ON oi.order_id = p.order_id
        GROUP BY p.order_id, o.customer_id, p.total_value
        ORDER BY p.total_value DESC, p.order_id
        LIMIT %(limit)s
    """,
}


def fetch_candidate_rows(cursor, scenario: str, limit: int) -> list[dict[str, Any]]:
    cursor.execute(
        SCENARIO_QUERIES[scenario],
        {"limit": limit, "high_value_threshold": HIGH_VALUE_THRESHOLD},
    )
    column_names = [column.name for column in cursor.description]
    return [dict(zip(column_names, row, strict=True)) for row in cursor.fetchall()]


def build_tickets(rows: Iterable[dict[str, Any]], scenario: str) -> list[TicketDraft]:
    builder = SCENARIO_BUILDERS[scenario]
    return [builder(row) for row in rows]


def replace_support_tickets(cursor) -> None:
    cursor.execute("TRUNCATE TABLE support_tickets")


def insert_tickets(cursor, tickets: Iterable[TicketDraft]) -> None:
    insert_sql = """
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
    """
    for ticket in tickets:
        cursor.execute(insert_sql, ticket.__dict__)


def ticket_counts(cursor) -> dict[str, int]:
    cursor.execute(
        """
        SELECT scenario, COUNT(*) AS count
        FROM support_tickets
        GROUP BY scenario
        ORDER BY scenario
        """
    )
    return {scenario: count for scenario, count in cursor.fetchall()}


def generate_support_tickets(
    database_url: str,
    limit_per_scenario: int = DEFAULT_LIMIT_PER_SCENARIO,
    replace: bool = False,
) -> dict[str, int]:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            if replace:
                replace_support_tickets(cursor)
            for scenario in SCENARIO_QUERIES:
                rows = fetch_candidate_rows(cursor, scenario, limit_per_scenario)
                insert_tickets(cursor, build_tickets(rows, scenario))
            counts = ticket_counts(cursor)
        conn.commit()
    return counts


def main() -> None:
    parser = ArgumentParser(description="Generate derived support tickets from Olist data.")
    parser.add_argument(
        "--limit-per-scenario",
        type=int,
        default=DEFAULT_LIMIT_PER_SCENARIO,
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing support_tickets before generating new tickets.",
    )
    args = parser.parse_args()

    settings = get_settings()
    counts = generate_support_tickets(
        settings.database_url,
        limit_per_scenario=args.limit_per_scenario,
        replace=args.replace,
    )

    total = sum(counts.values())
    print(f"support_tickets_total: {total}")
    for scenario, count in counts.items():
        print(f"{scenario}: {count}")


if __name__ == "__main__":
    main()
