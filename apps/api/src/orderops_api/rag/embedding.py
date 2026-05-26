from __future__ import annotations

from collections import Counter
from hashlib import blake2b
import json
from math import sqrt
import re
from typing import Any, Literal, Protocol
from urllib import request

from orderops_api.core.config import Settings


EmbeddingInputType = Literal["query", "document"]


class EmbeddingProvider(Protocol):
    dimension: int

    def embed_text(self, text: str, input_type: EmbeddingInputType = "document") -> list[float]:
        ...

    def embed(self, text: str) -> list[float]:
        ...


class HashingEmbeddingProvider:
    """Small deterministic embedding provider for tests and fallback runs.

    This is not a semantic model. Real local RAG should use
    SentenceTransformersEmbeddingProvider or an embedding API.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_text(self, text: str, input_type: EmbeddingInputType = "document") -> list[float]:
        return self.embed(text)

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token, count in Counter(tokenize_for_embedding(text)).items():
            index = stable_hash(token) % self.dimension
            vector[index] += float(count)
        return normalize(vector)


class SentenceTransformersEmbeddingProvider:
    """Local semantic embedding provider for models such as e5 or bge-m3."""

    def __init__(
        self,
        model_name: str,
        query_prefix: str = "",
        document_prefix: str = "",
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for "
                "ORDEROPS_EMBEDDING_PROVIDER=sentence_transformers"
            ) from exc

        self.model_name = model_name
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self._model = SentenceTransformer(model_name)
        if hasattr(self._model, "get_embedding_dimension"):
            self.dimension = int(self._model.get_embedding_dimension())
        else:
            self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed_text(self, text: str, input_type: EmbeddingInputType = "document") -> list[float]:
        prefix = self.query_prefix if input_type == "query" else self.document_prefix
        vector = self._model.encode(
            prefix + text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [float(value) for value in vector.tolist()]

    def embed(self, text: str) -> list[float]:
        return self.embed_text(text, input_type="document")


class OpenAICompatibleEmbeddingProvider:
    """Embedding provider for OpenAI-compatible `/v1/embeddings` APIs."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        dimension: int,
        api_path: str = "/v1/embeddings",
        query_prefix: str = "",
        document_prefix: str = "",
    ) -> None:
        if not base_url:
            raise ValueError("Embedding API base URL is required.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.api_path = api_path
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix

    def embed_text(self, text: str, input_type: EmbeddingInputType = "document") -> list[float]:
        prefix = self.query_prefix if input_type == "query" else self.document_prefix
        payload = {
            "model": self.model,
            "input": prefix + text,
        }
        response = post_json(
            f"{self.base_url}{self.api_path}",
            payload,
            bearer_token=self.api_key,
        )
        return extract_openai_embedding(response)

    def embed(self, text: str) -> list[float]:
        return self.embed_text(text, input_type="document")


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.embedding_provider.strip().lower()
    if provider == "hashing":
        return HashingEmbeddingProvider(dimension=settings.embedding_dimension)
    if provider == "sentence_transformers":
        return SentenceTransformersEmbeddingProvider(
            model_name=settings.embedding_model,
            query_prefix=settings.embedding_query_prefix,
            document_prefix=settings.embedding_document_prefix,
        )
    if provider == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding_api_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
            api_path=settings.embedding_api_path,
            query_prefix=settings.embedding_query_prefix,
            document_prefix=settings.embedding_document_prefix,
        )
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")


def extract_openai_embedding(response: dict[str, Any]) -> list[float]:
    try:
        embedding = response["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Embedding API response must include data[0].embedding") from exc
    return [float(value) for value in embedding]


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


def stable_hash(value: str) -> int:
    digest = blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def tokenize_for_embedding(text: str) -> list[str]:
    normalized = text.lower()
    latin_tokens = re.findall(r"[a-z0-9_]+", normalized)
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    cjk_bigrams = [left + right for left, right in zip(cjk_chars, cjk_chars[1:])]
    return latin_tokens + cjk_chars + cjk_bigrams


def normalize(vector: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
