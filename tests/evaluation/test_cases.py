from pathlib import Path

from orderops_api.evaluation.cases import load_eval_cases


def test_load_seed_eval_cases_parses_expected_fields() -> None:
    cases = load_eval_cases(Path("data/eval/eval_cases_seed.csv"))

    assert len(cases) == 8
    delivery_case = next(case for case in cases if case.case_id == "EVAL-001")
    assert delivery_case.expected_intent == "delivery_compensation"
    assert delivery_case.expected_tools == [
        "get_order_summary",
        "search_policy",
        "check_delivery_compensation",
    ]
    assert delivery_case.expected_approval_required is True
    assert delivery_case.metric_tags == ["delivery", "tool", "rag", "approval"]


def test_seed_eval_cases_include_security_and_missing_context_controls() -> None:
    cases = {case.case_id: case for case in load_eval_cases(Path("data/eval/eval_cases_seed.csv"))}

    assert cases["EVAL-007"].expected_intent == "blocked"
    assert cases["EVAL-007"].expected_blocked is True
    assert cases["EVAL-008"].expected_intent == "missing_context"
    assert cases["EVAL-008"].expected_tools == []
