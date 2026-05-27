from pathlib import Path

import pytest

from orderops_api.evaluation.runner import run_eval


def test_run_eval_defaults_to_no_live_llm_and_no_writes() -> None:
    report = run_eval(
        cases_path=Path("data/eval/eval_cases_seed.csv"),
        live_llm=False,
        allow_writes=False,
        case_ids={"EVAL-008"},
        write_reports=False,
    )

    assert report.live_llm is False
    assert report.allow_writes is False
    assert report.summary.case_count == 1
    assert report.summary.task_success_rate == 1.0
    assert report.summary.llm_success_count == 0
    assert report.cases[0].actual_tools == []


def test_run_eval_rejects_unknown_case_id() -> None:
    with pytest.raises(ValueError, match="Unknown eval case"):
        run_eval(
            cases_path=Path("data/eval/eval_cases_seed.csv"),
            case_ids={"EVAL-DOES-NOT-EXIST"},
            write_reports=False,
        )
