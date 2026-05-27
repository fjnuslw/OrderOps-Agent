from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from orderops_api.agent.guard import (
    detect_prompt_injection,
    extract_hex_id,
    infer_intent,
    safe_ops_sql_for_message,
)
from orderops_api.agent.state import (
    AgentRunInput,
    AgentRunOutput,
    AgentState,
    append_citation,
    append_step,
    append_tool_call,
    initial_state,
    output_from_state,
    set_plan,
)
from orderops_api.tools.analysis_tools import SellerQualityInput, analyze_seller_quality
from orderops_api.tools.delivery_tools import DeliveryCompensationInput, check_delivery_compensation
from orderops_api.tools.order_tools import GetOrderSummaryInput, get_order_summary
from orderops_api.tools.policy_tools import PolicySearchInput, search_policy_tool
from orderops_api.tools.refund_tools import RefundEligibilityInput, check_refund_eligibility
from orderops_api.tools.sql_tools import SqlAnalysisInput, run_sql_analysis
from orderops_api.tools.ticket_tools import CreateSupportTicketDraftInput, create_support_ticket_draft


@dataclass(frozen=True)
class AgentTools:
    get_order_summary: Callable[..., Any] = get_order_summary
    search_policy: Callable[..., Any] = search_policy_tool
    check_delivery_compensation: Callable[..., Any] = check_delivery_compensation
    check_refund_eligibility: Callable[..., Any] = check_refund_eligibility
    create_support_ticket_draft: Callable[..., Any] = create_support_ticket_draft
    run_sql_analysis: Callable[..., Any] = run_sql_analysis
    analyze_seller_quality: Callable[..., Any] = analyze_seller_quality


def elapsed_node_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def infer_refund_reason(message: str) -> str:
    text = message.lower()
    if any(keyword in text for keyword in ("quality", "damaged", "broken", "defective", "破损", "损坏", "质量")):
        return "quality_issue"
    if any(keyword in text for keyword in ("delay", "late", "延迟", "晚到", "迟到")):
        return "delivery_delay"
    if any(keyword in text for keyword in ("cancel", "canceled", "取消")):
        return "canceled_order"
    return "unknown"


def input_guard_node(state: AgentState) -> AgentState:
    started_at = perf_counter()
    reason = detect_prompt_injection(state["message"])
    if reason:
        state["blocked"] = True
        state["blocked_reason"] = reason
        state["intent"] = "blocked"
        state["risk_level"] = "high"
        append_step(state, "input_guard", "blocked", reason, elapsed_node_ms(started_at))
        return state

    state["blocked"] = False
    if state.get("order_id") is None:
        state["order_id"] = extract_hex_id(state["message"])
    if state.get("seller_id") is None and any(token in state["message"].lower() for token in ("seller", "卖家")):
        state["seller_id"] = extract_hex_id(state["message"])
    append_step(
        state,
        "input_guard",
        "success",
        "Input accepted and identifiers extracted.",
        elapsed_node_ms(started_at),
    )
    return state


def intent_router_node(state: AgentState) -> AgentState:
    started_at = perf_counter()
    intent = infer_intent(state["message"], state["user_role"])
    if intent in {"delivery_compensation", "refund_review"} and not state.get("order_id"):
        state["intent"] = "missing_context"
        append_step(
            state,
            "intent_router",
            "missing_context",
            "Order id is required for this intent.",
            elapsed_node_ms(started_at),
        )
        return state
    if intent == "seller_quality" and not state.get("seller_id"):
        state["seller_id"] = extract_hex_id(state["message"])
        if not state.get("seller_id"):
            state["intent"] = "missing_context"
            append_step(
                state,
                "intent_router",
                "missing_context",
                "Seller id is required for this intent.",
                elapsed_node_ms(started_at),
            )
            return state
    state["intent"] = intent
    append_step(state, "intent_router", "success", f"Intent routed to {intent}.", elapsed_node_ms(started_at))
    return state


