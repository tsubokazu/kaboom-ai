"""Data ingest orchestration endpoints."""
from __future__ import annotations

import asyncio
from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config.settings import settings
from batch.scripts.run_daily_ingest import DEFAULT_INTERVAL_DAYS, run_daily_ingest

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


class IngestJobResponse(BaseModel):
    job_id: str
    status: str
    requested_at: str


class IngestJobDetail(BaseModel):
    job_id: str
    status: str
    requested_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    intervals: Dict[str, int]
    market: str
    symbols: Optional[list[str]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock: asyncio.Lock = asyncio.Lock()


async def _require_ingest_token(x_ingest_token: Optional[str] = Header(None)) -> None:
    token = settings.INGEST_API_TOKEN
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingest API token is not configured",
        )
    if x_ingest_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest token")


async def _execute_ingest_job(
    job_id: str,
    *,
    interval_days: Dict[str, int],
    market: str,
    symbols: Optional[list[str]],
    chunk_size: int,
) -> None:
    async with _jobs_lock:
        _jobs[job_id]["status"] = "running"
        _jobs[job_id]["started_at"] = datetime.utcnow().isoformat() + "Z"

    try:
        result = await asyncio.to_thread(
            run_daily_ingest,
            interval_days,
            market,
            symbols,
            chunk_size,
        )
        async with _jobs_lock:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
            _jobs[job_id]["result"] = result
    except Exception as exc:  # pragma: no cover - 実行時例外
        async with _jobs_lock:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat() + "Z"
            _jobs[job_id]["error"] = str(exc)


@router.post("/run-daily", response_model=IngestJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_daily_ingest(
    payload: IngestRequest,
    x_ingest_token: Optional[str] = Header(None),
) -> IngestJobResponse:
    """Supabase銘柄を対象に日次バックフィルを非同期実行する。"""

    # デバッグ: トークン比較情報
    import os
    env_token = os.getenv("INGEST_API_TOKEN")
    settings_token = settings.INGEST_API_TOKEN

    if x_ingest_token != env_token:
        debug_info = {
            "received_token_full": x_ingest_token,
            "env_token_full": env_token,
            "settings_token_full": settings_token,
            "received_len": len(x_ingest_token) if x_ingest_token else 0,
            "env_len": len(env_token) if env_token else 0,
            "settings_len": len(settings_token) if settings_token else 0,
            "tokens_match": x_ingest_token == env_token,
            "request_received": datetime.utcnow().isoformat() + "Z"
        }
        raise HTTPException(status_code=401, detail=f"Debug auth info: {debug_info}")

    interval_days = payload.intervals or dict(DEFAULT_INTERVAL_DAYS)
    job_id = uuid.uuid4().hex
    requested_at = datetime.utcnow().isoformat() + "Z"

    async with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "requested_at": requested_at,
            "intervals": interval_days,
            "market": payload.market,
            "symbols": payload.symbols,
        }

    asyncio.create_task(
        _execute_ingest_job(
            job_id,
            interval_days=interval_days,
            market=payload.market,
            symbols=payload.symbols,
            chunk_size=payload.chunk_size,
        )
    )

    return IngestJobResponse(job_id=job_id, status="queued", requested_at=requested_at)


@router.get("/jobs/{job_id}", response_model=IngestJobDetail)
async def get_ingest_job(
    job_id: str,
    _: None = Depends(_require_ingest_token),
) -> IngestJobDetail:
    """実行中または完了済みジョブの状態を返す。"""

    async with _jobs_lock:
        job = _jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return IngestJobDetail(**job)


@router.get("/jobs", response_model=List[IngestJobDetail])
async def list_all_jobs(
    status: Optional[str] = None,
    limit: int = 10,
    _: None = Depends(_require_ingest_token),
) -> List[IngestJobDetail]:
    """全ジョブリストを取得（ステータスフィルタ・件数制限対応）"""

    async with _jobs_lock:
        jobs = list(_jobs.values())

    # ステータスフィルタ
    if status:
        jobs = [job for job in jobs if job.get("status") == status]

    # 最新順にソート
    jobs.sort(key=lambda x: x.get("requested_at", ""), reverse=True)

    # 件数制限
    jobs = jobs[:limit]

    return [IngestJobDetail(**job) for job in jobs]


@router.get("/jobs/stats")
async def get_job_stats(
    _: None = Depends(_require_ingest_token),
) -> Dict[str, Any]:
    """ジョブ統計情報を取得"""

    async with _jobs_lock:
        total_jobs = len(_jobs)
        status_counts = {}
        for job in _jobs.values():
            status = job.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "total_jobs": total_jobs,
        "status_breakdown": status_counts,
        "memory_usage_mb": len(str(_jobs)) / 1024 / 1024,  # 概算
        "active_jobs": status_counts.get("running", 0) + status_counts.get("queued", 0)
    }


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    _: None = Depends(_require_ingest_token),
) -> Dict[str, str]:
    """完了済みジョブを削除（メモリクリーンアップ）"""

    async with _jobs_lock:
        if job_id not in _jobs:
            raise HTTPException(status_code=404, detail="Job not found")

        job = _jobs[job_id]
        if job.get("status") in ["running", "queued"]:
            raise HTTPException(status_code=400, detail="Cannot delete active job")

        del _jobs[job_id]

    return {"message": f"Job {job_id} deleted successfully"}


@router.delete("/jobs")
async def cleanup_completed_jobs(
    _: None = Depends(_require_ingest_token),
) -> Dict[str, Any]:
    """完了済み・失敗ジョブを一括削除"""

    deleted_count = 0
    async with _jobs_lock:
        job_ids_to_delete = [
            job_id for job_id, job in _jobs.items()
            if job.get("status") in ["completed", "failed"]
        ]

        for job_id in job_ids_to_delete:
            del _jobs[job_id]
            deleted_count += 1

    return {
        "deleted_jobs": deleted_count,
        "remaining_jobs": len(_jobs),
        "message": f"Cleaned up {deleted_count} completed/failed jobs"
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
        "settings_debug": settings.DEBUG
    }
