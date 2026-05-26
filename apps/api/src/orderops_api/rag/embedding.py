from __future__ import annotations

from collections import Counter
from hashlib import blake2b
from math import sqrt
import re
from typing import Protocol


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, text: str) -> list[float]:
        ...


class HashingEmbeddingProvider:
    """Small deterministic embedding provider for local development.

    This is not a semantic model. It gives us a stable vector interface without
    downloading model weights, so the RAG pipeline can be built and tested first.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token, count in Counter(tokenize_for_embedding(text)).items():
            index = stable_hash(token) % self.dimension
            vector[index] += float(count)
        return normalize(vector)


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
