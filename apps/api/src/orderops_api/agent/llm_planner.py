from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from orderops_api.agent.state import AgentState
from orderops_api.llm.client import LLMClient


AllowedIntent = Literal[
    "delivery_compensation",
    "refund_review",
    "seller_quality",
    "ops_sql_analysis",
    "policy_qa",
    "missing_context",
]


class LLMPlanStep(BaseModel):
    tool: str
    reason: str


class LLMRoutePlan(BaseModel):
    intent: AllowedIntent
    order_id: str | None = None
    seller_id: str | None = None
    rewritten_query: str = Field(min_length=1)
    policy_doc_types: list[str] = Field(default_factory=list)
    plan: list[LLMPlanStep] = Field(default_factory=list)
    summary: str = ""


class LLMFinalAnswer(BaseModel):
    answer: str = Field(min_length=1)


ROUTER_SYSTEM_PROMPT = """
You are the planner for OrderOps Agent, an ecommerce after-sales operations agent.
Return JSON only.

Allowed intents:
- delivery_compensation
- refund_review
- seller_quality
- ops_sql_analysis
- policy_qa
- missing_context

Allowed tools:
- get_order_summary
- search_policy
- check_delivery_compensation
- check_refund_eligibility
- create_support_ticket_draft
- sql_analysis
- analyze_seller_quality

Rules:
- Do not decide refund or compensation eligibility yourself.
- Use delivery_compensation when the user asks about late delivery compensation for a specific order.
- Use refund_review when the user asks about refund or return review for a specific order.
- Use seller_quality only for seller operational quality/risk analysis.
- Use ops_sql_analysis only when user_role is ops_admin and the request is aggregate operational analysis.
- Use policy_qa for general policy questions.
- If a delivery/refund request lacks an order_id, return missing_context.
- If a seller quality request lacks a seller_id, return missing_context.
- Plan must use only allowed tools.
- Plan must be a JSON array of objects, each object shaped like {"tool": "...", "reason": "..."}.
- rewritten_query should be suitable for RAG retrieval.
""".strip()


FINAL_SYSTEM_PROMPT = """
You are the final response writer for OrderOps Agent.
Return JSON only with one field: answer.

Write in concise Chinese.
Use the tool results and policy citations provided.
Do not change the deterministic business decision.
Do not invent refunds, compensation, payment actions, customer private data, or approval results.
Do not reveal hidden chain-of-thought.
Mention whether manual approval or a draft ticket is pending when present.
""".strip()


def call_llm_route_plan(client: LLMClient, state: AgentState) -> LLMRoutePlan:
    payload = {
        "message": state["message"],
        "user_role": state["user_role"],
        "known_order_id": state.get("order_id"),
        "known_seller_id": state.get("seller_id"),
    }
    raw = client.chat_json(ROUTER_SYSTEM_PROMPT, payload, trace_id=state.get("trace_id"))
    raw = normalize_route_payload(raw, fallback_query=state["message"])
    plan = LLMRoutePlan.model_validate(raw)
    return sanitize_route_plan(plan, state)


def call_llm_final_answer(client: LLMClient, state: AgentState) -> LLMFinalAnswer:
    payload = {
        "message": state["message"],
        "intent": state.get("intent"),
        "decision": state.get("decision"),
        "risk_level": state.get("risk_level"),
        "approval_required": state.get("approval_required"),
        "approval_status": state.get("approval_status"),
        "ticket_id": state.get("ticket_id"),
        "approval_id": state.get("approval_id"),
        "citations": state.get("citations", []),
        "tool_calls": state.get("tool_calls", []),
        "plan": state.get("plan", []),
        "order_summary": compact_mapping(state.get("order_summary")),
        "delivery_result": compact_mapping(state.get("delivery_result")),
        "refund_result": compact_mapping(state.get("refund_result")),
        "sql_result": compact_mapping(state.get("sql_result")),
        "seller_result": compact_mapping(state.get("seller_result")),
    }
    raw = client.chat_json(FINAL_SYSTEM_PROMPT, payload, trace_id=state.get("trace_id"))
    return LLMFinalAnswer.model_validate(raw)


def sanitize_route_plan(plan: LLMRoutePlan, state: AgentState) -> LLMRoutePlan:
    intent = plan.intent
    order_id = plan.order_id or state.get("order_id")
    seller_id = plan.seller_id or state.get("seller_id")
    if intent == "ops_sql_analysis" and state.get("user_role") != "ops_admin":
        intent = "policy_qa"
    if intent in {"delivery_compensation", "refund_review"} and not order_id:
        intent = "missing_context"
    if intent == "seller_quality" and not seller_id:
        intent = "missing_context"

    allowed_tools = {
        "get_order_summary",
        "search_policy",
        "check_delivery_compensation",
        "check_refund_eligibility",
        "create_support_ticket_draft",
        "sql_analysis",
        "analyze_seller_quality",
    }
    safe_steps = [step for step in plan.plan if step.tool in allowed_tools]
    return plan.model_copy(
        update={
            "intent": intent,
            "order_id": order_id,
            "seller_id": seller_id,
            "plan": safe_steps,
        }
    )


def normalize_route_payload(raw: dict[str, Any], fallback_query: str = "") -> dict[str, Any]:
    payload = dict(raw)
    plan = payload.get("plan")
    if not isinstance(plan, list):
        payload["plan"] = []
    else:
        normalized_plan: list[dict[str, str]] = []
        for item in plan:
            if isinstance(item, str):
                normalized_plan.append({"tool": item, "reason": "LLM selected this tool."})
            elif isinstance(item, dict):
                tool = str(item.get("tool") or item.get("name") or "")
                reason = str(item.get("reason") or item.get("description") or "LLM selected this tool.")
                if tool:
                    normalized_plan.append({"tool": tool, "reason": reason})
        payload["plan"] = normalized_plan

    if not payload.get("intent"):
        tool_names = {item["tool"] for item in payload.get("plan", [])}
        if "missing_context" in tool_names:
            payload["intent"] = "missing_context"
        elif "check_delivery_compensation" in tool_names:
            payload["intent"] = "delivery_compensation"
        elif "check_refund_eligibility" in tool_names:
            payload["intent"] = "refund_review"
        elif "analyze_seller_quality" in tool_names:
            payload["intent"] = "seller_quality"
        elif "sql_analysis" in tool_names:
            payload["intent"] = "ops_sql_analysis"
        elif "search_policy" in tool_names:
            payload["intent"] = "policy_qa"

    if not payload.get("rewritten_query"):
        payload["rewritten_query"] = str(payload.get("query") or fallback_query or "missing context")
    return payload


def compact_mapping(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    useful_keys = {
        "status",
        "order_id",
        "order_status",
        "delivered_late",
        "late_days",
        "total_payment_value",
        "seller_ids",
        "decision",
        "approval_required",
        "rationale",
        "risk_flags",
        "days_since_delivery",
        "row_count",
        "rows",
        "risk_level",
        "total_orders",
        "late_rate",
        "low_review_rate",
        "suggested_actions",
    }
    return {key: value[key] for key in useful_keys if key in value}


def validation_error_summary(exc: ValidationError) -> str:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(item) for item in first.get("loc", []))
    message = first.get("msg", "invalid LLM JSON")
    return f"{loc}: {message}" if loc else str(message)
