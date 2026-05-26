# Policy RAG

Phase 5 indexes the demo policy documents under `data/policies/` and exposes a policy search path backed by Qdrant.

## Current Scope

Implemented:

- Markdown policy loading with frontmatter metadata.
- Section-based chunking.
- Deterministic local embedding provider.
- Qdrant collection creation and point upsert.
- `search_policy` retrieval with doc_id, section_id, score, text, source path, and risk level.
- Lightweight lexical reranking.

Not implemented yet:

- Real semantic embedding model.
- Real neural reranker model.
- Agent tool integration.

## Current Retrieval Stack

```text
policy markdown
-> section chunks
-> HashingEmbeddingProvider
-> Qdrant
-> vector search
-> LexicalReranker
-> top-k policy chunks
```

`HashingEmbeddingProvider` is intentionally small and deterministic. It is useful for building the pipeline without downloading model weights, but it is not a real semantic embedding model.

`LexicalReranker` uses token overlap as a local placeholder. It is not a neural rerank model.

## Future Model Upgrade

Recommended local model path:

```text
embedding: BAAI/bge-m3
rerank: BAAI/bge-reranker-v2-m3
```

The code is structured around provider interfaces so the local hashing provider can later be replaced without rewriting the indexing/search flow.

## Index Policies

Start Qdrant:

```powershell
docker compose up -d
```

Index policy chunks:

```powershell
conda activate orderops-agent
python scripts/index_policies.py
```

Latest local result:

```text
indexed_policy_chunks: 18
```

## Search Policies

```powershell
python scripts/search_policy.py "延迟送达如何补偿" --top-k 5
```

Latest local smoke check top result:

```text
delivery_sla_policy_v1
delivery_sla_policy_v1#s2
2. 延迟送达判断
```

The retrieved text includes the rule that delivery later than the estimated date by more than 2 natural days can enter delayed compensation review.
