from orderops_api.rag.rerank import LexicalReranker
from orderops_api.rag.search import PolicySearchResult


def make_result(doc_id: str, text: str) -> PolicySearchResult:
    return PolicySearchResult(
        doc_id=doc_id,
        section_id=f"{doc_id}#s1",
        score=0.1,
        text=text,
        title="section",
        source_path="policy.md",
        risk_level="medium",
    )


def test_lexical_reranker_promotes_matching_policy_text() -> None:
    results = [
        make_result("refund_policy_v1", "退款 质量问题 人工复核"),
        make_result("delivery_sla_policy_v1", "延迟送达 超过预计日期 补偿 人工审批"),
    ]

    reranked = LexicalReranker().rerank("延迟送达如何补偿", results)

    assert reranked[0].doc_id == "delivery_sla_policy_v1"
