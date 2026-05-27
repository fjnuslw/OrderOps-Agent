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
| Phase 7 | Done | LLM-assisted LangGraph workflow | `/api/agent/run`, `/api/chat`, graph tests, guard smoke |
| Phase 8 | Done | Evaluation runner and reports | 8 seed cases, metrics, `/api/evals/run`, smoke check |

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
- LLM-assisted intent router with deterministic fallback
- LLM-assisted query rewrite with deterministic fallback
- LLM-assisted visible plan builder with deterministic fallback
- policy retriever
- order summary
- delivery/refund decision paths
- rule verifier
- approval gate
- draft ticket creation
- LLM-assisted final composer with deterministic fallback

The API exposes:

- `POST /api/agent/run`
- `POST /api/chat`

The response includes intent, visible plan, citations, tool calls, LLM calls, approval state, and step trace with node latency.

DeepSeek can be enabled through local `.env` with `ORDEROPS_LLM_PROVIDER=deepseek`, `ORDEROPS_LLM_MODEL=deepseek-v4-pro`, and `ORDEROPS_LLM_API_KEY`. Without a key, the workflow remains runnable through deterministic fallbacks.

### Phase 8: Evaluation

The project now has a repeatable agent eval loop:

- seed cases: `data/eval/eval_cases_seed.csv`
- runner: `apps/api/src/orderops_api/evaluation/`
- CLI: `scripts/run_eval.py`
- API: `POST /api/evals/run`
- docs: `docs/EVALUATION.md`

The default eval disables live LLM calls and write tools. It checks intent accuracy, tool selection, tool arguments, retrieval citations, business decisions, approval state, risk control, task success, and latency.

## Known Boundaries

- The project is a local demo, not production deployment.
- Olist lacks real logistics events, refund ledgers, customer support conversations, and compensation records.
- Current policies are synthetic and intentionally documented as demo policies.
- SQL analysis is read-only and guarded; it is not an admin SQL console.
- Streaming is accepted in the agent request schema but not implemented yet.
- Trace details are returned in responses, but a separate trace storage API is not implemented yet.
- The Phase 8 eval set is still a seed regression suite, not a large external benchmark.

## Next Phase

The next useful phases are trace persistence, more realistic multi-turn memory, and a small operator UI. The eval suite should also grow from the current seed set into a larger frozen regression set.
