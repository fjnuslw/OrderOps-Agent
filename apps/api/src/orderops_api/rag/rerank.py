from __future__ import annotations

from dataclasses import replace
import json
from typing import Any, Protocol
from urllib import request

from orderops_api.core.config import Settings
from orderops_api.rag.embedding import tokenize_for_embedding


class Reranker(Protocol):
    def rerank(self, query: str, results: list[Any]) -> list[Any]:
        ...


class NoopReranker:
    def rerank(self, query: str, results: list[Any]) -> list[Any]:
        return results


class LexicalReranker:
    """Tiny local reranker based on token overlap.

    This is a placeholder for a real rerank model such as bge-reranker-v2-m3.
    """

    def rerank(self, query: str, results: list[Any]) -> list[Any]:
        query_tokens = set(tokenize_for_embedding(query))
        reranked: list[Any] = []
        for result in results:
            text_tokens = set(tokenize_for_embedding(result.text))
            overlap = len(query_tokens.intersection(text_tokens))
            rerank_score = result.score + overlap * 0.01
            reranked.append(replace(result, score=rerank_score))
        return sorted(reranked, key=lambda result: result.score, reverse=True)


class CrossEncoderReranker:
    """Local neural reranker for cross-encoder models such as bge-reranker."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for ORDEROPS_RERANK_PROVIDER=cross_encoder"
            ) from exc

        self.model_name = model_name
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, results: list[Any]) -> list[Any]:
        if not results:
            return results
        pairs = [(query, result.text) for result in results]
        scores = self._model.predict(pairs)
        reranked = [
            replace(result, score=float(score))
            for result, score in zip(results, scores, strict=True)
        ]
        return sorted(reranked, key=lambda result: result.score, reverse=True)


class HttpReranker:
    """Generic HTTP reranker using a Cohere/Jina-style response shape."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        api_path: str = "/rerank",
    ) -> None:
        if not base_url:
            raise ValueError("Rerank API base URL is required.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.api_path = api_path

    def rerank(self, query: str, results: list[Any]) -> list[Any]:
        if not results:
            return results
        payload = {
            "model": self.model,
            "query": query,
            "documents": [result.text for result in results],
            "top_n": len(results),
        }
        response = post_json(
            f"{self.base_url}{self.api_path}",
            payload,
            bearer_token=self.api_key,
        )
        return apply_http_rerank_response(results, response)


def build_reranker(settings: Settings, enabled: bool = True) -> Reranker:
    if not enabled:
        return NoopReranker()

    provider = settings.rerank_provider.strip().lower()
    if provider in {"none", "noop", "disabled"}:
        return NoopReranker()
    if provider == "lexical":
        return LexicalReranker()
    if provider == "cross_encoder":
        return CrossEncoderReranker(settings.rerank_model)
    if provider == "http":
        return HttpReranker(
            base_url=settings.rerank_api_base_url,
            api_key=settings.rerank_api_key,
            model=settings.rerank_model,
            api_path=settings.rerank_api_path,
        )
    raise ValueError(f"Unsupported rerank provider: {settings.rerank_provider}")


def apply_http_rerank_response(results: list[Any], response: dict[str, Any]) -> list[Any]:
    raw_items = response.get("results") or response.get("data")
    if not isinstance(raw_items, list):
        raise ValueError("Rerank API response must include a results or data list.")

    reranked: list[Any] = []
    for item in raw_items:
        index = int(item.get("index", item.get("document_index")))
        score = float(item.get("relevance_score", item.get("score")))
        reranked.append(replace(results[index], score=score))
    return sorted(reranked, key=lambda result: result.score, reverse=True)


def post_json(url: str, payload: dict[str, Any], bearer_token: str = "") -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    with request.urlopen(req, timeout=60) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)
