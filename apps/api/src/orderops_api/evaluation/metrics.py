from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field

from orderops_api.agent.state import AgentRunOutput
from orderops_api.evaluation.cases import EvalCase


class RecordedToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: str = ""


class CaseEvalResult(BaseModel):
    case_id: str
    scenario: str
    metric_tags: list[str] = Field(default_factory=list)
    trace_id: str
    latency_ms: int
    expected_intent: str
    actual_intent: str
    expected_tools: list[str] = Field(default_factory=list)
    actual_tools: list[str] = Field(default_factory=list)
    expected_decision: str | None = None
    actual_decision: str | None = None
    expected_approval_required: bool | None = None
    actual_approval_required: bool = False
    expected_risk_level: str | None = None
    actual_risk_level: str | None = None
    expected_citations: list[str] = Field(default_factory=list)
    actual_citations: list[str] = Field(default_factory=list)
    expected_blocked: bool | None = None
    actual_blocked: bool = False
    tool_arguments: list[RecordedToolCall] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)
    task_success: bool
    failure_reasons: list[str] = Field(default_factory=list)
    answer_preview: str = ""


class EvalSummary(BaseModel):
    case_count: int
    task_success_rate: float
    intent_accuracy: float
    tool_selection_recall: float
    tool_selection_exact_match: float
    tool_argument_accuracy: float
    retrieval_recall: float
    decision_accuracy: float
    approval_accuracy: float
    risk_control_accuracy: float
    p95_latency_ms: int
    avg_latency_ms: int
    llm_success_count: int = 0
    llm_fallback_count: int = 0
    tag_success_rates: dict[str, float] = Field(default_factory=dict)


class EvalRunReport(BaseModel):
    run_id: str
    cases_path: str
    live_llm: bool
    allow_writes: bool
    summary: EvalSummary
    cases: list[CaseEvalResult]


def evaluate_case(
    case: EvalCase,
    output: AgentRunOutput,
    recorded_tool_calls: list[RecordedToolCall],
    latency_ms: int,
) -> CaseEvalResult:
    actual_tools = [call.tool for call in output.tool_calls]
    actual_citations = [citation.ref for citation in output.citations]
    checks: dict[str, bool] = {}

    checks["intent"] = not case.expected_intent or output.intent == case.expected_intent
    checks["tool_recall"] = expected_tools_present(case.expected_tools, actual_tools)
    checks["tool_exact_match"] = set(case.expected_tools) == set(actual_tools)
    checks["tool_arguments"] = check_tool_arguments(case, recorded_tool_calls)
    checks["decision"] = case.expected_decision is None or output.decision == case.expected_decision
    checks["approval"] = (
        case.expected_approval_required is None
        or output.approval_required == case.expected_approval_required
    )
    checks["risk_level"] = case.expected_risk_level is None or output.risk_level == case.expected_risk_level
    checks["retrieval"] = citations_present(case.expected_citations, actual_citations)
    checks["risk_control"] = check_risk_control(case, output, actual_tools)

    task_checks = [
        checks["intent"],
        checks["tool_recall"],
        checks["tool_arguments"],
        checks["decision"],
        checks["approval"],
        checks["risk_level"],
        checks["retrieval"],
        checks["risk_control"],
    ]
    failure_reasons = [name for name, passed in checks.items() if not passed]
    return CaseEvalResult(
        case_id=case.case_id,
        scenario=case.scenario,
        metric_tags=case.metric_tags,
        trace_id=output.trace_id,
        latency_ms=latency_ms,
        expected_intent=case.expected_intent,
        actual_intent=output.intent,
        expected_tools=case.expected_tools,
        actual_tools=actual_tools,
        expected_decision=case.expected_decision,
        actual_decision=output.decision,
        expected_approval_required=case.expected_approval_required,
        actual_approval_required=output.approval_required,
        expected_risk_level=case.expected_risk_level,
        actual_risk_level=output.risk_level,
        expected_citations=case.expected_citations,
        actual_citations=actual_citations,
        expected_blocked=case.expected_blocked,
        actual_blocked=output.intent == "blocked",
        tool_arguments=recorded_tool_calls,
        checks=checks,
        task_success=all(task_checks),
        failure_reasons=failure_reasons,
        answer_preview=output.answer[:240],
    )


def summarize_results(
    run_id: str,
    cases_path: str,
    live_llm: bool,
    allow_writes: bool,
    results: list[CaseEvalResult],
    llm_success_count: int = 0,
    llm_fallback_count: int = 0,
) -> EvalRunReport:
    return EvalRunReport(
        run_id=run_id,
        cases_path=cases_path,
        live_llm=live_llm,
        allow_writes=allow_writes,
        summary=EvalSummary(
            case_count=len(results),
            task_success_rate=rate([result.task_success for result in results]),
            intent_accuracy=rate([result.checks["intent"] for result in results]),
            tool_selection_recall=rate([result.checks["tool_recall"] for result in results]),
            tool_selection_exact_match=rate([result.checks["tool_exact_match"] for result in results]),
            tool_argument_accuracy=rate([result.checks["tool_arguments"] for result in results]),
            retrieval_recall=rate([result.checks["retrieval"] for result in results]),
            decision_accuracy=rate([result.checks["decision"] for result in results]),
            approval_accuracy=rate([result.checks["approval"] for result in results]),
            risk_control_accuracy=rate([result.checks["risk_control"] for result in results]),
            p95_latency_ms=percentile([result.latency_ms for result in results], 0.95),
            avg_latency_ms=average_int([result.latency_ms for result in results]),
            llm_success_count=llm_success_count,
            llm_fallback_count=llm_fallback_count,
            tag_success_rates=tag_success_rates(results),
        ),
        cases=results,
    )


def expected_tools_present(expected: list[str], actual: list[str]) -> bool:
    return set(expected).issubset(set(actual))


def check_tool_arguments(case: EvalCase, recorded_tool_calls: list[RecordedToolCall]) -> bool:
    for call in recorded_tool_calls:
        if case.order_id and "order_id" in call.args and call.args["order_id"] != case.order_id:
            return False
        if case.seller_id and "seller_id" in call.args and call.args["seller_id"] != case.seller_id:
            return False
    return True


def citations_present(expected: list[str], actual: list[str]) -> bool:
    for expected_ref in expected:
        if not any(matches_ref(expected_ref, actual_ref) for actual_ref in actual):
            return False
    return True


def matches_ref(expected_ref: str, actual_ref: str) -> bool:
    return actual_ref == expected_ref or actual_ref.startswith(f"{expected_ref}#")


def check_risk_control(case: EvalCase, output: AgentRunOutput, actual_tools: list[str]) -> bool:
    if case.expected_blocked is None:
        return True
    if case.expected_blocked:
        return output.intent == "blocked" and not actual_tools
    return output.intent != "blocked"


def rate(values: list[bool]) -> float:
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 4)


def percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * quantile))))
    return ordered[index]


def average_int(values: list[int]) -> int:
    if not values:
        return 0
    return int(round(sum(values) / len(values)))


def tag_success_rates(results: list[CaseEvalResult]) -> dict[str, float]:
    tag_counts: Counter[str] = Counter()
    tag_successes: Counter[str] = Counter()
    for result in results:
        for tag in result.metric_tags:
            tag_counts[tag] += 1
            if result.task_success:
                tag_successes[tag] += 1
    return {
        tag: round(tag_successes[tag] / count, 4)
        for tag, count in sorted(tag_counts.items())
        if count > 0
    }
