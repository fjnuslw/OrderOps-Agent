# Derived Support Tickets

Phase 4 derives support tickets from imported Olist order data. Olist does not include a native customer support ticket table, so this project creates one from realistic operational signals.

## Scenarios

| Scenario | Source signal | Purpose |
| --- | --- | --- |
| `delivery_delay` | Delivered later than estimated date by more than 2 days | Compensation and delivery SLA review |
| `low_review` | Review score `<= 2` | Customer recovery and reply drafting |
| `canceled_order` | Order status is `canceled` | Refund status follow-up |
| `high_value_order` | Total payment value `>= 1000` | High-impact manual review |

## Generate Tickets

Make sure local infrastructure is running and Olist CSVs have already been imported:

```powershell
docker compose up -d
conda activate orderops-agent
python scripts/db_bootstrap.py
python scripts/etl_olist.py --replace
```

Generate derived tickets:

```powershell
python scripts/generate_support_tickets.py --replace
```

Default behavior generates up to 100 tickets per scenario.

## Latest Local Smoke Check

```text
support_tickets_total: 400
canceled_order: 100
delivery_delay: 100
high_value_order: 100
low_review: 100
```

Integrity check:

```text
total: 400
distinct_ticket_ids: 400
missing_order_id: 0
```

## Notes

Ticket IDs are deterministic per `scenario + order_id`, so repeated generation can update existing tickets without creating duplicates. Use `--replace` during local development when you want a clean regenerated set.
