from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any
from urllib import request
from urllib.error import HTTPError
from uuid import NAMESPACE_URL, uuid5

from orderops_api.rag.embedding import EmbeddingProvider
from orderops_api.rag.policies import PolicyChunk


class QdrantHttpClient:
    def __init__(self, base_url: str, collection_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.collection_name = collection_name

    def recreate_collection(self, vector_size: int) -> None:
        self._request("DELETE", f"/collections/{self.collection_name}", allow_404=True)
        self._request(
            "PUT",
            f"/collections/{self.collection_name}",
            {
                "vectors": {
                    "size": vector_size,
                    "distance": "Cosine",
                }
            },
        )

    def upsert_chunks(
        self,
        chunks: list[PolicyChunk],
        embedding_provider: EmbeddingProvider,
    ) -> None:
        points = []
        for chunk in chunks:
            points.append(
                {
                    "id": str(uuid5(NAMESPACE_URL, chunk.chunk_id)),
                    "vector": embedding_provider.embed(chunk.text),
                    "payload": asdict(chunk),
                }
            )
        self._request(
            "PUT",
            f"/collections/{self.collection_name}/points?wait=true",
            {"points": points},
        )

    def search(self, vector: list[float], limit: int) -> list[dict[str, Any]]:
        response = self._request(
            "POST",
            f"/collections/{self.collection_name}/points/search",
            {
                "vector": vector,
                "limit": limit,
                "with_payload": True,
                "with_vector": False,
            },
        )
        return response["result"]

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        allow_404: bool = False,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            if allow_404 and exc.code == 404:
                return {}
            raise
        if not body:
            return {}
        return json.loads(body)
