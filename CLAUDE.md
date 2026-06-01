# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a microservices-based platform (PFI — Proyecto Final Integrador) built with FastAPI + PostgreSQL. The services are orchestrated via Docker Compose with Traefik as the API gateway.

## Running the Infrastructure

```bash
# Start shared infrastructure (postgres, redis, minio, pgadmin, api-gateway)
docker compose up -d postgres redis minio pgadmin api-gateway

# Start a specific microservice (uses Docker profiles)
docker compose --profile services up -d identity-service

# Tear everything down
docker compose down
```

Services are exposed at:
- API Gateway (Traefik): `http://localhost:80`, dashboard at `http://localhost:8080`
- identity-service direct: `http://localhost:8001`
- pgAdmin: `http://localhost:5050`
- MinIO console: `http://localhost:9001`

## Architecture

### Shared infrastructure (always running)
| Service | Purpose |
|---------|---------|
| Traefik | API gateway — routes `/api/<service>` to the correct container |
| PostgreSQL 16 | Single DB instance with one schema per service for isolation |
| Redis 7 | Shared cache / session store |
| MinIO | Object storage (used by scoring and mlops services) |

### Microservices (one per domain, all FastAPI/Python 3.12)
Each service lives under `services/<name>/` and follows the same internal layout:

```
services/<name>/
  app/
    config.py      # pydantic-settings, reads env vars
    database.py    # SQLAlchemy engine + session
    models.py      # SQLAlchemy ORM models (schema-namespaced)
    schemas.py     # Pydantic request/response schemas
    auth.py        # JWT helpers (identity-service only)
    main.py        # FastAPI app, routes
  requirements.txt
  Dockerfile
```

Planned services and their schemas:
- `identity` — auth, users, roles
- `clinical` — patient clinical records
- `scoring` — scoring/assessment results (uses MinIO for file storage)
- `analytics` — reporting and dashboards
- `mlops` — ML model management (uses MinIO for model artifacts)

### Database isolation pattern
`infra/postgres/init.sql` creates one PostgreSQL schema and one DB user per service. Each service connects only to its own schema — enforced via `GRANT` permissions. SQLAlchemy models use `__table_args__ = {"schema": "<service>"}`.

### JWT auth pattern (identity-service)
- Access tokens: 15 min, HS256, payload includes `sub` (user UUID) and `role`
- Refresh tokens: 7 days, stored in `identity.refresh_tokens` as SHA-256 hash, single-use (revoked on use)
- `SECRET_KEY` comes from env var `secret_key` — the default in `config.py` is dev-only

### Traefik routing
Each service container declares its own Traefik labels:
```
traefik.http.routers.<name>.rule=PathPrefix(`/api/<name>`)
```
The FastAPI app sets `root_path="/api/<name>"` so OpenAPI docs resolve correctly.

## Adding a New Microservice

1. Create `services/<name>/` following the existing identity-service structure.
2. Add the service to `docker-compose.yml` under the `services` profile with appropriate env vars and Traefik labels.
3. `infra/postgres/init.sql` already pre-creates schemas for all planned services — no changes needed there for the five planned domains.
4. Run `docker compose --profile services up -d <name>` to start it.
