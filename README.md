# OrderOps Agent

OrderOps Agent is an ecommerce after-sales operations agent demo. It is designed to show an end-to-end agent workflow that combines policy retrieval, structured order data, tool calling, workflow orchestration, evaluation, and backend service design.

This repository currently contains the project specification and starter assets for Codex-driven implementation.

## Project Materials

- `docs/PROJECT_SPEC.md` - full product and engineering specification
- `docs/BUILD_PLAN.md` - practical staged build plan
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
python -m uvicorn orderops_api.main:app --app-dir apps/api/src --reload
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

## Notes

The raw Olist dataset is not included in this repository. Download it separately from Kaggle or another public mirror, place local CSV files under `data/raw/`, and document the data source before publishing derived results.
