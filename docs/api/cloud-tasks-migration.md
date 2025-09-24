# Celery to Cloud Tasks Migration Plan — Ingestion Pipeline First

## 1. Scope & Goals
- Replace the current Celery-based ingestion jobs (`/api/v1/ingest/run-daily`, etc.)
  with Cloud Tasks + Cloud Run HTTP handlers.
- Keep the REST interface to n8n unchanged (`POST /api/v1/ingest/run-daily` returns
  a `job_id`, `GET /api/v1/ingest/jobs/{id}` returns status).
- Use Redis only for job status/progress storage (no longer as Celery broker).
- Lay groundwork so that other Celery tasks (universe selection, chart analysis,
  AI scoring) can migrate afterward.

## 2. Current State
- FastAPI exposes `/api/v1/ingest/run-daily` which enqueues a Celery task.
- Celery workers (Redis broker) execute ingestion, update progress via `RedisClient`.
- `/api/v1/ingest/jobs/{job_id}` reads Redis & Celery state for monitoring.
- n8n automation: trigger → POST run-daily → poll jobs/{id} → notify.

### Pain Points
- Celery workers must be deployed/managed separately (non Cloud Run friendly).
- Redis broker is a single point of failure.
- Vertical scaling & scheduling are manual.

## 3. Target Architecture (Cloud Run + Cloud Tasks)
```
n8n → POST /api/v1/ingest/run-daily (Cloud Run)
     → Cloud Tasks (HTTP PUSH) → POST /internal/ingest/run-daily (Cloud Run endpoint)
     → Redis job status / InfluxDB load
     → GET /api/v1/ingest/jobs/{id} for status (same as today)
```

### Key Changes
1. `POST /api/v1/ingest/run-daily` will create a Cloud Task instead of Celery job.
2. New internal endpoint `POST /internal/ingest/run-daily` executes ingestion synchronously.
3. `RedisClient` continues to store job progress/results; job IDs will be Cloud Task IDs.
4. Celery worker deployment can be removed once all ingestion tasks migrate.

## 4. Implementation Phases

### Phase 0 – Preparation
- [ ] Inspect `api/app/tasks/` ingestion functions (current Celery tasks).
- [ ] Confirm job status schema in Redis (`job:<id>` format) and job API expectations.
- [ ] Ensure Cloud Run service account has `roles/cloudtasks.enqueuer`.
- [ ] Create Cloud Tasks queue `ingest-jobs` (region: asia-northeast1).

### Phase 1 – API Adjustments
- [ ] Add Cloud Tasks helper (`cloud_tasks.py`) to enqueue tasks:
      ```python
      create_task(queue="ingest-jobs", url="/internal/ingest/run-daily", payload={...})
      ```
- [ ] Modify `/api/v1/ingest/run-daily` to call `create_task` and return task name as `job_id`.
- [ ] Keep `GET /api/v1/ingest/jobs/{job_id}` unchanged (reads Redis only).

### Phase 2 – Worker Endpoint
- [ ] Implement `/internal/ingest/run-daily` FastAPI route (secured via Cloud Tasks IAM header).
- [ ] Move ingestion logic from Celery task into this route:
      - Validate payload.
      - Update job status (`queued` → `running` → `completed`/`failed`).
      - Reuse existing ingestion modules (`batch/scripts/run_daily_ingest.py`).
- [ ] Handle Cloud Tasks retry semantics (idempotent operations, duplicate protection).

### Phase 3 – Testing
- [ ] Local integration test: call internal endpoint directly.
- [ ] End-to-end test using `gcloud tasks enqueue` (or `curl` with proper headers).
- [ ] n8n dry-run: `POST /api/v1/ingest/run-daily` → poll → check notifications.
- [ ] Cloud Run logs: confirm success, retry behavior, error logging.

### Phase 4 – Cutover
- [ ] Update docs (`CLAUDE.md`, `docs/api/cloud-tasks-migration.md`).
- [ ] Disable Celery worker deployment for ingestion tasks.
- [ ] Monitor Cloud Tasks queue & Cloud Run for a few ingestion cycles.
- [ ] Remove unused Celery code after confidence period (optional).

## 5. Security & IAM Considerations
- Cloud Tasks will call Cloud Run with OIDC token:
  - Service account needs `roles/run.invoker` on Cloud Run service.
  - Validate audience (`aud`) in handler.
- Ensure `X-Ingest-Token` or similar secrets are still required for external API.
- Optionally limit `POST /internal/ingest/run-daily` to Cloud Tasks requests only.

## 6. Rollback Plan
- Keep Celery worker deployment available until Cloud Tasks version is stable.
- Feature-flag approach: allow `/api/v1/ingest/run-daily` to enqueue Celery or Cloud Tasks based on configuration.
- Use separate Redis keys for new jobs if necessary to avoid clashes.

## 7. Next Steps after Ingestion
- Universe selection job → same pattern.
- Chart generation & technical analysis tasks.
- Long-running AI analysis (backtests) via Cloud Run Jobs if batch size is large.

## 8. References
- Cloud Tasks HTTP target docs: https://cloud.google.com/tasks/docs/creating-http-target-tasks
- Authenticating Cloud Tasks to Cloud Run: https://cloud.google.com/tasks/docs/creating-http-target-tasks#auth
- FastAPI Cloud Run deployment guide (current project’s Dockerfile & CI/CD pipeline)

