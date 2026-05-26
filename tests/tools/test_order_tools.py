from datetime import datetime

from orderops_api.tools.order_tools import build_order_summary, calculate_late_days


def test_calculate_late_days_uses_natural_day_ceiling() -> None:
    estimated = datetime(2018, 1, 1, 12, 0, 0)
    delivered = datetime(2018, 1, 3, 13, 0, 0)

    assert calculate_late_days(delivered, estimated) == 3
    assert calculate_late_days(estimated, delivered) == 0
    assert calculate_late_days(None, estimated) is None


def test_build_order_summary_aggregates_money_and_sellers() -> None:
    summary = build_order_summary(
        order={
            "order_id": "ORDER-1",
            "customer_id": "CUSTOMER-1",
            "order_status": "delivered",
            "order_purchase_timestamp": datetime(2018, 1, 1),
            "order_approved_at": datetime(2018, 1, 1),
            "order_delivered_carrier_date": datetime(2018, 1, 2),
            "order_delivered_customer_date": datetime(2018, 1, 6),
            "order_estimated_delivery_date": datetime(2018, 1, 3),
        },
        items=[
            {
                "order_item_id": 1,
                "product_id": "PRODUCT-1",
                "seller_id": "SELLER-2",
                "price": 10,
                "freight_value": 2,
            },
            {
                "order_item_id": 2,
                "product_id": "PRODUCT-2",
                "seller_id": "SELLER-1",
                "price": 20,
                "freight_value": 3,
            },
        ],
        payments=[
            {
                "payment_sequential": 1,
                "payment_type": "credit_card",
                "payment_installments": 1,
                "payment_value": 35,
            }
        ],
        latest_review=None,
        tickets=[],
    )

    assert summary.status == "success"
    assert summary.total_item_value == 30
    assert summary.total_freight_value == 5
    assert summary.total_payment_value == 35
    assert summary.seller_ids == ["SELLER-1", "SELLER-2"]
    assert summary.delivered_late
    assert summary.late_days == 3
