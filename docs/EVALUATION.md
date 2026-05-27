# Evaluation

Phase 8 adds a repeatable evaluation loop for the OrderOps Agent. The goal is not to claim a broad benchmark score; it is to catch regressions in the actual product workflow we are building.

## What It Checks

The seed set in `data/eval/eval_cases_seed.csv` covers:

- delayed delivery compensation
- on-time delivery rejection
- refund review
- policy-only Q&A
- seller quality analysis
- guarded read-only SQL analysis
- unsafe input blocking
- missing order context

Each case declares expected intent, required tools, expected decision, approval requirement, expected citations, risk level, and metric tags.

## Metrics

`scripts/run_eval.py` reports:

- task success rate
- intent accuracy
- tool selection recall
- tool selection exact match
- tool argument accuracy
- retrieval recall
- decision accuracy
- approval accuracy
- risk-control accuracy
- p95 and average latency
- LLM success and fallback call counts
- tag-level success rates

`task_success_rate` is the strict product-facing metric. A case only passes when the relevant routing, tool, argument, retrieval, decision, approval, and risk-control checks pass.

## Default Safety

By default, evaluation is conservative:

- `live_llm=False`, so it does not spend API credits.
- `allow_writes=False`, so it does not create support ticket drafts.
- report files are written only by the CLI path unless disabled.

This makes the default eval suitable for frequent local runs and CI-style checks.

## Run It

Run the full seed set:

```powershell
python scripts/run_eval.py
```

Run one case without writing reports:

```powershell
python scripts/run_eval.py --case-id EVAL-008 --no-write-report --json
```

Run a small live LLM smoke case when `.env` has a provider key:

```powershell
python scripts/run_eval.py --case-id EVAL-008 --live-llm --no-write-report --json
```

Allow write tools only when you intentionally want draft tickets created during an eval:

```powershell
python scripts/run_eval.py --allow-writes
```

The API exposes the same runner:

```text
POST /api/evals/run
```

Example body:

```json
{
  "case_ids": ["EVAL-008"],
  "live_llm": false,
  "allow_writes": false,
  "write_reports": false
}
```

## Reports

CLI runs write:

```text
reports/eval/eval_report.json
reports/eval/eval_report.md
```

`reports/` is ignored by Git because eval reports are generated artifacts. Commit the eval code and seed cases, not local report outputs.

## Current Boundary

This is a seed regression suite, not a large public benchmark. The next reasonable expansion is to add more cases from real support-ticket scenarios, keep a frozen golden set, and track trend reports over time.
