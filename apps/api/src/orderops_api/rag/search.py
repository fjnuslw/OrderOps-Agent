from __future__ import annotations

from dataclasses import dataclass

from orderops_api.core.config import get_settings
from orderops_api.rag.embedding import HashingEmbeddingProvider
from orderops_api.rag.qdrant import QdrantHttpClient


@dataclass(frozen=True)
class PolicySearchResult:
    doc_id: str
    section_id: str
    score: float
    text: str
    title: str
    source_path: str
    risk_level: str


def search_policy(query: str, top_k: int = 5, rerank: bool = True) -> list[PolicySearchResult]:
    settings = get_settings()
    embedding_provider = HashingEmbeddingProvider()
    client = QdrantHttpClient(settings.qdrant_url, settings.qdrant_collection)
    query_vector = embedding_provider.embed(query)
    raw_results = client.search(query_vector, top_k * 4 if rerank else top_k)
    results = [search_result_from_qdrant(item) for item in raw_results]

    if rerank:
        from orderops_api.rag.rerank import LexicalReranker

        results = LexicalReranker().rerank(query, results)
    return results[:top_k]


def search_result_from_qdrant(item: dict) -> PolicySearchResult:
    payload = item["payload"]
    return PolicySearchResult(
        doc_id=payload["doc_id"],
        section_id=payload["section_id"],
        score=float(item["score"]),
        text=payload["text"],
        title=payload["title"],
        source_path=payload["source_path"],
        risk_level=payload["risk_level"],
    )
