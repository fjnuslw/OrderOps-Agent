from orderops_api.tools.analysis_tools import (
    seller_issue_categories,
    seller_risk_level,
    seller_suggested_actions,
)


def test_seller_risk_level_uses_late_and_review_rates() -> None:
    assert seller_risk_level(20, 0.25, 0.20) == "high"
    assert seller_risk_level(8, 0.25, 0.05) == "medium"
    assert seller_risk_level(4, 0.5, 0.5) == "low"


def test_seller_issue_categories_and_actions_are_stable() -> None:
    categories = seller_issue_categories(0.25, 0.2, 0.12)

    assert categories == ["late_delivery", "low_review", "support_ticket_pressure"]
    assert seller_suggested_actions("high", categories) == [
        "manual_review",
        "review_fulfillment_sla",
        "request_seller_response",
        "reduce_exposure",
    ]
    assert seller_suggested_actions("low", []) == ["monitor"]
