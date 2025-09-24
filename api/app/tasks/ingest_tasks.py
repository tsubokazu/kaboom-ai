"""データインジェスト関連のCeleryタスク定義。"""
from __future__ import annotations

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

    resolved_intervals = interval_days or dict(DEFAULT_INTERVAL_DAYS)
    logger.info(
        "[run_daily_ingest_task] job_id=%s market=%s symbols=%s intervals=%s chunk_size=%s",
        self.request.id,
        market,
        symbols[:5] if symbols else "<supabase>",
        resolved_intervals,
        chunk_size,
    )
    result = run_daily_ingest(
        interval_days=resolved_intervals,
        market=market,
        symbols=symbols,
        chunk_size=chunk_size,
    )
    logger.info(
        "[run_daily_ingest_task] job_id=%s completed result_keys=%s",
        self.request.id,
        list(result.keys()),
    )
    return result
