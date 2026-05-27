from orderops_api.tools.approval_tools import (
    DecideApprovalInput,
    approval_status_for_action,
    build_decision_reason,
    ticket_status_for_approval,
)


def test_approval_action_maps_to_ticket_status() -> None:
    assert approval_status_for_action("approve") == "approved"
    assert approval_status_for_action("reject") == "rejected"
    assert ticket_status_for_approval("approve") == "open"
    assert ticket_status_for_approval("reject") == "rejected"


def test_build_decision_reason_preserves_existing_reason() -> None:
    request = DecideApprovalInput(
        approval_id="APR-1",
        action="approve",
        decided_by="ops",
        decision_reason="Evidence is sufficient.",
    )

    reason = build_decision_reason("Original reason.", request)

    assert "Original reason." in reason
    assert "Decision by ops: approve" in reason
    assert "Evidence is sufficient" in reason
