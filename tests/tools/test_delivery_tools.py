from orderops_api.tools.delivery_tools import decide_delivery_compensation
from orderops_api.tools.order_tools import OrderSummaryOutput


def test_delivery_compensation_requires_manual_approval_when_late() -> None:
    summary = OrderSummaryOutput(
        status="success",
        order_id="ORDER-1",
        order_status="delivered",
        delivered_late=True,
        late_days=3,
    )

    decision, approval_required, rationale = decide_delivery_compensation(summary)

    assert decision == "eligible_with_manual_approval"
    assert approval_required
    assert "2 natural days" in rationale


def test_delivery_compensation_rejects_on_time_delivery() -> None:
    summary = OrderSummaryOutput(
        status="success",
        order_id="ORDER-2",
        order_status="delivered",
        delivered_late=False,
        late_days=2,
    )

    decision, approval_required, _ = decide_delivery_compensation(summary)

    assert decision == "not_eligible"
    assert not approval_required


def test_delivery_compensation_sends_undelivered_orders_to_manual_review() -> None:
    summary = OrderSummaryOutput(
        status="success",
        order_id="ORDER-3",
        order_status="shipped",
    )

    decision, approval_required, rationale = decide_delivery_compensation(summary)

    assert decision == "manual_review_required"
    assert approval_required
    assert "not marked delivered" in rationale
