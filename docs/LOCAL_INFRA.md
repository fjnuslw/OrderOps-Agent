# Local Infrastructure

Phase 2 introduces local services that the API will use in later phases. These services are not business logic yet; they are the local runtime dependencies for future ETL, RAG, state, and evaluation work.

## Services

| Service | Local URL | Purpose |
| --- | --- | --- |
| PostgreSQL | `localhost:5432` | Structured data: orders, tickets, evaluation results |
| Redis | `localhost:6379` | Cache, session state, lightweight background task state |
| Qdrant | `http://localhost:6333` | Vector database for policy document retrieval |

## Files

- `docker-compose.yml` defines the local containers.
- `.env.example` documents environment variables and safe local defaults.
- `.env` is for your local overrides and must not be committed.
- `apps/api/src/orderops_api/core/config.py` is the Python settings module used by the API.

## Start Services

Install Docker Desktop first, then run:

```powershell
docker compose up -d
```

Check status:

```powershell
docker compose ps
```

Stop services:

```powershell
docker compose down
```

Stop services and delete local persisted data:

```powershell
docker compose down -v
```

## Configuration Flow

The API reads settings in this order:

1. Defaults in `core/config.py`
2. Local `.env` file when present
3. Environment variables already set in the shell

For normal local development, copy `.env.example` to `.env` only when you need to change ports, credentials, or service URLs.

## Current Limitation

This phase defines and tests configuration, but it does not connect to these services yet. Database schema creation, ETL, Qdrant indexing, and Redis-backed state are later phases.
