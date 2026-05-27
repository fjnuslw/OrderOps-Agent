from orderops_api.core.config import settings_from_env
from orderops_api.rag.rerank import (
    HttpReranker,
    LexicalReranker,
    NoopReranker,
    apply_http_rerank_response,
    build_reranker,
)
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


def test_reranker_factory_defaults_to_lexical() -> None:
    settings = settings_from_env({})
    reranker = build_reranker(settings)

    assert isinstance(reranker, LexicalReranker)
    assert reranker is build_reranker(settings)


def test_reranker_factory_can_disable_rerank() -> None:
    reranker = build_reranker(settings_from_env({}), enabled=False)

    assert isinstance(reranker, NoopReranker)


def test_http_reranker_factory() -> None:
    reranker = build_reranker(
        settings_from_env(
            {
                "ORDEROPS_RERANK_PROVIDER": "http",
                "ORDEROPS_RERANK_MODEL": "bge-reranker",
                "ORDEROPS_RERANK_API_BASE_URL": "https://rerank.example.test",
            }
        )
    )

    assert isinstance(reranker, HttpReranker)


def test_apply_http_rerank_response_uses_indices_and_scores() -> None:
    results = [
        make_result("refund_policy_v1", "退款"),
        make_result("delivery_sla_policy_v1", "延迟送达"),
    ]

    reranked = apply_http_rerank_response(
        results,
        {
            "results": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.1},
            ]
        },
    )

    assert reranked[0].doc_id == "delivery_sla_policy_v1"
    assert reranked[0].score == 0.9
