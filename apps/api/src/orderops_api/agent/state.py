from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field


AgentIntent = Literal[
    "delivery_compensation",
    "refund_review",
    "seller_quality",
    "ops_sql_analysis",
    "policy_qa",
    "blocked",
    "missing_context",
]


class AgentRunInput(BaseModel):
    session_id: str = "local-session"
    user_role: Literal["customer", "agent", "ops_admin"] = "agent"
    message: str = Field(min_length=1)
    order_id: str | None = None
    seller_id: str | None = None
    request_at: datetime | None = None
    trace_id: str | None = None
    auto_create_ticket: bool = True
    stream: bool = False


class AgentStep(BaseModel):
    step: int
    node: str
    status: str
    summary: str
    latency_ms: int | None = None


class AgentToolCall(BaseModel):
    tool: str
    status: str
    summary: str


class AgentLLMCall(BaseModel):
    node: str
    status: str
    model: str
    summary: str


class AgentPlanStep(BaseModel):
    step: int
    tool: str
    reason: str


class AgentCitation(BaseModel):
    ref: str
    title: str | None = None


class AgentRunOutput(BaseModel):
    trace_id: str
    intent: AgentIntent
    answer: str
    approval_required: bool = False
    approval_status: Literal["not_required", "pending", "approved", "rejected"] = "not_required"
    ticket_id: str | None = None
    approval_id: str | None = None
    decision: str | None = None
    risk_level: str | None = None
    rewritten_query: str | None = None
    plan: list[AgentPlanStep] = Field(default_factory=list)
    citations: list[AgentCitation] = Field(default_factory=list)
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
    llm_calls: list[AgentLLMCall] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)
    blocked_reason: str | None = None


class AgentState(TypedDict, total=False):
    input: dict[str, Any]
    trace_id: str
    message: str
    user_role: str
    order_id: str | None
    seller_id: str | None
    request_at: datetime | None
    auto_create_ticket: bool
    intent: str
    rewritten_query: str | None
    policy_doc_types: list[str]
    plan: list[dict[str, Any]]
    blocked: bool
    blocked_reason: str | None
    steps: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    llm_calls: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    approval_required: bool
    approval_status: str
    ticket_id: str | None
    approval_id: str | None
    decision: str | None
    risk_level: str | None
    answer: str
    order_summary: dict[str, Any] | None
    delivery_result: dict[str, Any] | None
    refund_result: dict[str, Any] | None
    policy_result: dict[str, Any] | None
    ticket_result: dict[str, Any] | None
    sql_result: dict[str, Any] | None
    seller_result: dict[str, Any] | None
    llm_route: dict[str, Any] | None


def initial_state(request: AgentRunInput) -> AgentState:
    trace_id = request.trace_id or f"agent-{uuid4().hex[:12]}"
    return {
        "input": request.model_dump(mode="json"),
        "trace_id": trace_id,
        "message": request.message,
        "user_role": request.user_role,
        "order_id": request.order_id,
        "seller_id": request.seller_id,
        "request_at": request.request_at,
        "auto_create_ticket": request.auto_create_ticket,
        "intent": "missing_context",
        "rewritten_query": None,
        "policy_doc_types": [],
        "plan": [],
        "blocked": False,
        "blocked_reason": None,
        "steps": [],
        "tool_calls": [],
        "llm_calls": [],
        "citations": [],
        "approval_required": False,
        "approval_status": "not_required",
        "ticket_id": None,
        "approval_id": None,
        "decision": None,
        "risk_level": None,
        "answer": "",
        "llm_route": None,
    }


def output_from_state(state: AgentState) -> AgentRunOutput:
    return AgentRunOutput(
        trace_id=state["trace_id"],
        intent=state.get("intent", "missing_context"),
        answer=state.get("answer", ""),
        approval_required=state.get("approval_required", False),
        approval_status=state.get("approval_status", "not_required"),
        ticket_id=state.get("ticket_id"),
        approval_id=state.get("approval_id"),
        decision=state.get("decision"),
        risk_level=state.get("risk_level"),
        rewritten_query=state.get("rewritten_query"),
        plan=[AgentPlanStep(**item) for item in state.get("plan", [])],
        citations=[AgentCitation(**item) for item in state.get("citations", [])],
        tool_calls=[AgentToolCall(**item) for item in state.get("tool_calls", [])],
        llm_calls=[AgentLLMCall(**item) for item in state.get("llm_calls", [])],
        steps=[AgentStep(**item) for item in state.get("steps", [])],
        blocked_reason=state.get("blocked_reason"),
    )


def append_step(
    state: AgentState,
    node: str,
    status: str,
    summary: str,
    latency_ms: int | None = None,
) -> None:
    steps = state.setdefault("steps", [])
    steps.append(
        {
            "step": len(steps) + 1,
            "node": node,
            "status": status,
            "summary": summary,
            "latency_ms": latency_ms,
        }
    )


def append_tool_call(state: AgentState, tool: str, status: str, summary: str) -> None:
    state.setdefault("tool_calls", []).append(
        {
            "tool": tool,
            "status": status,
            "summary": summary,
        }
    )


def append_llm_call(
    state: AgentState,
    node: str,
    status: str,
    model: str,
    summary: str,
) -> None:
    state.setdefault("llm_calls", []).append(
        {
            "node": node,
            "status": status,
            "model": model,
            "summary": summary,
        }
    )


def append_citation(state: AgentState, ref: str, title: str | None = None) -> None:
    citations = state.setdefault("citations", [])
    if any(item["ref"] == ref for item in citations):
        return
    citations.append({"ref": ref, "title": title})


def set_plan(state: AgentState, steps: list[tuple[str, str]]) -> None:
    state["plan"] = [
        {"step": index + 1, "tool": tool, "reason": reason}
        for index, (tool, reason) in enumerate(steps)
    ]
