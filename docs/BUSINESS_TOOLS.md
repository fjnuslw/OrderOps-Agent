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

### check_refund_eligibility

Purpose: decide whether an order can enter refund review. This tool does not execute a refund; it only returns an eligibility decision and policy citations.

API:

```http
POST /api/tools/refund-eligibility
```

Example request:

```json
{
  "order_id": "1b3190b2dfa9d789e1f14c05b647a14a",
  "reason_category": "delivery_delay",
  "request_at": "2018-09-23T12:00:00",
  "customer_message": "配送严重延迟，申请退款复核",
  "policy_top_k": 3,
  "trace_id": "demo-refund-1"
}
```

Current decision rules:

- Delivered orders requested within 7 natural days can enter refund review.
- Canceled or unavailable orders enter manual fulfillment/refund review.
- Requests outside the 7-day window are rejected unless quality signals require manual review.
- Low review score, high order value, unknown reason, or missing request timestamp are returned as risk flags.

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

### decide_approval

Purpose: approve or reject a pending approval record and move the related support ticket status.

API:

```http
POST /api/tools/approval-decision
```

Example request:

```json
{
  "approval_id": "APR-A2C5C1365168",
  "action": "approve",
  "decided_by": "ops_reviewer",
  "decision_reason": "Evidence is sufficient.",
  "trace_id": "demo-approval-1"
}
```

Status transitions:

- `approve`: `approvals.status=approved`, `support_tickets.status=open`
- `reject`: `approvals.status=rejected`, `support_tickets.status=rejected`
- already decided approvals return `conflict`

## SQL Guard

`orderops_api.tools.sql_guard` contains the first SQL guardrail helpers for the later SQL analysis tool:

- only `SELECT` or `WITH` queries are allowed
- multiple statements are rejected
- write/admin keywords are rejected
- private fields such as `customer_unique_id` are rejected
- a default `LIMIT` can be appended when missing

The guarded SQL analysis execution tool is exposed as `sql_analysis`.

### sql_analysis

Purpose: execute controlled read-only SQL analysis.

API:

```http
POST /api/tools/sql-analysis
```

Example request:

```json
{
  "sql": "SELECT order_status, COUNT(*) AS count FROM orders GROUP BY order_status ORDER BY count DESC",
  "limit": 10,
  "timeout_ms": 3000,
  "trace_id": "demo-sql-1"
}
```

The tool:

- strips SQL comments before validation
- allows only `SELECT` or `WITH`
- blocks multiple statements
- blocks write/admin keywords
- blocks private fields such as `customer_unique_id`
- adds or tightens `LIMIT`
- runs the query in a read-only transaction with statement timeout

### seller_quality_analysis

Purpose: analyze a seller's operational quality in a bounded time window.

API:

```http
POST /api/tools/seller-quality
```

Example request:

```json
{
  "seller_id": "7a67c85e85bb2ce8582c35f2203ad736",
  "time_window_days": 365,
  "trace_id": "demo-seller-1"
}
```

Current metrics:

- total orders
- delivered orders
- delayed orders
- low-review orders
- support-ticket pressure
- late rate
- low-review rate
- seller risk level
- suggested actions

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
decide_approval: success
check_refund_eligibility: success
sql_analysis: success and blocked
seller_quality_analysis: success
```
