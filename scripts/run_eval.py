from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from orderops_api.evaluation.runner import run_eval


def main() -> None:
    parser = ArgumentParser(description="Run OrderOps Agent evaluation cases.")
    parser.add_argument("--cases", default="data/eval/eval_cases_seed.csv", help="Path to eval case CSV.")
    parser.add_argument("--reports-dir", default="reports/eval", help="Directory for JSON and Markdown reports.")
    parser.add_argument("--case-id", action="append", help="Run only the selected case id. Can be repeated.")
    parser.add_argument("--case-limit", type=int, help="Run only the first N cases after filtering.")
    parser.add_argument("--live-llm", action="store_true", help="Use the LLM configured in .env. Default disables LLM for reproducible evals.")
    parser.add_argument("--allow-writes", action="store_true", help="Allow eval cases to create draft tickets if requested.")
    parser.add_argument("--no-write-report", action="store_true", help="Do not write report files.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()

    try:
        report = run_eval(
            cases_path=Path(args.cases),
            reports_dir=Path(args.reports_dir),
            live_llm=args.live_llm,
            allow_writes=args.allow_writes,
            case_ids=set(args.case_id or []),
            case_limit=args.case_limit,
            write_reports=not args.no_write_report,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print(json.dumps(report.summary.model_dump(), ensure_ascii=False, indent=2))
        if not args.no_write_report:
            print(f"Reports written to: {args.reports_dir}")

    if report.summary.task_success_rate < 1.0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
