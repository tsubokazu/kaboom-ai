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
- [x] Inspect `api/app/tasks/` ingestion functions (current Celery tasks).
- [x] Confirm job status schema in Redis (`job:<id>` format) and job API expectations.
- [x] Ensure Cloud Run service account has `roles/cloudtasks.enqueuer`.
- [x] Create Cloud Tasks queue `ingest-jobs` (region: asia-northeast1).

### Phase 1 – API Adjustments
- [x] Add Cloud Tasks helper (`cloud_tasks.py`) to enqueue tasks:
      ```python
      create_task(queue="ingest-jobs", url="/internal/ingest/run-daily", payload={...})
      ```
- [x] Modify `/api/v1/ingest/run-daily` to call `create_task` and return task name as `job_id`.
- [x] Keep `GET /api/v1/ingest/jobs/{job_id}` unchanged (reads Redis only).

### Phase 2 – Worker Endpoint
- [x] Implement `/internal/ingest/run-daily` FastAPI route (secured via Cloud Tasks IAM header).
- [x] Move ingestion logic from Celery task into this route:
      - Validate payload.
      - Update job status (`queued` → `running` → `completed`/`failed`).
      - Reuse existing ingestion modules (`batch/scripts/run_daily_ingest.py`).
- [x] Handle Cloud Tasks retry semantics (idempotent operations, duplicate protection).

### Phase 3 – Testing
- [x] Local integration test: call internal endpoint directly.
- [x] End-to-end test using `gcloud tasks enqueue` (or `curl` with proper headers).
- [x] n8n dry-run: `POST /api/v1/ingest/run-daily` → poll → check notifications.
- [x] Cloud Run logs: confirm success, retry behavior, error logging.

### Phase 4 – Cutover
- [x] Update docs (`CLAUDE.md`, `docs/api/cloud-tasks-migration.md`).
- [x] Disable Celery worker deployment for ingestion tasks.
- [x] Monitor Cloud Tasks queue & Cloud Run for a few ingestion cycles.
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

## 8. Implementation Details

### 実装済みファイル
- `api/app/services/cloud_tasks.py` - Cloud Tasksヘルパーサービス
- `api/app/routers/internal.py` - 内部エンドポイント（Cloud Tasks実行用）
- `api/app/routers/ingest.py` - パブリックAPIの修正（Cloud Tasks対応）
- `api/app/config/settings.py` - Cloud Tasks設定追加
- `api/requirements.txt`, `api/pyproject.toml` - 依存関係追加

### 発生したエラーと対処法

#### 1. 依存関係エラー
```
ImportError: cannot import name 'tasks_v2' from 'google.cloud'
```
**対処**: `google-cloud-tasks>=2.16.0,<3.0.0`と`PyJWT>=2.8.0,<3.0.0`を追加

#### 2. プロジェクトID未設定
```
Permission denied on resource project None
```
**対処**: `GOOGLE_CLOUD_PROJECT=kaboom-472705`環境変数を追加

#### 3. タスクタイムアウト制限
```
Task.dispatchDeadline must be between [15s, 30m]
```
**対処**: タイムアウトを1800秒（30分）に変更

#### 4. OIDC認証エラー
タスクが実行されない（HTTP status code 0）
**対処**: Cloud TasksにOIDCトークン認証を追加
```python
"oidc_token": {
    "service_account_email": f"{project_number}-compute@developer.gserviceaccount.com",
    "audience": full_url
}
```

#### 5. JobStatus enum比較エラー
ジョブが常に"queued"ステータスのまま
**対処**: `progress_info.status.value == "completed"`（.valueプロパティを使用）

### 設定値
- Cloud Tasksキュー: `ingest-jobs`
- リージョン: `asia-northeast1`
- タイムアウト: 30分（Cloud Tasks制限）
- 認証: OIDC token with service account

## 9. 今後の追加タスク用ガイドライン

### 新しいタスクをCloud Tasksに移行する手順

1. **設定の準備**
   ```python
   # api/app/config/settings.py に追加
   TASK_NAME_QUEUE: str = os.getenv("TASK_NAME_QUEUE", "task-name-jobs")
   ```

2. **Cloud Tasksキューの作成**
   ```bash
   gcloud tasks queues create task-name-jobs \
     --location=asia-northeast1
   ```

3. **内部エンドポイントの実装**
   ```python
   # api/app/routers/internal.py に追加
   @router.post("/internal/task-name/run")
   async def run_task_name_internal(
       request: TaskNameRequest,
       redis_client: RedisClient = Depends(get_redis_client)
   ):
       # 実装ロジック
   ```

4. **パブリックAPIの修正**
   ```python
   # 既存のCeleryタスク呼び出しをCloud Tasks呼び出しに変更
   if settings.USE_CLOUD_TASKS:
       task_name = await cloud_tasks.create_task(...)
   else:
       task = celery_task.delay(...)
   ```

### ベストプラクティス

- **環境変数による制御**: `USE_CLOUD_TASKS`フラグで段階的移行
- **エラーハンドリング**: Redisへのステータス更新を確実に実行
- **タイムアウト設定**: Cloud Tasksの30分制限を考慮
- **認証設定**: OIDC tokenによるCloud Run認証
- **冪等性**: 同じタスクの重複実行を考慮した実装

## 10. References
- Cloud Tasks HTTP target docs: https://cloud.google.com/tasks/docs/creating-http-target-tasks
- Authenticating Cloud Tasks to Cloud Run: https://cloud.google.com/tasks/docs/creating-http-target-tasks#auth
- FastAPI Cloud Run deployment guide (current project's Dockerfile & CI/CD pipeline)

