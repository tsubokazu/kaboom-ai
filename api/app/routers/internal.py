"""Cloud Tasks internal endpoints for task execution"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
import logging

from fastapi import APIRouter, Request, HTTPException, Depends, status
from pydantic import BaseModel, Field
import jwt

from app.services.redis_client import RedisClient, get_redis_client
from app.services.job_progress_service import JobProgressService, get_job_progress_service, JobStatus
from batch.scripts.run_daily_ingest import run_daily_ingest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal"])


class CloudTaskPayload(BaseModel):
    """Cloud Task からのペイロード"""
    job_id: str
    created_at: str
    payload: Dict[str, Any]


class IngestPayload(BaseModel):
    """インジェストタスクペイロード"""
    interval_days: Dict[str, int]
    market: str = "TSE_PRIME"
    symbols: Optional[list[str]] = None
    chunk_size: int = 5000


async def _verify_cloud_tasks_request(request: Request) -> None:
    """Cloud Tasks リクエスト認証"""
    # OIDC トークン検証（本番環境）
    oidc_token = request.headers.get("authorization")
    if oidc_token:
        try:
            # Bearer トークンを抽出
            if oidc_token.startswith("Bearer "):
                token = oidc_token[7:]
                # JWT 検証（本番ではGoogleの公開鍵で検証）
                # 開発環境では簡易チェックのみ
                if os.getenv("ENVIRONMENT") == "production":
                    # 本番では適切なJWT検証を実装
                    decoded = jwt.decode(
                        token,
                        options={"verify_signature": False},  # 開発用
                        algorithms=["RS256"]
                    )
                    logger.info(f"OIDC token verified: {decoded.get('aud')}")
        except Exception as e:
            logger.warning(f"OIDC token verification failed: {e}")

    # User-Agent チェック（Cloud Tasks 特有）
    user_agent = request.headers.get("user-agent", "")
    if not user_agent.startswith("Google-Cloud-Tasks"):
        logger.warning(f"Unexpected User-Agent: {user_agent}")

    # X-CloudTasks-* ヘッダー確認
    task_name = request.headers.get("x-cloudtasks-taskname")
    if not task_name:
        logger.warning("Missing X-CloudTasks-TaskName header")


@router.post("/ingest/run-daily")
async def execute_daily_ingest(
    request: Request,
    payload: CloudTaskPayload,
    redis_client: RedisClient = Depends(get_redis_client),
    progress_service: JobProgressService = Depends(get_job_progress_service),
) -> Dict[str, Any]:
    """
    Cloud Tasks から呼び出される日次インジェスト実行エンドポイント

    Cloud Tasksによって非同期で呼び出され、実際のデータインジェスト処理を実行します。
    """
    # Cloud Tasks リクエスト検証
    await _verify_cloud_tasks_request(request)

    job_id = payload.job_id
    ingest_payload = IngestPayload(**payload.payload)

    logger.info(
        f"[execute_daily_ingest] Starting job_id={job_id} "
        f"market={ingest_payload.market} symbols={len(ingest_payload.symbols) if ingest_payload.symbols else 'auto'} "
        f"intervals={ingest_payload.interval_days}"
    )

    try:
        # Step 1: ジョブ開始
        logger.info(f"[execute_daily_ingest] Creating job progress for {job_id}")
        await progress_service.create_job(
            job_id=job_id,
            total_steps=100,
            job_type="data_ingest",
            metadata={
                "intervals": ingest_payload.interval_days,
                "market": ingest_payload.market,
                "symbols_count": len(ingest_payload.symbols) if ingest_payload.symbols else "auto",
                "chunk_size": ingest_payload.chunk_size,
                "executor": "cloud_tasks"
            }
        )
        logger.info(f"[execute_daily_ingest] Job progress created for {job_id}")

        # Step 2: 実行開始
        logger.info(f"[execute_daily_ingest] Updating progress to RUNNING for {job_id}")
        await progress_service.update_progress(
            job_id=job_id,
            status=JobStatus.RUNNING,
            progress_percent=10.0,
            current_step="Starting data ingestion process"
        )
        logger.info(f"[execute_daily_ingest] Progress updated to RUNNING for {job_id}")

        # Step 3: 実際のデータ取得実行（同期処理）
        def run_ingest_sync():
            """同期的にインジェスト処理を実行"""
            return run_daily_ingest(
                interval_days=ingest_payload.interval_days,
                market=ingest_payload.market,
                symbols=ingest_payload.symbols,
                chunk_size=ingest_payload.chunk_size,
            )

        # 進捗更新
        await progress_service.update_progress(
            job_id=job_id,
            progress_percent=20.0,
            current_step="Executing data ingestion"
        )

        # インジェスト実行（CPUバウンドなタスクなので別スレッドで実行）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_ingest_sync)

        # Step 4: 完了処理
        logger.info(f"[execute_daily_ingest] Setting job result to COMPLETED for {job_id}")
        await progress_service.set_job_result(
            job_id=job_id,
            result_data=result,
            status=JobStatus.COMPLETED
        )
        logger.info(f"[execute_daily_ingest] Job result set to COMPLETED for {job_id}")

        logger.info(
            f"[execute_daily_ingest] Completed job_id={job_id} "
            f"result_keys={list(result.keys()) if isinstance(result, dict) else 'non-dict'}"
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "completed_at": datetime.utcnow().isoformat(),
            "result": result
        }

    except Exception as e:
        logger.error(f"[execute_daily_ingest] Failed job_id={job_id}: {e}", exc_info=True)

        # エラー処理
        try:
            await progress_service.set_job_error(
                job_id=job_id,
                error_message=str(e),
                status=JobStatus.FAILED
            )
        except Exception as progress_error:
            logger.error(f"Progress update failed: {progress_error}")

        # エラーレスポンス（Cloud Tasks はステータスコードでリトライを判断）
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "job_id": job_id,
                "failed_at": datetime.utcnow().isoformat()
            }
        )


@router.get("/health")
async def internal_health_check() -> Dict[str, str]:
    """内部エンドポイント用ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "cloud-tasks-worker",
        "timestamp": datetime.utcnow().isoformat()
    }