def query_rewrite_node(state: AgentState) -> AgentState:
    started_at = perf_counter()
    intent = state.get("intent")
    if intent == "delivery_compensation":
        state["policy_doc_types"] = ["delivery_sla_policy"]
        state["rewritten_query"] = f"delivery delay compensation policy for order {state.get('order_id')}"
    elif intent == "refund_review":
        state["policy_doc_types"] = ["refund_policy"]
        state["rewritten_query"] = f"refund eligibility and manual approval policy for order {state.get('order_id')}"
    elif intent == "policy_qa":
        state["policy_doc_types"] = []
        state["rewritten_query"] = state["message"]
    elif intent == "seller_quality":
        state["policy_doc_types"] = []
        state["rewritten_query"] = f"seller quality analysis for seller {state.get('seller_id')}"
    elif intent == "ops_sql_analysis":
        state["policy_doc_types"] = []
        state["rewritten_query"] = state["message"]
    else:
        state["policy_doc_types"] = []
        state["rewritten_query"] = state["message"]
    append_step(state, "query_rewrite", "success", "Query rewritten for retrieval and tool planning.", elapsed_node_ms(started_at))
    return state


def plan_builder_node(state: AgentState) -> AgentState:
    started_at = perf_counter()
    intent = state.get("intent")
    if intent == "delivery_compensation":
        set_plan(
            state,
            [
                ("get_order_summary", "Need order fulfillment timestamps and payment context."),
                ("search_policy", "Need delayed delivery compensation policy evidence."),
                ("check_delivery_compensation", "Need deterministic business-rule decision."),
                ("create_support_ticket_draft", "Create only a draft if manual approval is required."),
            ],
        )
    elif intent == "refund_review":
        set_plan(
            state,
            [
                ("get_order_summary", "Need order status, delivery timestamp, payment, and review signals."),
                ("search_policy", "Need refund window and manual review policy evidence."),
                ("check_refund_eligibility", "Need deterministic refund eligibility decision."),
                ("create_support_ticket_draft", "Create only a draft if manual approval is required."),
            ],
        )
    elif intent == "policy_qa":
        set_plan(state, [("search_policy", "Answer from policy citations.")])
    elif intent == "seller_quality":
        set_plan(state, [("analyze_seller_quality", "Generate seller quality metrics and risk level.")])
    elif intent == "ops_sql_analysis":
        set_plan(state, [("sql_analysis", "Run an approved read-only SQL template.")])
    else:
        state["plan"] = []
    append_step(state, "plan_builder", "success", f"{len(state.get('plan', []))} planned step(s).", elapsed_node_ms(started_at))
    return state


def order_summary_node(tools: AgentTools) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        started_at = perf_counter()
        result = tools.get_order_summary(
            GetOrderSummaryInput(order_id=state["order_id"], trace_id=state["trace_id"])
        )
        state["order_summary"] = result.model_dump(mode="json")
        if result.status in {"not_found", "error"}:
            state["decision"] = result.status
            state["approval_required"] = False
            state["approval_status"] = "not_required"
        append_tool_call(state, "get_order_summary", result.status, f"order_id={state['order_id']}")
        append_step(state, "order_summary", result.status, "Order summary retrieved.", elapsed_node_ms(started_at))
        return state

    return node


def policy_retriever_node(tools: AgentTools) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        started_at = perf_counter()
        result = tools.search_policy(
            PolicySearchInput(
                query=state.get("rewritten_query") or state["message"],
                doc_types=state.get("policy_doc_types", []),
                top_k=3,
                rerank=True,
                trace_id=state["trace_id"],
            )
        )
        state["policy_result"] = result.model_dump(mode="json")
        for citation in result.results:
            append_citation(state, citation.ref, citation.title)
        append_tool_call(state, "search_policy", result.status, f"results={len(result.results)}")
        append_step(state, "policy_retriever", result.status, "Policy citations retrieved.", elapsed_node_ms(started_at))
        return state

    return node


