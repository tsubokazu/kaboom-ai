# CLAUDE.md

This document explains how to work with the Kaboom project, with special focus on
FastAPI, Celery, and Redis development patterns now that the ingestion and
analysis pipelines are running on Cloud Run + n8n.

## Repository at a Glance

```
/
├── api/                 # FastAPI application (deployed to Cloud Run)
│   ├── app/             # Routers, services, middleware, celery tasks
│   ├── batch/           # Data ingestion + universe selection pipelines
│   ├── Dockerfile       # Cloud Run image (Artifact Registry)
│   └── ...
├── docs/                # Runbooks, architectural notes
├── web/                 # (Preparing) Next.js front-end project
└── .github/workflows/   # CI/CD pipelines (build + deploy to Cloud Run)
```

Important entry points:

- `api/app/main.py` – FastAPI application factory (lifespan hooks start DB, Redis,
  realtime, monitoring services).
- `api/app/routers/*` – REST API endpoints. Universe selection API has **not** been
  implemented yet; it currently runs via CLI/n8n.
- `api/app/tasks/*` – Celery task definitions (market data, AI analysis, etc.).
- `api/app/services/*` – Reusable services (Redis, monitoring, portfolio, trading).
- `api/batch/*` – Ingestion & universe selection pipelines used by Cloud Run jobs
  and n8n.

## FastAPI Development Guidelines

1. **Routers & Modules**
   - Create new endpoints under `api/app/routers/<feature>.py` and register them in
     `app/main.py`.
   - Keep routers thin. Business logic should live in `api/app/services` or
     dedicated modules.
   - Use Pydantic models for request/response validation. Place shared models in
     `api/app/schemas` (create if needed).

2. **Async everywhere**
   - Database calls use async SQLAlchemy sessions (`AsyncSessionLocal`).
   - Redis uses `redis.asyncio`; always `await redis_client.*`.

3. **Dependency Injection**
   - Use `Depends(...)` to inject services (DB session, Redis client, auth). Example:
     ```python
     @router.get("/jobs/{job_id}")
     async def get_job(job_id: str, redis_client: RedisClient = Depends(get_redis_client)):
         status = await redis_client.get_job_status(job_id)
         ...
     ```

4. **Job APIs (long running)**
   - For heavy tasks (ingestion, analysis), expose two endpoints:
     1. `POST /.../run` → enqueue a Celery task, return `job_id`.
     2. `GET /.../jobs/{job_id}` → read status/result from Redis or DB.
   - Follow the pattern already used by `/api/v1/ingest/run-daily`.

5. **Error Handling & Logging**
   - Log errors with `logger.error(...)` including context.
   - Bubble exceptions to FastAPI so they become 500 unless handled.
   - For Cloud Run health checks, keep endpoints fast and free of heavy dependencies.

## Celery Guidelines

1. **Celery App**
   - Defined in `api/app/tasks/celery_app.py`. Import tasks in `app/tasks/__init__.py`
     so Celery discovers them.
   - Configure broker/backend via `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (Redis by default).

2. **Defining Tasks**
   - Place in `api/app/tasks/<feature>_tasks.py`.
   - Use `@celery_app.task(bind=True, name="app.tasks.xxx")` to name tasks clearly.
   - Return structured dicts (status, data, error) that API clients can consume.

3. **Job Status Tracking**
   - Use `RedisClient.set_job_status(job_id, status, result)` to update state.
   - Store intermediate results in Redis or Supabase if needed.
   - Expose REST endpoints that read the job state (see FastAPI guidelines above).

4. **Retry & Timeouts**
   - Configure per-task `autoretry_for`, `retry_backoff` to handle transient errors
     (yfinance, Supabase network blips).
   - Keep tasks idempotent; running the same job twice should not corrupt data.

## Redis Usage

1. **Client**: `api/app/services/redis_client.py` provides a shared async client.
   - Call `get_redis_client()` via FastAPI `Depends` to ensure connection pooling.
   - Recently added helper methods (`set`, `get`, `publish`) wrap lower-level calls
     and provide compatibility for existing services.

2. **Key Patterns**
   - Caching: `cache:<key>` via `set_cache` / `get_cache`.
   - Sessions: `session:<id>` for auth tokens.
   - Jobs: `job:<job_id>` – Celery/n8n job states.
   - Pub/Sub: channels like `job_status:<job_id>`, `price_update:<symbol>`.

3. **Health Checks**
   - `/health` endpoint depends on Redis and DB being reachable. If you disable Redis
     in Cloud Run (e.g., `DISABLE_REDIS=true`), ensure middleware/services account
     for it.

## Universe & Market Data Jobs

- **Daily ingestion**: `/api/v1/ingest/run-daily` (non-blocking). Populates InfluxDB
  with 1m/5m/1d data for TSE Prime universe. Poll status via `/api/v1/ingest/jobs/{id}`.
- **Universe selection**: Implemented in `api/batch/pipeline/select_universe.py`.
  Currently executed via CLI or n8n script. *FastAPI or Celery wrapper is still a TODO.*
- **Backtesting inputs**: Updated data feeds are now ready; sell/buy logic should call
  the ingestion job before running analysis.

## n8n / Automation Notes

- n8n orchestrates job lifecycles: trigger → `POST` job → poll `GET` status → notify.
- Poll intervals of 90–120 seconds are recommended to avoid hitting Cloud Run limits.
- Use Slack / LINE Notify nodes for success/failure messages; include `job_id` and
  summary metrics for debugging.

## Next Steps / TODOs

- [ ] Expose universe-selection as a FastAPI async job endpoint.
- [ ] Add Celery task wrappers for chart generation + technical analysis.
- [ ] Write docs in `docs/api/` detailing new endpoints and job flows.
- [ ] Extend CLAUDE.md when new services (Backtest runner, AI decision service) are introduced.

Keep this guide updated whenever backend conventions change so assistants and
engineers share the same workflow.
