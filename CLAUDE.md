# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PFI (Proyecto Final Integrador) is a speech-therapy platform built as microservices using FastAPI + PostgreSQL, orchestrated via Docker Compose with Traefik as the API gateway.

> **Target architecture (v2.1):** the canonical design reference is
> `docs/Arquitectura-Logica.md` (Julio 2026), with C4 / sequence / class / ER diagrams
> under `docs/`. Key differences from the *currently implemented* code, tracked as the
> forward-looking design:
> - **Annotation subsystem re-engineered:** Label Studio is dropped in favor of an
>   **own annotation module** (UI in the React SPA + API in `mlops-service`). The
>   `docker-compose.yml` still ships the Label Studio container; retiring it is part of
>   this change.
> - **JWT** moves from **HS256 shared secret** (current code) to **RS256 + JWKS**
>   (offline verification via the identity-service public key).
> - **scoring-service** becomes an ML pipeline: `scoring-api` (FastAPI + SSE) +
>   `scoring-worker` (Celery) running ffmpeg → VAD → MFA/CTC alignment → GOP-CTC over
>   wav2vec2-XLSR-53 → phoneme classification.
> - **analytics-service** adds consolidated metrics, alerts and notifications;
>   **mlops-service** adds MLflow (registry) + DVC (dataset versioning).
> - **Planned event contract:** `AttemptCreated`, `AttemptScored`, `AttemptFailed`,
>   `PrescriptionUpdated`, `AlertRaised`, `ModelPromoted`, `CorpusConsentRevoked`.
>
> Only `PatientRegisteredWithInvitation` (identity → clinical) is implemented today; the
> rest of the above is design, not code.

## Running the Infrastructure

```bash
# Start shared infrastructure (postgres, redis, minio, pgadmin, api-gateway)
docker compose up -d postgres redis minio pgadmin api-gateway

# Start a specific microservice (uses Docker profiles)
docker compose --profile services up -d identity-service
docker compose --profile services up -d clinical-service

# Rebuild a service after code changes
docker compose --profile services up -d --build identity-service

# Tear everything down
docker compose down
```

Service endpoints:
- API Gateway (Traefik): `http://localhost:80`, dashboard at `http://localhost:8080`
- identity-service direct: `http://localhost:8001`
- clinical-service direct: `http://localhost:8002`
- scoring-service direct: `http://localhost:8003`
- Label Studio: `http://localhost:8090`
- pgAdmin: `http://localhost:5050`
- MinIO console: `http://localhost:9001`

### Local development (outside Docker)

To iterate without rebuilding images, run a service directly against the Docker-hosted infra:

```bash
cd services/identity-service
pip install -r requirements.txt
DATABASE_URL="postgresql://identity_user:identity_pass@localhost:5432/pfi" \
REDIS_URL="redis://localhost:6379/0" \
uvicorn app.main:app --reload --port 8001
```

OpenAPI docs for any running service: `http://localhost:<port>/docs`

## Architecture

### Shared infrastructure (always running)
| Service | Purpose |
|---------|---------|
| Traefik | Routes `/api/<service>` to the correct container |
| PostgreSQL 16 | Single DB instance, one schema per service |
| Redis 7 | Pub/sub event bus + shared cache |
| MinIO | Object storage for audio files and ML model artifacts |
| Label Studio | Phonemic labeling of audio data for the ML pipeline *(exploratory phase; being retired in the v2.1 re-engineering — replaced by the own annotation module in `mlops-service` + SPA)* |

### Service implementation status
| Service | Status | Port |
|---------|--------|------|
| identity-service | Complete | 8001 |
| clinical-service | Complete | 8002 |
| scoring-service | Stub | 8003 |
| analytics-service | Stub | 8004 |
| mlops-service | Stub | 8005 |

### Internal service layout

Every service follows this structure:

```
services/<name>/
  app/
    config.py      # pydantic-settings, reads env vars
    database.py    # SQLAlchemy engine + SessionLocal + Base
    models.py      # SQLAlchemy ORM models (schema-namespaced)
    schemas.py     # Pydantic request/response schemas
    main.py        # FastAPI app + all routes
    events.py      # Redis pub/sub listener (if the service consumes events)
    auth.py        # JWT helpers (identity-service only)
  requirements.txt
  Dockerfile
```

### Database isolation pattern

`infra/postgres/init.sql` creates one PostgreSQL schema and one DB user per service. Each service's DB user can only access its own schema. SQLAlchemy models declare `__table_args__ = {"schema": "<service>"}`.

Tables are created at startup via `Base.metadata.create_all(bind=engine)` in `main.py` — there are no active Alembic migrations yet (alembic is in requirements but unused).

### JWT auth pattern

- Access tokens: 15 min, HS256, payload `{"sub": "<user_uuid>", "role": "<role>", "type": "access"}`
- Refresh tokens: 7 days, stored in `identity.refresh_tokens` as SHA-256 hash, **single-use** (revoked on use, new one issued)
- The shared `secret_key` env var is used by every service to verify tokens independently — there is no auth proxy. Non-identity services decode the JWT directly in `main.py` using `python-jose`.

### Traefik routing

Each service container declares its own labels:
```
traefik.http.routers.<name>.rule=PathPrefix(`/api/<name>`)
```
The FastAPI app sets `root_path="/api/<name>"` so OpenAPI docs and redirects resolve correctly through the gateway.

### Redis event bus

Services communicate asynchronously via Redis pub/sub on named channels. The listener runs in a background daemon thread started on FastAPI `startup`.

Current events:

| Channel | Event | Publisher | Consumer |
|---------|-------|-----------|----------|
| `identity.events` | `PatientRegisteredWithInvitation` | identity-service | clinical-service |

**Invitation → patient registration flow:**
1. A clinician calls `POST /api/identity/invitations` → generates a `PFI-XXXXXXXX` code stored in `identity.invitation_codes`.
2. The patient calls `POST /api/identity/invitations/{code}/validate` to prefill the registration form.
3. The patient calls `POST /api/identity/auth/register-with-code` → marks the code as `consumed`, creates the `identity.users` record, and publishes `PatientRegisteredWithInvitation` to Redis.
4. clinical-service's listener receives the event and automatically creates a `clinical.patients` record and a `clinical.clinical_relationships` row linking the patient to the clinician.

### Adding a new microservice

1. Create `services/<name>/` following the identity-service or clinical-service structure.
2. Add the service to `docker-compose.yml` under the `services` profile with the appropriate env vars and Traefik labels.
3. `infra/postgres/init.sql` already pre-creates schemas for all five planned domains — no SQL changes needed.
4. Run `docker compose --profile services up -d --build <name>`.
