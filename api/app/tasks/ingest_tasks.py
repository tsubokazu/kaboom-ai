"""データインジェスト関連のCeleryタスク定義。"""
from __future__ import annotations

import asyncio
from typing import Dict, Optional

from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from batch.scripts.run_daily_ingest import DEFAULT_INTERVAL_DAYS, run_daily_ingest

logger = get_task_logger(__name__)


@celery_app.task(
    name="ingest.run_daily",
    queue="ingest",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_daily_ingest_task(
    self,
    interval_days: Optional[Dict[str, int]] = None,
    market: str = "TSE_PRIME",
    symbols: Optional[list[str]] = None,
    chunk_size: int = 5_000,
) -> Dict[str, object]:
    """Supabase銘柄の日次バックフィルをCeleryタスクとして実行する。"""

    job_id = self.request.id
    resolved_intervals = interval_days or dict(DEFAULT_INTERVAL_DAYS)

    logger.info(
        "[run_daily_ingest_task] job_id=%s market=%s symbols=%s intervals=%s chunk_size=%s",
        job_id,
        market,
        symbols[:5] if symbols else "<supabase>",
        resolved_intervals,
        chunk_size,
    )

    # 進捗追跡統合（非同期処理を同期的に実行）
    def run_with_progress():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run_ingest_with_progress(
                job_id, resolved_intervals, market, symbols, chunk_size
            ))
        finally:
            loop.close()

    try:
        result = run_with_progress()
        logger.info(
            "[run_daily_ingest_task] job_id=%s completed result_keys=%s",
            job_id,
            list(result.keys()),
        )
        return result
    except Exception as e:
        logger.error(
            "[run_daily_ingest_task] job_id=%s failed: %s",
            job_id, str(e)
        )
        raise


async def _run_ingest_with_progress(
    job_id: str,
    interval_days: Dict[str, int],
    market: str,
    symbols: Optional[list[str]],
    chunk_size: int
) -> Dict[str, object]:
    """進捗追跡付きでingest処理を実行"""

    try:
        # 進捗サービス初期化
        from app.services.job_progress_service import JobProgressService, JobStatus
        from app.services.redis_client import RedisClient

        # Celeryワーカー環境でRedisクライアント初期化
        redis_client = RedisClient()
        await redis_client.connect()
        progress_service = JobProgressService(redis_client)

        # Step 1: ジョブ開始
        await progress_service.create_job(
            job_id=job_id,
            total_steps=100,
            job_type="data_ingest",
            metadata={
                "intervals": interval_days,
                "market": market,
                "symbols_count": len(symbols) if symbols else "auto",
                "chunk_size": chunk_size
            }
        )

        # Step 2: 実行開始
        await progress_service.update_progress(
            job_id=job_id,
            status=JobStatus.RUNNING,
            progress_percent=10.0,
            current_step="Starting data ingestion process"
        )

        # Step 3: 実際のデータ取得実行
        result = run_daily_ingest(
            interval_days=interval_days,
            market=market,
            symbols=symbols,
            chunk_size=chunk_size,
        )

        # Step 4: 完了
        await progress_service.set_job_result(
            job_id=job_id,
            result_data=result,
            status=JobStatus.COMPLETED
        )

        return result

    except Exception as e:
        # エラー処理
        try:
            await progress_service.set_job_error(
                job_id=job_id,
                error_message=str(e),
                status=JobStatus.FAILED
            )
        except:
            pass  # 進捗更新エラーは無視

        raise
