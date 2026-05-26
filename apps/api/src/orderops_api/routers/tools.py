from fastapi import APIRouter

from orderops_api.tools.delivery_tools import (
    DeliveryCompensationInput,
    DeliveryCompensationOutput,
    check_delivery_compensation,
)
from orderops_api.tools.order_tools import GetOrderSummaryInput, OrderSummaryOutput, get_order_summary
from orderops_api.tools.policy_tools import PolicySearchInput, PolicySearchOutput, search_policy_tool


router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.post("/order-summary", response_model=OrderSummaryOutput)
def order_summary(request: GetOrderSummaryInput) -> OrderSummaryOutput:
    return get_order_summary(request)


@router.post("/policy-search", response_model=PolicySearchOutput)
def policy_search(request: PolicySearchInput) -> PolicySearchOutput:
    return search_policy_tool(request)


@router.post("/delivery-compensation", response_model=DeliveryCompensationOutput)
def delivery_compensation(request: DeliveryCompensationInput) -> DeliveryCompensationOutput:
    return check_delivery_compensation(request)
