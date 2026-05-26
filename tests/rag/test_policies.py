from pathlib import Path

from orderops_api.rag.policies import load_policy_chunks, load_policy_document


def test_load_policy_document_reads_frontmatter() -> None:
    document = load_policy_document(Path("data/policies/delivery_sla_policy_v1.md"))

    assert document.doc_id == "delivery_sla_policy_v1"
    assert document.risk_level == "medium"
    assert document.title == "物流时效与赔付政策 v1"


def test_policy_chunks_include_delivery_delay_section() -> None:
    chunks = load_policy_chunks(Path("data/policies"))

    matching = [
        chunk
        for chunk in chunks
        if chunk.doc_id == "delivery_sla_policy_v1" and "延迟送达判断" in chunk.title
    ]

    assert matching
    assert "超过 2 个自然日" in matching[0].text
