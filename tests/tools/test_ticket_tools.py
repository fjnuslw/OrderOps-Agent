from orderops_api.tools.ticket_tools import (
    CreateSupportTicketDraftInput,
    approval_reason,
    make_approval_id,
    make_draft_ticket_id,
)


def test_draft_ticket_and_approval_ids_are_deterministic() -> None:
    ticket_id = make_draft_ticket_id("delivery_delay", "ORDER-1")

    assert ticket_id == make_draft_ticket_id("delivery_delay", "ORDER-1")
    assert ticket_id.startswith("DRAFT-")
    assert make_approval_id(ticket_id).startswith("APR-")


def test_approval_reason_includes_policy_refs() -> None:
    request = CreateSupportTicketDraftInput(
        order_id="ORDER-1",
        scenario="delivery_delay",
        title="Delivery delay review",
        description="Order arrived late.",
        expected_action="Review compensation.",
        policy_refs=["delivery_sla_policy_v1#s3"],
    )

    reason = approval_reason(request)

    assert "manual approval" in reason
    assert "delivery_sla_policy_v1#s3" in reason
