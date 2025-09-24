"""Data ingest orchestration endpoints backed by Celery."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.services.redis_client import RedisClient, get_redis_client
from app.services.job_progress_service import JobProgressService, get_job_progress_service
from app.tasks.celery_app import celery_app
from app.tasks.ingest_tasks import run_daily_ingest_task
from batch.scripts.run_daily_ingest import DEFAULT_INTERVAL_DAYS

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingest"])


class IngestRequest(BaseModel):
    intervals: Optional[Dict[str, int]] = Field(
        default=None,
        description="interval=daysの辞書形式。未指定の場合はデフォルト設定を使用",
    )
    market: str = Field(default="TSE_PRIME", description="Supabaseのmarketフィルタ")
    symbols: Optional[list[str]] = Field(
        default=None,
        description="明示的に対象シンボルを指定。指定しない場合はSupabaseから取得",
    )
    chunk_size: int = Field(default=5_000, ge=500, description="InfluxDB書き込み時のバッチサイズ")

REDIS_JOB_META_PREFIX = "ingest:job:"
REDIS_JOB_LIST_KEY = "ingest:jobs"
JOB_METADATA_TTL_SECONDS = 7 * 24 * 3600  # 7日保持


class IngestJobResponse(BaseModel):
    job_id: str
    status: str
    requested_at: str


class IngestJobDetail(BaseModel):
    job_id: str
    status: str
    requested_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    intervals: Dict[str, int]
    market: str
    symbols: Optional[list[str]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # Progress tracking integration
    progress_percent: Optional[float] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: Optional[int] = None
    processing_details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


async def _require_ingest_token(x_ingest_token: Optional[str] = Header(None)) -> None:
    token = settings.INGEST_API_TOKEN
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingest API token is not configured",
        )
    if x_ingest_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest token")


def _redis_job_key(job_id: str) -> str:
    return f"{REDIS_JOB_META_PREFIX}{job_id}"


def _map_state_to_status(state: str) -> str:
    normalized = (state or "").upper()
    if normalized == "PENDING":
        return "queued"
    if normalized in {"RECEIVED", "STARTED"}:
        return "running"
    if normalized == "RETRY":
        return "retry"
    if normalized in {"SUCCESS", "COMPLETED"}:
        return "completed"
    if normalized == "FAILURE":
        return "failed"
    if normalized == "REVOKED":
        return "revoked"
    return normalized.lower() or "unknown"


async def _store_job_metadata(redis_client: RedisClient, payload: Dict[str, Any]) -> None:
    if not redis_client.client:
        await redis_client.connect()
    job_id = payload["job_id"]
    meta_key = _redis_job_key(job_id)
    encoded = json.dumps(payload, ensure_ascii=False, default=str)
    await redis_client.client.set(meta_key, encoded, ex=JOB_METADATA_TTL_SECONDS)
    await redis_client.client.lpush(REDIS_JOB_LIST_KEY, job_id)
    # 古い履歴を削除（直近100件保持）
    await redis_client.client.ltrim(REDIS_JOB_LIST_KEY, 0, 99)


async def _load_job_metadata(redis_client: RedisClient, job_id: str) -> Optional[Dict[str, Any]]:
    if not redis_client.client:
        await redis_client.connect()
    raw = await redis_client.client.get(_redis_job_key(job_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def _remove_job_metadata(redis_client: RedisClient, job_id: str) -> None:
    if not redis_client.client:
        await redis_client.connect()
    await redis_client.client.delete(_redis_job_key(job_id))
    await redis_client.client.lrem(REDIS_JOB_LIST_KEY, 0, job_id)


async def _build_job_detail(
    job_id: str,
    redis_client: RedisClient,
    *,
    allow_missing: bool = False,
    progress_service: Optional[JobProgressService] = None,
) -> Optional[IngestJobDetail]:
    async_result = AsyncResult(job_id, app=celery_app)
    metadata = await _load_job_metadata(redis_client, job_id)

    if metadata is None and async_result.state == "PENDING" and not allow_missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if metadata is None and allow_missing:
        if async_result.state == "PENDING":
            return None
        metadata = {
            "job_id": job_id,
            "requested_at": None,
            "intervals": {},
            "market": "TSE_PRIME",
            "symbols": None,
        }

    status = _map_state_to_status(async_result.state)
    completed_at = None
    if status == "completed" and async_result.date_done:
        completed_at = async_result.date_done.isoformat()

    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    if status == "completed":
        try:
            result_data = async_result.result
            if isinstance(result_data, dict):
                result = result_data
            else:
                result = json.loads(json.dumps(result_data, default=str))
        except Exception:  # noqa: BLE001 - 変換時は失敗しても無視
            result = None
    elif status in {"failed", "revoked"}:
        try:
            error_obj = async_result.result
            error = str(error_obj) if error_obj is not None else async_result.traceback
        except Exception:  # noqa: BLE001
            error = async_result.traceback

    # Progress tracking integration
    progress_percent = None
    current_step = None
    total_steps = None
    completed_steps = None
    processing_details = None
    metrics = None

    if progress_service:
        try:
            progress_info = await progress_service.get_job_progress(job_id)
            if progress_info:
                progress_percent = progress_info.progress_percent
                current_step = progress_info.current_step
                total_steps = progress_info.total_steps
                completed_steps = progress_info.completed_steps
                processing_details = progress_info.processing_details
                metrics = progress_info.metrics
        except Exception:
            # Progress情報の取得に失敗してもメインレスポンスには影響しない
            pass

    return IngestJobDetail(
        job_id=job_id,
        status=status,
        requested_at=metadata.get("requested_at"),
        started_at=metadata.get("started_at"),
        completed_at=completed_at,
        intervals=metadata.get("intervals", {}),
        market=metadata.get("market", "TSE_PRIME"),
        symbols=metadata.get("symbols"),
        result=result,
        error=error,
        progress_percent=progress_percent,
        current_step=current_step,
        total_steps=total_steps,
        completed_steps=completed_steps,
        processing_details=processing_details,
        metrics=metrics,
    )


@router.post("/run-daily", response_model=IngestJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_daily_ingest(
    payload: IngestRequest,
    x_ingest_token: Optional[str] = Header(None),
    redis_client: RedisClient = Depends(get_redis_client),
) -> IngestJobResponse:
    """Supabase銘柄を対象に日次バックフィルを非同期実行する。"""

    await _require_ingest_token(x_ingest_token)

    interval_days = payload.intervals or dict(DEFAULT_INTERVAL_DAYS)
    requested_at = datetime.utcnow().isoformat() + "Z"

    # Celeryタスクとして実行（適切なキュー管理）
    task = run_daily_ingest_task.delay(
        interval_days=interval_days,
        market=payload.market,
        symbols=payload.symbols,
        chunk_size=payload.chunk_size,
    )
    job_id = task.id
    metadata = {
        "job_id": job_id,
        "status": "queued",
        "requested_at": requested_at,
        "intervals": interval_days,
        "market": payload.market,
        "symbols": payload.symbols,
        "chunk_size": payload.chunk_size,
    }
    await _store_job_metadata(redis_client, metadata)

    return IngestJobResponse(job_id=job_id, status="queued", requested_at=requested_at)


@router.get("/jobs", response_model=List[IngestJobDetail])
async def list_all_jobs(
    status: Optional[str] = None,
    limit: int = 10,
    _: None = Depends(_require_ingest_token),
    redis_client: RedisClient = Depends(get_redis_client),
    progress_service: JobProgressService = Depends(get_job_progress_service),
) -> List[IngestJobDetail]:
    """全ジョブリストを取得（ステータスフィルタ・件数制限対応）"""

    if limit <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="limit must be positive")

    if not redis_client.client:
        await redis_client.connect()

    # 余裕を持って取得し、フィルタ後に切り詰め
    raw_ids = await redis_client.client.lrange(REDIS_JOB_LIST_KEY, 0, max(99, limit * 5))

    jobs: List[IngestJobDetail] = []
    for job_id in raw_ids:
        detail = await _build_job_detail(job_id, redis_client, allow_missing=True, progress_service=progress_service)
        if not detail:
            continue
        if status and detail.status != status:
            continue
        jobs.append(detail)
        if len(jobs) >= limit:
            break

    return jobs


@router.get("/jobs/{job_id}", response_model=IngestJobDetail)
async def get_ingest_job(
    job_id: str,
    _: None = Depends(_require_ingest_token),
    redis_client: RedisClient = Depends(get_redis_client),
    progress_service: JobProgressService = Depends(get_job_progress_service),
) -> IngestJobDetail:
    """実行中または完了済みジョブの状態を返す（進捗情報統合）。"""

    detail = await _build_job_detail(job_id, redis_client, progress_service=progress_service)
    return detail


@router.get("/jobs/stats")
async def get_job_stats(
    _: None = Depends(_require_ingest_token),
    redis_client: RedisClient = Depends(get_redis_client),
    progress_service: JobProgressService = Depends(get_job_progress_service),
) -> Dict[str, Any]:
    """ジョブ統計情報を取得"""

    if not redis_client.client:
        await redis_client.connect()

    raw_ids = await redis_client.client.lrange(REDIS_JOB_LIST_KEY, 0, 99)
    total_jobs = len(raw_ids)
    status_counts: Dict[str, int] = {}

    for job_id in raw_ids:
        detail = await _build_job_detail(job_id, redis_client, allow_missing=True, progress_service=progress_service)
        if not detail:
            continue
        status_counts[detail.status] = status_counts.get(detail.status, 0) + 1

    active_jobs = status_counts.get("running", 0) + status_counts.get("queued", 0) + status_counts.get("retry", 0)

    return {
        "total_jobs": total_jobs,
        "status_breakdown": status_counts,
        "active_jobs": active_jobs,
    }


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    _: None = Depends(_require_ingest_token),
    redis_client: RedisClient = Depends(get_redis_client),
) -> Dict[str, str]:
    """完了済みジョブを削除（メモリクリーンアップ）"""

    async_result = AsyncResult(job_id, app=celery_app)
    status = _map_state_to_status(async_result.state)

    if status in {"queued", "running", "retry"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete active job")

    if status == "unknown" and not await _load_job_metadata(redis_client, job_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    async_result.forget()
    await _remove_job_metadata(redis_client, job_id)

    return {"message": f"Job {job_id} deleted successfully"}


@router.delete("/jobs")
async def cleanup_completed_jobs(
    _: None = Depends(_require_ingest_token),
    redis_client: RedisClient = Depends(get_redis_client),
) -> Dict[str, Any]:
    """完了済み・失敗ジョブを一括削除"""

    if not redis_client.client:
        await redis_client.connect()

    raw_ids = await redis_client.client.lrange(REDIS_JOB_LIST_KEY, 0, 99)
    deleted_count = 0

    for job_id in raw_ids:
        async_result = AsyncResult(job_id, app=celery_app)
        status = _map_state_to_status(async_result.state)
        if status not in {"completed", "failed", "revoked"}:
            continue
        async_result.forget()
        await _remove_job_metadata(redis_client, job_id)
        deleted_count += 1

    remaining = await redis_client.client.lrange(REDIS_JOB_LIST_KEY, 0, 99)

    return {
        "deleted_jobs": deleted_count,
        "remaining_jobs": len(remaining),
        "message": f"Cleaned up {deleted_count} completed/failed jobs",
    }


@router.get("/debug/token-info")
async def debug_token_info():
    """デバッグ用: 環境変数の設定状況を確認（本番では削除）"""
    import os

    token = settings.INGEST_API_TOKEN
    env_token = os.getenv("INGEST_API_TOKEN")

    return {
        "settings_token_configured": token is not None,
        "settings_token_length": len(token) if token else 0,
        "settings_token_prefix": token[:25] + "..." if token and len(token) > 25 else token,
        "env_token_configured": env_token is not None,
        "env_token_length": len(env_token) if env_token else 0,
        "env_token_prefix": env_token[:25] + "..." if env_token and len(env_token) > 25 else env_token,
        "tokens_match": token == env_token if token and env_token else False,
        "settings_debug": settings.DEBUG,
    }
