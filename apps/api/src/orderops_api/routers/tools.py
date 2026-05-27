from fastapi import APIRouter

from orderops_api.tools.analysis_tools import (
    SellerQualityInput,
    SellerQualityOutput,
    analyze_seller_quality,
)
from orderops_api.tools.approval_tools import (
    ApprovalDecisionOutput,
    DecideApprovalInput,
    decide_approval,
)
from orderops_api.tools.delivery_tools import (
    DeliveryCompensationInput,
    DeliveryCompensationOutput,
    check_delivery_compensation,
)
from orderops_api.tools.order_tools import GetOrderSummaryInput, OrderSummaryOutput, get_order_summary
from orderops_api.tools.policy_tools import PolicySearchInput, PolicySearchOutput, search_policy_tool
from orderops_api.tools.refund_tools import (
    RefundEligibilityInput,
    RefundEligibilityOutput,
    check_refund_eligibility,
)
from orderops_api.tools.sql_tools import SqlAnalysisInput, SqlAnalysisOutput, run_sql_analysis
from orderops_api.tools.ticket_tools import (
    CreateSupportTicketDraftInput,
    CreateSupportTicketDraftOutput,
    create_support_ticket_draft,
)


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


@router.post("/refund-eligibility", response_model=RefundEligibilityOutput)
def refund_eligibility(request: RefundEligibilityInput) -> RefundEligibilityOutput:
    return check_refund_eligibility(request)


@router.post("/support-ticket-draft", response_model=CreateSupportTicketDraftOutput)
def support_ticket_draft(request: CreateSupportTicketDraftInput) -> CreateSupportTicketDraftOutput:
    return create_support_ticket_draft(request)


@router.post("/approval-decision", response_model=ApprovalDecisionOutput)
def approval_decision(request: DecideApprovalInput) -> ApprovalDecisionOutput:
    return decide_approval(request)


@router.post("/sql-analysis", response_model=SqlAnalysisOutput)
def sql_analysis(request: SqlAnalysisInput) -> SqlAnalysisOutput:
    return run_sql_analysis(request)


@router.post("/seller-quality", response_model=SellerQualityOutput)
def seller_quality(request: SellerQualityInput) -> SellerQualityOutput:
    return analyze_seller_quality(request)
