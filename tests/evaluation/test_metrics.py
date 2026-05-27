from orderops_api.agent.state import AgentCitation, AgentRunOutput, AgentToolCall
from orderops_api.evaluation.cases import EvalCase
from orderops_api.evaluation.metrics import RecordedToolCall, evaluate_case, summarize_results


def test_evaluate_case_checks_intent_tools_arguments_and_citations() -> None:
    case = EvalCase(
        case_id="EVAL-X",
        scenario="delivery_late",
        message="Check order",
        order_id="ORDER-1",
        expected_intent="delivery_compensation",
        expected_tools=["get_order_summary", "search_policy"],
        expected_decision="eligible_with_manual_approval",
        expected_approval_required=True,
        expected_citations=["delivery_sla_policy_v1"],
        expected_blocked=False,
        metric_tags=["delivery", "rag"],
    )
    output = AgentRunOutput(
        trace_id="trace-x",
        intent="delivery_compensation",
        answer="done",
        approval_required=True,
        decision="eligible_with_manual_approval",
        citations=[AgentCitation(ref="delivery_sla_policy_v1#s3")],
        tool_calls=[
            AgentToolCall(tool="get_order_summary", status="success", summary="ok"),
            AgentToolCall(tool="search_policy", status="success", summary="ok"),
        ],
    )
    recorded_tool_calls = [
        RecordedToolCall(tool="get_order_summary", args={"order_id": "ORDER-1"}, status="success")
    ]

    result = evaluate_case(case, output, recorded_tool_calls, latency_ms=123)

    assert result.task_success
    assert result.checks["intent"]
    assert result.checks["tool_arguments"]
    assert result.checks["retrieval"]
    assert result.checks["risk_control"]


def test_summarize_results_reports_tag_rates_and_latency() -> None:
    case = EvalCase(case_id="EVAL-X", scenario="missing", message="Need context")
    output = AgentRunOutput(trace_id="trace-x", intent="missing_context", answer="missing")
    result = evaluate_case(case, output, [], latency_ms=42)
    result.metric_tags = ["routing"]

    report = summarize_results(
        run_id="eval-test",
        cases_path="data/eval/eval_cases_seed.csv",
        live_llm=False,
        allow_writes=False,
        results=[result],
    )

    assert report.summary.case_count == 1
    assert report.summary.task_success_rate == 1.0
    assert report.summary.p95_latency_ms == 42
    assert report.summary.tag_success_rates == {"routing": 1.0}
