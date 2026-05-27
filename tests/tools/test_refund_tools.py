from datetime import datetime

from orderops_api.tools.order_tools import OrderSummaryOutput, OrderTimeline, ReviewSummary
from orderops_api.tools.refund_tools import RefundEligibilityInput, decide_refund, has_quality_signal


def test_refund_decision_allows_review_inside_delivery_window() -> None:
    request = RefundEligibilityInput(
        order_id="ORDER-1",
        reason_category="unknown",
        request_at=datetime(2018, 1, 6),
    )
    summary = OrderSummaryOutput(
        status="success",
        order_id="ORDER-1",
        order_status="delivered",
        timeline=OrderTimeline(delivered_customer_at=datetime(2018, 1, 1)),
    )

    decision, approval_required, _, days_since, _ = decide_refund(request, summary)

    assert decision == "eligible_with_manual_approval"
    assert approval_required
    assert days_since == 5


def test_refund_decision_rejects_late_request_without_quality_signal() -> None:
    request = RefundEligibilityInput(
        order_id="ORDER-1",
        reason_category="unknown",
        request_at=datetime(2018, 1, 20),
    )
    summary = OrderSummaryOutput(
        status="success",
        order_id="ORDER-1",
        order_status="delivered",
        timeline=OrderTimeline(delivered_customer_at=datetime(2018, 1, 1)),
    )

    decision, approval_required, _, days_since, _ = decide_refund(request, summary)

    assert decision == "not_eligible"
    assert not approval_required
    assert days_since == 19


def test_quality_signal_uses_reason_review_and_message() -> None:
    request = RefundEligibilityInput(order_id="ORDER-1", customer_message="商品破损")
    summary = OrderSummaryOutput(
        status="success",
        order_id="ORDER-1",
        latest_review=ReviewSummary(review_score=5),
    )

    assert has_quality_signal(request, summary)

    review_summary = OrderSummaryOutput(
        status="success",
        order_id="ORDER-2",
        latest_review=ReviewSummary(review_score=2),
    )
    assert has_quality_signal(RefundEligibilityInput(order_id="ORDER-2"), review_summary)
