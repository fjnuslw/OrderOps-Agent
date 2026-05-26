from orderops_api.rag.search import PolicySearchResult
from orderops_api.tools.policy_tools import matches_doc_types, policy_result_to_citation


def test_matches_doc_types_accepts_policy_family_prefix() -> None:
    result = PolicySearchResult(
        doc_id="delivery_sla_policy_v1",
        section_id="delivery_sla_policy_v1#s2",
        score=0.9,
        text="policy text",
        title="2. 延迟送达判断",
        source_path="data/policies/delivery_sla_policy_v1.md",
        risk_level="medium",
    )

    assert matches_doc_types(result, ["delivery_sla_policy"])
    assert matches_doc_types(result, ["delivery_sla_policy_v1"])
    assert not matches_doc_types(result, ["refund_policy"])


def test_policy_result_to_citation_preserves_reference_fields() -> None:
    result = PolicySearchResult(
        doc_id="refund_policy_v1",
        section_id="refund_policy_v1#s1",
        score=0.8,
        text="refund policy",
        title="1. Refund",
        source_path="data/policies/refund_policy_v1.md",
        risk_level="high",
    )

    citation = policy_result_to_citation(result)

    assert citation.ref == "refund_policy_v1#s1"
    assert citation.model_dump()["ref"] == "refund_policy_v1#s1"
    assert citation.risk_level == "high"
