# Phase Status

本文档是当前项目阶段的收束视图。它不替代 `docs/BUILD_PLAN.md`，而是方便快速回答三个问题：已经完成什么、如何验证、还有什么缺口。

## Summary

| Phase | Status | Main Output | Verification |
|---|---|---|---|
| Phase 0 | Done | GitHub-ready repository baseline | README, `.gitignore`, staged docs |
| Phase 1 | Done | FastAPI backend scaffold | `GET /health`, API tests |
| Phase 2 | Done | Local Postgres, Redis, Qdrant | `docker compose ps`, config tests |
| Phase 3 | Done | Olist ETL into PostgreSQL | table counts, ETL tests |
| Phase 4 | Done | Derived support tickets | scenario counts, ticket tests |
| Phase 5 | Done | Real local BGE policy RAG | Qdrant 1024-dim collection, policy search smoke |
| Phase 6 | Done | Controlled business tools | 8 tool APIs, logs, unit and smoke tests |
| Phase 7 | Done | LangGraph workflow | `/api/agent/run`, `/api/chat`, graph tests, guard smoke |
| Phase 8 | Later | Evaluation runner and reports | not started |

## Current Health Command

Run the phase smoke check:

```powershell
python scripts/phase_smoke_check.py
```

Run unit tests:

```powershell
python -m pytest
```

On this Windows machine, if pytest cannot access the default temp directory, use:

```powershell
python -m pytest --basetemp=D:\Agent_proj\pytest-cache-files-run
```

## Completed Phase Details

### Phase 0: Repository Baseline

The repository has a stable project layout, `.gitignore`, GitHub remote, and staged project docs. Local secrets and raw data are intentionally not committed.

### Phase 1: Backend Scaffold

FastAPI is available through `orderops_api.main:create_app`. The health route is stable:

```text
GET /health
```

### Phase 2: Local Infrastructure

Docker Compose runs:

- PostgreSQL on host port `15432`
- Redis on `6379`
- Qdrant on `6333` and `6334`

PostgreSQL uses port `15432` because local `5432` may already be occupied.

### Phase 3: Database and ETL

Olist CSV data is imported into these core tables:

- `orders`
- `order_items`
- `payments`
- `reviews`
- `products`
- `sellers`
- `customers`

Raw CSV files stay under `data/raw/` and are ignored by Git.

### Phase 4: Derived Support Tickets

The project creates `support_tickets` from operational signals missing in Olist:

- delivery delay
- low review
- canceled order
- high value order

This gives the Agent realistic work items without pretending the original dataset has a support center table.

### Phase 5: Policy RAG

The active local RAG stack is real, not placeholder:

- embedding: `D:\models\bge-m3`
- rerank: `D:\models\bge-reranker-v2-m3`
- vector store: Qdrant collection `orderops_policies`

Current policy docs are demo policies with explicit Olist data bindings. They separate business rules from dataset-specific field mappings.

### Phase 6: Business Tools

The business tool layer is now the stable action surface for Phase 7:

- `POST /api/tools/order-summary`
- `POST /api/tools/policy-search`
- `POST /api/tools/delivery-compensation`
- `POST /api/tools/refund-eligibility`
- `POST /api/tools/support-ticket-draft`
- `POST /api/tools/approval-decision`
- `POST /api/tools/sql-analysis`
- `POST /api/tools/seller-quality`

All tools use Pydantic schemas and write `tool_call_logs`. Write-intent tools stop at drafts and approvals; no money movement is executed.

### Phase 7: LangGraph Workflow

The agent workflow is now a real LangGraph state machine with:

- input guard
- intent router
- query rewrite
- plan builder
- policy retriever
- order summary
- delivery/refund decision paths
- rule verifier
- approval gate
- draft ticket creation
- final composer

The API exposes:

- `POST /api/agent/run`
- `POST /api/chat`

The response includes intent, visible plan, citations, tool calls, approval state, and step trace with node latency.

## Known Boundaries

- The project is a local demo, not production deployment.
- Olist lacks real logistics events, refund ledgers, customer support conversations, and compensation records.
- Current policies are synthetic and intentionally documented as demo policies.
- SQL analysis is read-only and guarded; it is not an admin SQL console.
- Streaming is accepted in the agent request schema but not implemented yet.
- Trace details are returned in responses, but a separate trace storage API is not implemented yet.
- Phase 8 evaluation metrics are not implemented yet.

## Next Phase

Phase 8 should add evaluation with:

- fixed eval cases
- retrieval recall checks
- tool selection accuracy
- tool argument accuracy
- task success rate
- risk-control accuracy
- latency reporting
