"""
改良版データインジェストタスク - 進捗追跡統合

リアルタイム進捗更新・詳細状況報告を実装
"""
from __future__ import annotations

from typing import Dict, Optional, List
import asyncio
from functools import partial

from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.services.job_progress_service import JobProgressService, JobStatus
from batch.scripts.run_daily_ingest import DEFAULT_INTERVAL_DAYS, run_daily_ingest

logger = get_task_logger(__name__)


@celery_app.task(
    name="ingest.run_daily_enhanced",
    queue="ingest",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def run_daily_ingest_enhanced_task(
    self,
    interval_days: Optional[Dict[str, int]] = None,
    market: str = "TSE_PRIME",
    symbols: Optional[List[str]] = None,
    chunk_size: int = 5_000,
) -> Dict[str, object]:
    """
    進捗追跡付きデータインジェストタスク

    ベストプラクティス実装：
    - リアルタイム進捗更新
    - 詳細処理状況報告
    - エラーハンドリング強化
    - パフォーマンスメトリクス追跡
    """

    job_id = self.request.id
    resolved_intervals = interval_days or dict(DEFAULT_INTERVAL_DAYS)

    # 同期関数内で非同期処理を実行するためのヘルパー
    def run_async(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _async_task():
        from app.services.redis_client import get_redis_client

        # 進捗サービス初期化
        redis_client = await get_redis_client()
        progress_service = JobProgressService(redis_client)

        try:
            # Step 1: ジョブ初期化
            await progress_service.create_job(
                job_id=job_id,
                total_steps=100,
                job_type="data_ingest",
                metadata={
                    "intervals": resolved_intervals,
                    "market": market,
                    "symbols_count": len(symbols) if symbols else "auto",
                    "chunk_size": chunk_size
                }
            )

            # Step 2: 設定バリデーション
            await progress_service.update_progress(
                job_id=job_id,
                status=JobStatus.STARTING,
                progress_percent=5.0,
                current_step="Validating configuration and loading symbols",
                details={"phase": "initialization"}
            )

            logger.info(
                "[enhanced_ingest_task] job_id=%s market=%s intervals=%s",
                job_id, market, resolved_intervals
            )

            # Step 3: 実際のデータ取得開始
            await progress_service.update_progress(
                job_id=job_id,
                status=JobStatus.RUNNING,
                progress_percent=10.0,
                current_step="Starting data ingestion process",
                details={"phase": "data_processing"}
            )

            # 進捗コールバック付きでデータ取得実行
            progress_callback = partial(_create_progress_callback, progress_service, job_id)

            result = await _run_ingest_with_progress(
                resolved_intervals, market, symbols, chunk_size, progress_callback
            )

            # Step 4: 完了処理
            await progress_service.set_job_result(
                job_id=job_id,
                result_data=result,
                status=JobStatus.COMPLETED
            )

            logger.info(
                "[enhanced_ingest_task] job_id=%s completed successfully",
                job_id
            )

            return result

        except Exception as e:
            # エラー処理
            await progress_service.set_job_error(
                job_id=job_id,
                error_message=str(e),
                status=JobStatus.FAILED
            )

            logger.error(
                "[enhanced_ingest_task] job_id=%s failed: %s",
                job_id, str(e)
            )
            raise

    # 非同期処理を同期コンテキストで実行
    return run_async(_async_task())


async def _run_ingest_with_progress(
    interval_days: Dict[str, int],
    market: str,
    symbols: Optional[List[str]],
    chunk_size: int,
    progress_callback
) -> Dict[str, object]:
    """進捗コールバック付きでデータ取得を実行"""

    # カスタムバージョンのrun_daily_ingestを実装
    # 実際の処理中に進捗更新を行う

    from batch.pipeline.supabase_sector_loader import load_symbols_from_supabase
    from batch.config.loader import load_influx_config
    from batch.ingest.backfill_yf import INTERVAL_SPECS, fetch_symbol, dataframe_to_points, write_to_influx
    from influxdb_client_3 import InfluxDBClient3

    config = load_influx_config()
    symbol_list = symbols or load_symbols_from_supabase(market)

    if not symbol_list:
        raise RuntimeError("バックフィル対象の銘柄が取得できませんでした")

    total_operations = len(symbol_list) * len(interval_days)
    completed_operations = 0

    result = {
        "total_symbols": len(symbol_list),
        "intervals": {},
    }

    # 進捗報告: データ取得開始
    await progress_callback(
        progress_percent=15.0,
        current_step=f"Processing {len(symbol_list)} symbols across {len(interval_days)} intervals",
        details={"total_symbols": len(symbol_list), "total_operations": total_operations}
    )

    with InfluxDBClient3(
        host=config.host,
        token=config.token,
        org=config.org,
        timeout=30_000,
        max_retries=config.max_retries,
    ) as client:

        for interval_idx, (interval, days) in enumerate(interval_days.items()):
            spec = INTERVAL_SPECS.get(interval)
            if spec is None:
                logger.warning("interval=%s はサポートされていません。スキップします", interval)
                continue

            bucket = getattr(config, spec.default_bucket_attr, None)
            if not bucket:
                raise RuntimeError(f"InfluxConfigに {spec.default_bucket_attr} が設定されていません")

            interval_summary = {
                "bucket": bucket,
                "days_requested": days,
                "symbols_processed": 0,
                "points_written": 0,
                "failures": [],
            }

            # 進捗報告: インターバル開始
            base_progress = 15.0 + (interval_idx / len(interval_days)) * 70.0
            await progress_callback(
                progress_percent=base_progress,
                current_step=f"Processing interval {interval} ({days} days)",
                details={
                    "current_interval": interval,
                    "interval_progress": f"{interval_idx + 1}/{len(interval_days)}"
                }
            )

            for symbol_idx, symbol in enumerate(symbol_list):
                try:
                    df = fetch_symbol(symbol, interval, days, spec)
                    if df.empty:
                        continue

                    points = dataframe_to_points(df, symbol, spec.measurement)
                    written = write_to_influx(client, bucket, points, chunk_size)

                    interval_summary["symbols_processed"] += 1
                    interval_summary["points_written"] += written
                    completed_operations += 1

                    # 定期的な進捗報告（10銘柄ごと）
                    if symbol_idx % 10 == 0:
                        symbol_progress = (symbol_idx / len(symbol_list)) * (70.0 / len(interval_days))
                        current_progress = base_progress + symbol_progress

                        await progress_callback(
                            progress_percent=current_progress,
                            current_step=f"Processing {symbol} ({symbol_idx + 1}/{len(symbol_list)})",
                            details={
                                "current_symbol": symbol,
                                "current_interval": interval,
                                "symbols_completed": symbol_idx + 1,
                                "points_written": interval_summary["points_written"]
                            },
                            metrics={
                                "operations_completed": completed_operations,
                                "operations_total": total_operations,
                                "completion_rate": f"{completed_operations}/{total_operations}"
                            }
                        )

                except Exception as exc:
                    logger.exception("%s: interval=%s でエラーが発生しました", symbol, interval)
                    interval_summary["failures"].append({
                        "symbol": symbol,
                        "error": str(exc),
                    })

            result["intervals"][interval] = interval_summary

    # 最終進捗報告
    await progress_callback(
        progress_percent=90.0,
        current_step="Finalizing results and cleanup",
        details={"phase": "finalization"},
        metrics={
            "total_symbols_processed": result["total_symbols"],
            "total_intervals": len(result["intervals"])
        }
    )

    return result


async def _create_progress_callback(progress_service: JobProgressService, job_id: str, **kwargs):
    """進捗更新コールバック生成"""
    await progress_service.update_progress(job_id=job_id, **kwargs)