def delivery_compensation_node(tools: AgentTools) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        started_at = perf_counter()
        result = tools.check_delivery_compensation(
            DeliveryCompensationInput(order_id=state["order_id"], policy_top_k=1, trace_id=state["trace_id"])
        )
        state["delivery_result"] = result.model_dump(mode="json")
        state["decision"] = result.decision
        state["approval_required"] = result.approval_required
        state["approval_status"] = "pending" if result.approval_required else "not_required"
        for ref in result.policy_refs:
            append_citation(state, ref)
        append_tool_call(
            state,
            "check_delivery_compensation",
            result.status,
            f"decision={result.decision}, approval_required={result.approval_required}",
        )
        append_step(state, "delivery_compensation", result.status, result.rationale, elapsed_node_ms(started_at))
        return state

    return node


def refund_eligibility_node(tools: AgentTools) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        started_at = perf_counter()
        result = tools.check_refund_eligibility(
            RefundEligibilityInput(
                order_id=state["order_id"],
                reason_category=infer_refund_reason(state["message"]),
                request_at=state.get("request_at") or datetime.now(),
                customer_message=state["message"],
                policy_top_k=1,
                trace_id=state["trace_id"],
            )
        )
        state["refund_result"] = result.model_dump(mode="json")
        state["decision"] = result.decision
        state["approval_required"] = result.approval_required
        state["approval_status"] = "pending" if result.approval_required else "not_required"
        state["risk_level"] = "high" if "high_value_order" in result.risk_flags else state.get("risk_level")
        for ref in result.policy_refs:
            append_citation(state, ref)
        append_tool_call(
            state,
            "check_refund_eligibility",
            result.status,
            f"decision={result.decision}, approval_required={result.approval_required}",
        )
        append_step(state, "refund_eligibility", result.status, result.rationale, elapsed_node_ms(started_at))
        return state

    return node


def sql_analysis_node(tools: AgentTools) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        started_at = perf_counter()
        sql = safe_ops_sql_for_message(state["message"])
        if sql is None:
            state["sql_result"] = {"status": "blocked", "row_count": 0}
            append_tool_call(state, "sql_analysis", "blocked", "No approved SQL template matched.")
            append_step(state, "sql_analysis", "blocked", "No approved SQL template matched the request.", elapsed_node_ms(started_at))
            return state
        result = tools.run_sql_analysis(SqlAnalysisInput(sql=sql, limit=20, trace_id=state["trace_id"]))
        state["sql_result"] = result.model_dump(mode="json")
        append_tool_call(state, "sql_analysis", result.status, f"rows={result.row_count}")
        append_step(state, "sql_analysis", result.status, "Read-only SQL analysis completed.", elapsed_node_ms(started_at))
        return state

    return node


def seller_quality_node(tools: AgentTools) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        started_at = perf_counter()
        result = tools.analyze_seller_quality(
            SellerQualityInput(seller_id=state["seller_id"], trace_id=state["trace_id"])
        )
        state["seller_result"] = result.model_dump(mode="json")
        state["risk_level"] = result.risk_level
        append_tool_call(
            state,
            "seller_quality_analysis",
            result.status,
            f"risk_level={result.risk_level}, total_orders={result.total_orders}",
        )
        append_step(state, "seller_quality", result.status, "Seller quality metrics generated.", elapsed_node_ms(started_at))
        return state

    return node


def rule_verifier_node(state: AgentState) -> AgentState:
    started_at = perf_counter()
    intent = state.get("intent")
    if intent in {"delivery_compensation", "refund_review"}:
        decision = state.get("decision")
        if decision in {"not_found", "error"}:
            state["approval_required"] = False
            state["approval_status"] = "not_required"
            status = "blocked"
            summary = f"Business decision ended with {decision}; no write action is allowed."
        elif state.get("approval_required"):
            status = "success"
            summary = "Business rule requires manual approval before any operational action."
        else:
            status = "success"
            summary = "Business rule does not require manual approval."
    else:
        status = "skipped"
        summary = "No business decision verification needed for this intent."
    append_step(state, "rule_verifier", status, summary, elapsed_node_ms(started_at))
    return state


