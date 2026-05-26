# Olist ETL

Phase 3 imports the Olist CSV dataset into local PostgreSQL.

## Current Status

- Database schema bootstrap is implemented.
- CSV file validation is implemented.
- COPY-based import logic is implemented for the core Olist tables.
- The selected core tables preserve the original CSV columns used by this import path.
- The repository does not include raw Olist CSV files.

## Required CSV Files

Place these files under `data/raw/`:

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
olist_customers_dataset.csv
```

The larger geolocation and category translation files are intentionally deferred until the core import path is stable.

## Download Dataset

Canonical source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

License: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).

PowerShell download:

```powershell
Invoke-WebRequest -Uri 'https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce' -OutFile 'data/raw/brazilian-ecommerce.zip'
Expand-Archive 'data/raw/brazilian-ecommerce.zip' -DestinationPath 'data/raw' -Force
```

The downloaded files stay local because `data/raw/*` is ignored by Git.

## Bootstrap Database

Start local infrastructure:

```powershell
docker compose up -d
```

Apply the target schema:

```powershell
conda activate orderops-agent
python scripts/db_bootstrap.py
```

## Import CSV Files

After placing the required CSV files under `data/raw/`, run:

```powershell
python scripts/etl_olist.py --replace
```

`--replace` truncates the target Olist tables before importing, which makes repeated local development runs predictable.

## Smoke Check

The ETL command prints row counts for each imported table:

```text
orders: ...
order_items: ...
payments: ...
reviews: ...
products: ...
sellers: ...
customers: ...
```

When raw CSV files are missing, the command fails with a list of missing file paths instead of pretending the import succeeded.

Latest local smoke check:

```text
orders: 99441
order_items: 112650
payments: 103886
reviews: 99224
products: 32951
sellers: 3095
customers: 99441
```
