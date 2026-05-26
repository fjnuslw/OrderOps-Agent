# Policy RAG

Phase 5 indexes the demo policy documents under `data/policies/` and exposes a policy search path backed by Qdrant.

## Current Scope

Implemented:

- Markdown policy loading with frontmatter metadata.
- Section-based chunking.
- Configurable embedding provider abstraction.
- Qdrant collection creation and point upsert.
- `search_policy` retrieval with doc_id, section_id, score, text, source path, and risk level.
- Configurable rerank provider abstraction.

Not implemented yet:

- Agent tool integration.
- Hybrid lexical + vector retrieval.

## Current Retrieval Stack

```text
policy markdown
-> section chunks
-> embedding provider
-> Qdrant
-> vector search
-> optional rerank provider
-> top-k policy chunks
```

The default `HashingEmbeddingProvider` is intentionally small and deterministic. It is useful for building and testing the pipeline without downloading model weights, but it is not a real semantic embedding model.

The default `LexicalReranker` uses token overlap as a local placeholder. It is not a neural rerank model.

## Provider Options

### Default Local Development

```text
ORDEROPS_EMBEDDING_PROVIDER=hashing
ORDEROPS_EMBEDDING_MODEL=hashing-token-v1
ORDEROPS_EMBEDDING_DIMENSION=384
ORDEROPS_RERANK_PROVIDER=lexical
ORDEROPS_RERANK_MODEL=lexical-token-overlap-v1
```

This requires no model download and is the safest path for tests and CI-like local checks.

### Local e5 / BGE Models

Install optional local RAG dependencies:

```powershell
python -m pip install -e "apps/api[test,local-rag]"
```

Example multilingual e5-style config:

```text
ORDEROPS_EMBEDDING_PROVIDER=sentence_transformers
ORDEROPS_EMBEDDING_MODEL=intfloat/multilingual-e5-base
ORDEROPS_EMBEDDING_QUERY_PREFIX=query: 
ORDEROPS_EMBEDDING_DOCUMENT_PREFIX=passage: 
ORDEROPS_RERANK_PROVIDER=cross_encoder
ORDEROPS_RERANK_MODEL=BAAI/bge-reranker-v2-m3
```

Example BGE embedding config:

```text
ORDEROPS_EMBEDDING_PROVIDER=sentence_transformers
ORDEROPS_EMBEDDING_MODEL=BAAI/bge-m3
ORDEROPS_EMBEDDING_QUERY_PREFIX=
ORDEROPS_EMBEDDING_DOCUMENT_PREFIX=
ORDEROPS_RERANK_PROVIDER=cross_encoder
ORDEROPS_RERANK_MODEL=BAAI/bge-reranker-v2-m3
```

After changing embedding model or dimension, re-run indexing because Qdrant collection vectors must match the active embedding provider.

### OpenAI-Compatible Embedding API

```text
ORDEROPS_EMBEDDING_PROVIDER=openai_compatible
ORDEROPS_EMBEDDING_MODEL=text-embedding-3-small
ORDEROPS_EMBEDDING_DIMENSION=1536
ORDEROPS_EMBEDDING_API_BASE_URL=https://api.example.com
ORDEROPS_EMBEDDING_API_KEY=...
ORDEROPS_EMBEDDING_API_PATH=/v1/embeddings
```

Any service exposing an OpenAI-compatible `/v1/embeddings` response shape can be used.

### HTTP Rerank API

```text
ORDEROPS_RERANK_PROVIDER=http
ORDEROPS_RERANK_MODEL=bge-reranker
ORDEROPS_RERANK_API_BASE_URL=https://rerank.example.com
ORDEROPS_RERANK_API_KEY=...
ORDEROPS_RERANK_API_PATH=/rerank
```

The HTTP reranker expects a Cohere/Jina-style response containing item indices and scores, for example `results[].index` and `results[].relevance_score`.

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
