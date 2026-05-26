from __future__ import annotations

from dataclasses import replace

from orderops_api.rag.embedding import tokenize_for_embedding
from orderops_api.rag.search import PolicySearchResult


class LexicalReranker:
    """Tiny local reranker based on token overlap.

    This is a placeholder for a real rerank model such as bge-reranker-v2-m3.
    """

    def rerank(self, query: str, results: list[PolicySearchResult]) -> list[PolicySearchResult]:
        query_tokens = set(tokenize_for_embedding(query))
        reranked: list[PolicySearchResult] = []
        for result in results:
            text_tokens = set(tokenize_for_embedding(result.text))
            overlap = len(query_tokens.intersection(text_tokens))
            rerank_score = result.score + overlap * 0.01
            reranked.append(replace(result, score=rerank_score))
        return sorted(reranked, key=lambda result: result.score, reverse=True)
