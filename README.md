# OrderOps Agent

OrderOps Agent is an ecommerce after-sales operations agent demo. It is designed to show an end-to-end agent workflow that combines policy retrieval, structured order data, tool calling, workflow orchestration, evaluation, and backend service design.

This repository is being built phase by phase as a runnable learning project, not just a specification folder.

## Project Materials

- `docs/PROJECT_SPEC.md` - full product and engineering specification
- `docs/BUILD_PLAN.md` - practical staged build plan
- `docs/PHASE_STATUS.md` - completed phase status and gap checklist
- `docs/LOCAL_INFRA.md` - local PostgreSQL, Redis, and Qdrant guide
- `docs/ETL.md` - Olist CSV import guide
- `docs/SUPPORT_TICKETS.md` - derived support ticket generation guide
- `docs/POLICY_RAG.md` - policy document indexing and search guide
- `docs/BUSINESS_TOOLS.md` - controlled business tool guide
- `docs/AGENT_WORKFLOW.md` - LangGraph workflow guide
- `docs/CODEX_TASKS.md` - staged implementation tasks for Codex
- `docs/API_CONTRACT.yaml` - initial API contract
- `data/policies/` - versioned policy documents for RAG
- `data/eval/eval_cases_seed.csv` - seed evaluation cases
- `data/sql/target_schema.sql` - target database schema draft

## Development

Run tests:

```powershell
python -m pip install -e "apps/api[test,local-rag,agent]"
python -m pytest
```

Run phase smoke checks:

```powershell
python scripts/phase_smoke_check.py
```

Run the API locally:

```powershell
conda activate orderops-agent
python -m orderops_api
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

Start local infrastructure:

```powershell
docker compose up -d
```

See `docs/LOCAL_INFRA.md` for the service list and configuration flow.

## Dataset

This project uses the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), a public anonymized ecommerce dataset with about 100k Brazilian marketplace orders from 2016 to 2018.

License: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

Raw CSV files are not committed to this repository. Download them locally into `data/raw/`:

```powershell
Invoke-WebRequest -Uri 'https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce' -OutFile 'data/raw/brazilian-ecommerce.zip'
Expand-Archive 'data/raw/brazilian-ecommerce.zip' -DestinationPath 'data/raw' -Force
```

The current ETL path imports these core files:

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
olist_customers_dataset.csv
```

Load the local PostgreSQL schema and import data:

```powershell
conda activate orderops-agent
python scripts/db_bootstrap.py
python scripts/etl_olist.py --replace
```

Generate derived support tickets:

```powershell
python scripts/generate_support_tickets.py --replace
```

## Policy RAG

The real local RAG path uses `bge-m3` for embedding and `bge-reranker-v2-m3` for reranking. On this machine the private `.env` points to:

```text
D:\models\bge-m3
D:\models\bge-reranker-v2-m3
```

Download missing model files:

```powershell
python scripts/download_hf_snapshot.py BAAI/bge-m3 D:\models\bge-m3 --ignore "imgs/*" --ignore "onnx/*" --ignore "*.jpg" --ignore "*.webp"
python scripts/download_hf_snapshot.py BAAI/bge-reranker-v2-m3 D:\models\bge-reranker-v2-m3 --ignore "assets/*" --ignore "images/*"
```

Index and search policy documents:

```powershell
python scripts/index_policies.py
python scripts/search_policy.py "延迟送达如何补偿" --top-k 5
```

`HashingEmbeddingProvider` and `LexicalReranker` are kept only for fast tests and no-model fallback checks. See `docs/POLICY_RAG.md` for local model and API-compatible embedding/rerank configuration.

## Business Tools

Phase 6 exposes the first controlled tool APIs:

```powershell
POST http://127.0.0.1:8000/api/tools/order-summary
POST http://127.0.0.1:8000/api/tools/policy-search
POST http://127.0.0.1:8000/api/tools/delivery-compensation
POST http://127.0.0.1:8000/api/tools/refund-eligibility
POST http://127.0.0.1:8000/api/tools/support-ticket-draft
POST http://127.0.0.1:8000/api/tools/approval-decision
POST http://127.0.0.1:8000/api/tools/sql-analysis
POST http://127.0.0.1:8000/api/tools/seller-quality
```

See `docs/BUSINESS_TOOLS.md` for request examples and current decision rules.

## Agent Workflow

Phase 7 exposes the LangGraph agent workflow:

```powershell
POST http://127.0.0.1:8000/api/agent/run
POST http://127.0.0.1:8000/api/chat
```

Run one local case from the command line:

```powershell
python scripts/run_agent_case.py "订单 1b3190b2dfa9d789e1f14c05b647a14a 延迟送达，是否可以赔付？" --order-id 1b3190b2dfa9d789e1f14c05b647a14a
```

The response includes intent, decision, approval state, citations, tool calls, a visible plan, and step trace. See `docs/AGENT_WORKFLOW.md`.

Optional DeepSeek LLM routing and final answer composition can be enabled in your private `.env`:

```powershell
ORDEROPS_LLM_PROVIDER=deepseek
ORDEROPS_LLM_API_BASE_URL=https://api.deepseek.com
ORDEROPS_LLM_API_KEY=your_key_here
ORDEROPS_LLM_MODEL=deepseek-v4-pro
```

When no LLM key is configured, the workflow falls back to the deterministic router and composer.

SiliconFlow can also be used through the same OpenAI-compatible client:

```powershell
ORDEROPS_LLM_PROVIDER=siliconflow
ORDEROPS_LLM_API_BASE_URL=https://api.siliconflow.com/v1
ORDEROPS_LLM_API_KEY=your_siliconflow_key
ORDEROPS_LLM_MODEL=Qwen/Qwen2.5-72B-Instruct
```

## Notes

The raw Olist dataset is intentionally ignored by Git through `data/raw/*`. Keep downloaded CSV files local and cite the Kaggle source when publishing derived analysis or results.
