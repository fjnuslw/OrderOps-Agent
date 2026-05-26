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
-> bge-m3 embedding provider
-> Qdrant
-> vector search
-> bge-reranker-v2-m3 cross-encoder rerank
-> top-k policy chunks
```

The real local stack for this project is:

- embedding: `BAAI/bge-m3`
- rerank: `BAAI/bge-reranker-v2-m3`
- vector store: Qdrant collection `orderops_policies`

`HashingEmbeddingProvider` and `LexicalReranker` remain in the codebase only for fast unit tests and no-model fallback checks. They are not the intended policy RAG runtime.

## Local BGE Models

Install optional local RAG dependencies:

```powershell
python -m pip install -e "apps/api[test,local-rag]"
```

The current machine keeps model weights outside Git under `D:\models`:

```text
ORDEROPS_EMBEDDING_PROVIDER=sentence_transformers
ORDEROPS_EMBEDDING_MODEL=D:\models\bge-m3
ORDEROPS_EMBEDDING_DIMENSION=1024
ORDEROPS_EMBEDDING_QUERY_PREFIX=
ORDEROPS_EMBEDDING_DOCUMENT_PREFIX=
ORDEROPS_RERANK_PROVIDER=cross_encoder
ORDEROPS_RERANK_MODEL=D:\models\bge-reranker-v2-m3
```

The public `.env.example` uses HuggingFace model ids instead of local absolute paths. The private `.env` can point to local model directories to keep the runtime offline and reproducible on this machine.

After changing embedding model or dimension, re-run indexing because Qdrant collection vectors must match the active embedding provider.

## Download Models

If the model directories are missing, download them from HuggingFace into `D:\models`:

```powershell
python scripts/download_hf_snapshot.py BAAI/bge-m3 D:\models\bge-m3 --ignore "imgs/*" --ignore "onnx/*" --ignore "*.jpg" --ignore "*.webp"
python scripts/download_hf_snapshot.py BAAI/bge-reranker-v2-m3 D:\models\bge-reranker-v2-m3 --ignore "assets/*" --ignore "images/*"
```

The script downloads the model repository files with resume support and skips large non-runtime assets when ignore patterns are provided.

## Provider Options

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

Latest local smoke check used `D:\models\bge-m3` plus `D:\models\bge-reranker-v2-m3`.

Top result:

```text
0.9325 delivery_sla_policy_v1 delivery_sla_policy_v1#s2 2. 延迟送达判断
```

The retrieved text includes the rule that delivery later than the estimated date by more than 2 natural days can enter delayed compensation review.
