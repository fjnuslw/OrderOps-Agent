# OrderOps Agent

OrderOps Agent is an ecommerce after-sales operations agent demo. It is designed to show an end-to-end agent workflow that combines policy retrieval, structured order data, tool calling, workflow orchestration, evaluation, and backend service design.

This repository currently contains the project specification and starter assets for Codex-driven implementation.

## Project Materials

- `docs/PROJECT_SPEC.md` - full product and engineering specification
- `docs/BUILD_PLAN.md` - practical staged build plan
- `docs/LOCAL_INFRA.md` - local PostgreSQL, Redis, and Qdrant guide
- `docs/ETL.md` - Olist CSV import guide
- `docs/SUPPORT_TICKETS.md` - derived support ticket generation guide
- `docs/POLICY_RAG.md` - policy document indexing and search guide
- `docs/CODEX_TASKS.md` - staged implementation tasks for Codex
- `docs/API_CONTRACT.yaml` - initial API contract
- `data/policies/` - versioned policy documents for RAG
- `data/eval/eval_cases_seed.csv` - seed evaluation cases
- `data/sql/target_schema.sql` - target database schema draft

## Development

Run tests:

```powershell
python -m pytest
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

Index and search policy documents:

```powershell
python scripts/index_policies.py
python scripts/search_policy.py "延迟送达如何补偿" --top-k 5
```

RAG defaults to a deterministic local embedding provider and lexical reranker for reproducible development. See `docs/POLICY_RAG.md` for local e5/BGE and API-compatible embedding/rerank configuration.

## Notes

The raw Olist dataset is intentionally ignored by Git through `data/raw/*`. Keep downloaded CSV files local and cite the Kaggle source when publishing derived analysis or results.
