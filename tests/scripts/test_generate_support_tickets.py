from scripts.generate_support_tickets import (
    build_delivery_delay_ticket,
    build_high_value_order_ticket,
    make_ticket_id,
    priority_for_delivery_delay,
    priority_for_order_value,
    priority_for_review_score,
)


def test_make_ticket_id_is_deterministic() -> None:
    first = make_ticket_id("delivery_delay", "ORDER-1")
    second = make_ticket_id("delivery_delay", "ORDER-1")

    assert first == second
    assert first.startswith("TICKET-")


def test_priority_rules_are_stable() -> None:
    assert priority_for_delivery_delay(2) == "low"
    assert priority_for_delivery_delay(3) == "medium"
    assert priority_for_delivery_delay(7) == "high"
    assert priority_for_review_score(1) == "high"
    assert priority_for_review_score(2) == "medium"
    assert priority_for_order_value(999.99) == "medium"
    assert priority_for_order_value(2000.0) == "high"


def test_delivery_delay_ticket_uses_late_days() -> None:
    ticket = build_delivery_delay_ticket(
        {
            "order_id": "ORDER-1",
            "customer_id": "CUSTOMER-1",
            "seller_id": "SELLER-1",
            "late_days": 8,
        }
    )

    assert ticket.scenario == "delivery_delay"
    assert ticket.priority == "high"
    assert ticket.risk_level == "high"
    assert "8 days" in ticket.description


def test_high_value_ticket_uses_payment_total() -> None:
    ticket = build_high_value_order_ticket(
        {
            "order_id": "ORDER-2",
            "customer_id": "CUSTOMER-2",
            "seller_id": "SELLER-2",
            "total_value": 2500.25,
        }
    )

    assert ticket.scenario == "high_value_order"
    assert ticket.priority == "high"
    assert ticket.risk_level == "high"
    assert "2500.25" in ticket.description
