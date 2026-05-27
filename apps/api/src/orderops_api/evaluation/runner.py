from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from orderops_api.agent.graph import AgentTools, run_agent
from orderops_api.agent.state import AgentRunInput
from orderops_api.evaluation.cases import EvalCase, load_eval_cases
from orderops_api.evaluation.metrics import (
    CaseEvalResult,
    EvalRunReport,
    RecordedToolCall,
    evaluate_case,
    summarize_results,
)
from orderops_api.llm.client import DisabledLLMClient
from orderops_api.tools.analysis_tools import analyze_seller_quality
from orderops_api.tools.delivery_tools import check_delivery_compensation
from orderops_api.tools.order_tools import get_order_summary
from orderops_api.tools.policy_tools import search_policy_tool
from orderops_api.tools.refund_tools import check_refund_eligibility
from orderops_api.tools.sql_tools import run_sql_analysis
from orderops_api.tools.ticket_tools import create_support_ticket_draft


class RecordingToolbox:
    def __init__(self, live_llm: bool, allow_writes: bool) -> None:
        self.live_llm = live_llm
        self.allow_writes = allow_writes
        self.calls: list[RecordedToolCall] = []

    def as_agent_tools(self) -> AgentTools:
        return AgentTools(
            get_order_summary=self.record("get_order_summary", get_order_summary),
            search_policy=self.record("search_policy", search_policy_tool),
            check_delivery_compensation=self.record(
                "check_delivery_compensation",
                check_delivery_compensation,
            ),
            check_refund_eligibility=self.record(
                "check_refund_eligibility",
                check_refund_eligibility,
            ),
            create_support_ticket_draft=self.record(
                "create_support_ticket_draft",
                create_support_ticket_draft,
            ),
            run_sql_analysis=self.record("sql_analysis", run_sql_analysis),
            analyze_seller_quality=self.record("seller_quality_analysis", analyze_seller_quality),
            llm_client=None if self.live_llm else DisabledLLMClient(),
        )

    def reset(self) -> None:
        self.calls = []

    def record(self, tool_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(request, *args, **kwargs):
            if tool_name == "create_support_ticket_draft" and not self.allow_writes:
                raise RuntimeError("Eval runner blocked write tool because allow_writes=False.")
            result = func(request, *args, **kwargs)
            status = getattr(result, "status", "")
            self.calls.append(
                RecordedToolCall(
                    tool=tool_name,
                    args=request.model_dump(mode="json") if hasattr(request, "model_dump") else {},
                    status=status,
                )
            )
            return result

        return wrapper


def run_eval(
    cases_path: Path,
    reports_dir: Path | None = None,
    live_llm: bool = False,
    allow_writes: bool = False,
    case_ids: set[str] | None = None,
    case_limit: int | None = None,
    write_reports: bool = True,
) -> EvalRunReport:
    cases = load_eval_cases(cases_path)
    available_case_ids = {case.case_id for case in cases}
    if case_ids:
        unknown_case_ids = sorted(case_ids.difference(available_case_ids))
        if unknown_case_ids:
            raise ValueError(f"Unknown eval case id(s): {', '.join(unknown_case_ids)}")
        cases = [case for case in cases if case.case_id in case_ids]
    if case_limit is not None:
        cases = cases[:case_limit]
    if not cases:
        raise ValueError("No eval cases selected.")

    run_id = f"eval-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
    toolbox = RecordingToolbox(live_llm=live_llm, allow_writes=allow_writes)
    results: list[CaseEvalResult] = []
    llm_success_count = 0
    llm_fallback_count = 0

    for case in cases:
        toolbox.reset()
        request = build_agent_request(case, run_id, allow_writes)
        started_at = perf_counter()
        output = run_agent(request, tools=toolbox.as_agent_tools())
        latency_ms = int((perf_counter() - started_at) * 1000)
        llm_success_count += sum(1 for call in output.llm_calls if call.status == "success")
        llm_fallback_count += sum(1 for call in output.llm_calls if call.status == "fallback")
        results.append(
            evaluate_case(
                case=case,
                output=output,
                recorded_tool_calls=list(toolbox.calls),
                latency_ms=latency_ms,
            )
        )

    report = summarize_results(
        run_id=run_id,
        cases_path=str(cases_path),
        live_llm=live_llm,
        allow_writes=allow_writes,
        results=results,
        llm_success_count=llm_success_count,
        llm_fallback_count=llm_fallback_count,
    )
    if reports_dir is not None and write_reports:
        write_eval_reports(report, reports_dir)
    return report


def build_agent_request(case: EvalCase, run_id: str, allow_writes: bool) -> AgentRunInput:
    return AgentRunInput(
        session_id=f"eval-{run_id}",
        user_role=case.user_role,
        message=case.message,
        order_id=case.order_id,
        seller_id=case.seller_id,
        request_at=case.request_at,
        trace_id=f"{run_id}-{case.case_id}",
        auto_create_ticket=case.auto_create_ticket and allow_writes,
    )


def write_eval_reports(report: EvalRunReport, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / "eval_report.json"
    markdown_path = reports_dir / "eval_report.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")


def render_markdown_report(report: EvalRunReport) -> str:
    summary = report.summary
    lines = [
        "# OrderOps Agent Eval Report",
        "",
        f"- Run ID: `{report.run_id}`",
        f"- Cases: `{summary.case_count}`",
        f"- Live LLM: `{report.live_llm}`",
        f"- Allow writes: `{report.allow_writes}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Task Success Rate | {summary.task_success_rate:.2%} |",
        f"| Intent Accuracy | {summary.intent_accuracy:.2%} |",
        f"| Tool Selection Recall | {summary.tool_selection_recall:.2%} |",
        f"| Tool Selection Exact Match | {summary.tool_selection_exact_match:.2%} |",
        f"| Tool Argument Accuracy | {summary.tool_argument_accuracy:.2%} |",
        f"| Retrieval Recall | {summary.retrieval_recall:.2%} |",
        f"| Decision Accuracy | {summary.decision_accuracy:.2%} |",
        f"| Approval Accuracy | {summary.approval_accuracy:.2%} |",
        f"| Risk Control Accuracy | {summary.risk_control_accuracy:.2%} |",
        f"| p95 Latency | {summary.p95_latency_ms} ms |",
        f"| Avg Latency | {summary.avg_latency_ms} ms |",
        f"| LLM Success Calls | {summary.llm_success_count} |",
        f"| LLM Fallback Calls | {summary.llm_fallback_count} |",
        "",
        "## Tag Success Rates",
        "",
        "| Tag | Success Rate |",
        "|---|---:|",
    ]
    for tag, value in summary.tag_success_rates.items():
        lines.append(f"| `{tag}` | {value:.2%} |")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Scenario | Success | Intent | Tools | Failures | Latency |",
            "|---|---|---:|---|---|---|---:|",
        ]
    )
    for result in report.cases:
        failures = ", ".join(result.failure_reasons) if result.failure_reasons else "-"
        tools = ", ".join(result.actual_tools) if result.actual_tools else "-"
        lines.append(
            f"| `{result.case_id}` | {result.scenario} | {result.task_success} | "
            f"{result.actual_intent} | {tools} | {failures} | {result.latency_ms} |"
        )
    lines.append("")
    return "\n".join(lines)
