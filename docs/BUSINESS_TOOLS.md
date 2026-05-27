# Business Tools

Phase 6 starts the controlled tool layer that the future LangGraph agent will call. The tools are regular Python functions with Pydantic input/output schemas, and the API exposes a small testing surface under `/api/tools`.

## Implemented Tools

### get_order_summary

Purpose: read a single order and summarize fulfillment, money, sellers, latest review, and existing support tickets.

API:

```http
POST /api/tools/order-summary
```

Example request:

```json
{
  "order_id": "1b3190b2dfa9d789e1f14c05b647a14a",
  "trace_id": "demo-order-1"
}
```

Important output fields:

- `status`: `success`, `not_found`, or `error`
- `late_days`: natural-day ceiling between delivered date and estimated delivery date
- `delivered_late`: whether the delivered date is later than estimated
- `total_payment_value`
- `seller_ids`
- `support_tickets`

### search_policy

Purpose: wrap the existing policy RAG search as a tool-shaped interface.

API:

```http
POST /api/tools/policy-search
```

Example request:

```json
{
  "query": "延迟送达如何补偿",
  "doc_types": ["delivery_sla_policy"],
  "top_k": 3,
  "rerank": true,
  "trace_id": "demo-policy-1"
}
```

This uses the current local BGE stack: `D:\models\bge-m3` for embedding and `D:\models\bge-reranker-v2-m3` for rerank.

### check_delivery_compensation

Purpose: combine order summary and policy retrieval to decide whether a delivered order is a delayed-compensation candidate.

API:

```http
POST /api/tools/delivery-compensation
```

Example request:

```json
{
  "order_id": "1b3190b2dfa9d789e1f14c05b647a14a",
  "trace_id": "demo-delivery-1",
  "policy_top_k": 3
}
```

Current decision rules:

- If the order is not found, return `not_found`.
- If the order is not marked `delivered`, return `manual_review_required`.
- If delivered or estimated timestamps are incomplete, return `manual_review_required`.
- If delivered more than 2 natural days after estimated delivery, return `eligible_with_manual_approval`.
- Otherwise return `not_eligible`.

The tool never directly promises compensation. A positive decision has `approval_required=true`.

### create_support_ticket_draft

Purpose: create a support ticket draft and a pending approval record. This is the first controlled write tool in Phase 6.

API:

```http
POST /api/tools/support-ticket-draft
```

Example request:

```json
{
  "order_id": "1b3190b2dfa9d789e1f14c05b647a14a",
  "scenario": "delivery_delay",
  "title": "Delivery delay compensation review",
  "description": "Order arrived more than 2 natural days after the estimated delivery date.",
  "expected_action": "Review the policy evidence and decide whether compensation is appropriate.",
  "priority": "high",
  "risk_level": "high",
  "requested_by": "agent",
  "policy_refs": ["delivery_sla_policy_v1#s3"],
  "trace_id": "demo-ticket-1"
}
```

The tool writes:

- one `support_tickets` row with `status=draft_pending_approval`
- one `approvals` row with `status=pending`

It does not approve the ticket and does not perform any money movement.

## SQL Guard

`orderops_api.tools.sql_guard` contains the first SQL guardrail helpers for the later SQL analysis tool:

- only `SELECT` or `WITH` queries are allowed
- multiple statements are rejected
- write/admin keywords are rejected
- private fields such as `customer_unique_id` are rejected
- a default `LIMIT` can be appended when missing

The SQL analysis execution tool is not exposed yet.

## Tool Logs

Tool calls are written to `tool_call_logs` with:

- `trace_id`
- `tool_name`
- request args JSON
- result JSON
- status
- latency
- error type

Latest smoke check:

```text
get_order_summary: success
search_policy: success
check_delivery_compensation: success
create_support_ticket_draft: success
```