def approval_gate_node(state: AgentState) -> AgentState:
    started_at = perf_counter()
    if state.get("approval_required"):
        state["approval_status"] = "pending"
        summary = "Approval gate opened; write action can only create a draft pending approval."
    else:
        state["approval_status"] = "not_required"
        summary = "Approval gate closed; no manual approval required."
    append_step(state, "approval_gate", "success", summary, elapsed_node_ms(started_at))
    return state


def ticket_draft_node(tools: AgentTools) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        started_at = perf_counter()
        if not state.get("auto_create_ticket", True) or not state.get("approval_required"):
            append_step(state, "ticket_draft", "skipped", "No draft ticket required.", elapsed_node_ms(started_at))
            return state

        intent = state["intent"]
        if intent == "delivery_compensation":
            title = "Delivery delay compensation review"
            description = "Agent found a delayed delivery candidate requiring manual review."
            expected_action = "Review delivery policy evidence and decide whether compensation is appropriate."
            scenario = "delivery_delay"
            risk_level = "high" if state.get("decision") == "eligible_with_manual_approval" else "medium"
        elif intent == "refund_review":
            title = "Refund eligibility review"
            description = "Agent found a refund review candidate requiring manual review."
            expected_action = "Review refund policy evidence and decide whether refund workflow should proceed."
            scenario = "refund_review"
            risk_level = "high" if state.get("risk_level") == "high" else "medium"
        else:
            append_step(state, "ticket_draft", "skipped", "Intent does not create ticket drafts.", elapsed_node_ms(started_at))
            return state

        result = tools.create_support_ticket_draft(
            CreateSupportTicketDraftInput(
                order_id=state["order_id"],
                scenario=scenario,
                title=title,
                description=description,
                expected_action=expected_action,
                priority="high" if risk_level == "high" else "medium",
                risk_level=risk_level,
                requested_by="agent_graph",
                policy_refs=[item["ref"] for item in state.get("citations", [])],
                trace_id=state["trace_id"],
            )
        )
        state["ticket_result"] = result.model_dump(mode="json")
        state["ticket_id"] = result.ticket_id
        state["approval_id"] = result.approval_id
        state["approval_status"] = result.approval_status
        append_tool_call(state, "create_support_ticket_draft", result.status, f"ticket_id={result.ticket_id}")
        append_step(state, "ticket_draft", result.status, "Draft ticket and pending approval created.", elapsed_node_ms(started_at))
        return state

    return node


def final_composer_node(state: AgentState) -> AgentState:
    started_at = perf_counter()
    intent = state.get("intent", "missing_context")
    citation_count = len(state.get("citations", []))
    tool_count = len(state.get("tool_calls", []))
    if intent == "blocked":
        state["answer"] = "请求被安全规则拦截。该输入包含可能绕过规则、读取隐私字段或执行危险 SQL 的内容。"
    elif intent == "missing_context":
        state["answer"] = "缺少必要上下文。这个请求需要提供订单 ID 或卖家 ID。"
    elif intent == "delivery_compensation":
        state["answer"] = (
            f"延迟送达复核完成：决策为 {state.get('decision')}，审批状态为 {state.get('approval_status')}。"
            f"已调用 {tool_count} 个工具，返回 {citation_count} 条政策引用。"
        )
    elif intent == "refund_review":
        state["answer"] = (
            f"退款复核完成：决策为 {state.get('decision')}，审批状态为 {state.get('approval_status')}。"
            f"已调用 {tool_count} 个工具，返回 {citation_count} 条政策引用。"
        )
    elif intent == "seller_quality":
        state["answer"] = f"卖家质量分析完成：风险等级为 {state.get('risk_level')}。已调用 {tool_count} 个工具。"
    elif intent == "ops_sql_analysis":
        sql_result = state.get("sql_result") or {}
        state["answer"] = f"SQL 分析完成：状态 {sql_result.get('status')}，返回 {sql_result.get('row_count', 0)} 行。"
    else:
        state["answer"] = f"政策检索完成，已返回 {citation_count} 条相关引用。"
    append_step(state, "final_composer", "success", "Final auditable response composed.", elapsed_node_ms(started_at))
    return state


