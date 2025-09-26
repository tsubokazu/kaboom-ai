# CLAUDE.md

This document explains how to work with the Kaboom project, with special focus on
FastAPI, Cloud Tasks, and Redis development patterns now that the ingestion and
analysis pipelines are running on Cloud Run + n8n.

## Repository at a Glance

```
/
├── api/                 # FastAPI application (deployed to Cloud Run)
│   ├── app/             # Routers, services, middleware, cloud tasks
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
- `api/app/tasks/*` – Legacy Celery task definitions (being migrated to Cloud Tasks).
- `api/app/services/*` – Reusable services (Redis, monitoring, portfolio, trading, cloud_tasks).
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
     1. `POST /.../run` → enqueue a Cloud Task (or Celery if legacy), return `job_id`.
     2. `GET /.../jobs/{job_id}` → read status/result from Redis or DB.
   - Follow the pattern already used by `/api/v1/ingest/run-daily`.
   - Use `USE_CLOUD_TASKS` environment variable to switch between Cloud Tasks and Celery.

5. **Error Handling & Logging**
   - Log errors with `logger.error(...)` including context.
   - Bubble exceptions to FastAPI so they become 500 unless handled.
   - For Cloud Run health checks, keep endpoints fast and free of heavy dependencies.

## Cloud Tasks Guidelines (Primary)

1. **Cloud Tasks Service**
   - Implemented in `api/app/services/cloud_tasks.py`.
   - Uses HTTP PUSH targets to call internal Cloud Run endpoints.
   - Configured via `USE_CLOUD_TASKS`, `CLOUD_TASKS_LOCATION`, `CLOUD_RUN_SERVICE_URL` environment variables.

2. **Task Structure**
   - Public endpoint (e.g., `POST /api/v1/ingest/run-daily`) creates Cloud Task and returns `job_id`.
   - Internal endpoint (e.g., `POST /internal/ingest/run-daily`) executes actual work.
   - Internal endpoints are secured with OIDC token authentication.

3. **Job Status Tracking**
   - Use `RedisClient.set_job_status(job_id, status, result)` to update state.
   - Status enum values: `queued`, `running`, `completed`, `failed`.
   - Always use `.value` when comparing JobStatus enums: `status.value == "completed"`.

4. **Best Practices**
   - Keep tasks idempotent; running the same task twice should not corrupt data.
   - Handle Cloud Tasks 30-minute timeout limit.
   - Use proper error handling and status updates in internal endpoints.
   - Test with `gcloud tasks run` for manual execution.

## Celery Guidelines (Legacy - Being Migrated)

1. **Migration Status**
   - Ingestion jobs have been migrated to Cloud Tasks.
   - Other jobs (universe selection, analysis) still use Celery.
   - Use `USE_CLOUD_TASKS=false` to fall back to Celery if needed.

2. **Legacy Celery App**
   - Defined in `api/app/tasks/celery_app.py`. Import tasks in `app/tasks/__init__.py`
     so Celery discovers them.
   - Configure broker/backend via `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (Redis by default).

3. **Migration Process**
   - Follow the pattern in `/docs/api/cloud-tasks-migration.md`.
   - Create internal endpoint in `api/app/routers/internal.py`.
   - Update public API to support both Cloud Tasks and Celery via feature flag.

## Redis Usage

1. **Client**: `api/app/services/redis_client.py` provides a shared async client.
   - Call `get_redis_client()` via FastAPI `Depends` to ensure connection pooling.
   - Recently added helper methods (`set`, `get`, `publish`) wrap lower-level calls
     and provide compatibility for existing services.

2. **Key Patterns**
   - Caching: `cache:<key>` via `set_cache` / `get_cache`.
   - Sessions: `session:<id>` for auth tokens.
   - Jobs: `job:<job_id>` – Cloud Tasks/Celery/n8n job states.
   - Pub/Sub: channels like `job_status:<job_id>`, `price_update:<symbol>`.

3. **Health Checks**
   - `/health` endpoint depends on Redis and DB being reachable. If you disable Redis
     in Cloud Run (e.g., `DISABLE_REDIS=true`), ensure middleware/services account
     for it.

## Universe & Market Data Jobs

- **Daily ingestion**: `/api/v1/ingest/run-daily` (non-blocking). Now uses Cloud Tasks instead of Celery.
  Populates InfluxDB with 1m/5m/1d data for TSE Prime universe. Poll status via `/api/v1/ingest/jobs/{id}`.
- **Universe selection**: Implemented in `api/batch/pipeline/select_universe.py`.
  Currently executed via CLI or n8n script. *Cloud Tasks wrapper is still a TODO.*
- **Backtesting inputs**: Updated data feeds are now ready; sell/buy logic should call
  the ingestion job before running analysis.

## n8n / Automation Notes

- n8n orchestrates job lifecycles: trigger → `POST` job → poll `GET` status → notify.
- Poll intervals of 90–120 seconds are recommended to avoid hitting Cloud Run limits.
- Use Slack / LINE Notify nodes for success/failure messages; include `job_id` and
  summary metrics for debugging.

## Next Steps / TODOs

- [x] Migrate ingestion jobs from Celery to Cloud Tasks.
- [ ] Migrate universe-selection from CLI to Cloud Tasks FastAPI endpoint.
- [ ] Migrate remaining Celery tasks (chart generation, technical analysis) to Cloud Tasks.
- [ ] Remove legacy Celery infrastructure after all migrations complete.
- [x] Write docs in `docs/api/` detailing new endpoints and job flows.
- [ ] Extend CLAUDE.md when new services (Backtest runner, AI decision service) are introduced.

## Trading Decision API Reference

Detailed API candidates and orchestration flows for the trading decision platform are
documented in `docs/api/trading-decision-apis.md`. Review that file when implementing
new routers, services, or batch jobs related to market data ingestion, signal
production, portfolio management, or reporting.

## Environment Variables

Key environment variables for Cloud Tasks:
- `USE_CLOUD_TASKS=true` - Enable Cloud Tasks instead of Celery
- `GOOGLE_CLOUD_PROJECT=kaboom-472705` - GCP project ID
- `CLOUD_TASKS_LOCATION=asia-northeast1` - Cloud Tasks region
- `CLOUD_RUN_SERVICE_URL=https://api-xxxx-uc.a.run.app` - Cloud Run service URL

Keep this guide updated whenever backend conventions change so assistants and
engineers share the same workflow.