def guard_route(state: AgentState) -> str:
    return "final_composer" if state.get("blocked") else "intent_router"


def intent_route(state: AgentState) -> str:
    return "final_composer" if state.get("intent") in {"blocked", "missing_context"} else "query_rewrite"


def plan_route(state: AgentState) -> str:
    intent = state.get("intent")
    if intent in {"delivery_compensation", "refund_review"}:
        return "order_summary"
    if intent == "policy_qa":
        return "policy_retriever"
    if intent == "seller_quality":
        return "seller_quality"
    if intent == "ops_sql_analysis":
        return "sql_analysis"
    return "final_composer"


def after_order_route(state: AgentState) -> str:
    order_summary = state.get("order_summary") or {}
    if order_summary.get("status") in {"not_found", "error"}:
        return "rule_verifier"
    return "policy_retriever"


def after_policy_route(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "delivery_compensation":
        return "delivery_compensation"
    if intent == "refund_review":
        return "refund_eligibility"
    return "final_composer"


def approval_gate_route(state: AgentState) -> str:
    if state.get("approval_required") and state.get("auto_create_ticket", True):
        return "ticket_draft"
    return "final_composer"


def build_agent_graph(tools: AgentTools | None = None):
    tools = tools or AgentTools()
    graph = StateGraph(AgentState)
    graph.add_node("input_guard", input_guard_node)
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("query_rewrite", query_rewrite_node)
    graph.add_node("plan_builder", plan_builder_node)
    graph.add_node("order_summary", order_summary_node(tools))
    graph.add_node("policy_retriever", policy_retriever_node(tools))
    graph.add_node("delivery_compensation", delivery_compensation_node(tools))
    graph.add_node("refund_eligibility", refund_eligibility_node(tools))
    graph.add_node("sql_analysis", sql_analysis_node(tools))
    graph.add_node("seller_quality", seller_quality_node(tools))
    graph.add_node("rule_verifier", rule_verifier_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("ticket_draft", ticket_draft_node(tools))
    graph.add_node("final_composer", final_composer_node)

    graph.add_edge(START, "input_guard")
    graph.add_conditional_edges(
        "input_guard",
        guard_route,
        {"intent_router": "intent_router", "final_composer": "final_composer"},
    )
    graph.add_conditional_edges(
        "intent_router",
        intent_route,
        {"query_rewrite": "query_rewrite", "final_composer": "final_composer"},
    )
    graph.add_edge("query_rewrite", "plan_builder")
    graph.add_conditional_edges(
        "plan_builder",
        plan_route,
        {
            "order_summary": "order_summary",
            "policy_retriever": "policy_retriever",
            "seller_quality": "seller_quality",
            "sql_analysis": "sql_analysis",
            "final_composer": "final_composer",
        },
    )
    graph.add_conditional_edges(
        "order_summary",
        after_order_route,
        {"policy_retriever": "policy_retriever", "rule_verifier": "rule_verifier"},
    )
    graph.add_conditional_edges(
        "policy_retriever",
        after_policy_route,
        {
            "delivery_compensation": "delivery_compensation",
            "refund_eligibility": "refund_eligibility",
            "final_composer": "final_composer",
        },
    )
    graph.add_edge("delivery_compensation", "rule_verifier")
    graph.add_edge("refund_eligibility", "rule_verifier")
    graph.add_edge("rule_verifier", "approval_gate")
    graph.add_conditional_edges(
        "approval_gate",
        approval_gate_route,
        {"ticket_draft": "ticket_draft", "final_composer": "final_composer"},
    )
    graph.add_edge("sql_analysis", "final_composer")
    graph.add_edge("seller_quality", "final_composer")
    graph.add_edge("ticket_draft", "final_composer")
    graph.add_edge("final_composer", END)
    return graph.compile()


def run_agent(request: AgentRunInput, tools: AgentTools | None = None) -> AgentRunOutput:
    graph = build_agent_graph(tools)
    final_state = graph.invoke(initial_state(request))
    return output_from_state(final_state)
