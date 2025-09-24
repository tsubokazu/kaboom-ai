#!/usr/bin/env python3
"""
Cloud Run対応Celeryワーカー - HTTPヘルスチェック統合版

Celeryワーカー + 軽量HTTPサーバーを同一プロセスで実行
Cloud RunのHTTPヘルスチェック要件を満たしつつCeleryワーカーを動作
"""

import asyncio
import logging
import os
import threading
import time
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from celery import Celery

logger = logging.getLogger(__name__)

# Celeryアプリをインポート
from app.tasks.celery_app import celery_app

class CeleryWorkerHealthServer:
    """Celeryワーカー + ヘルスチェック統合サーバー"""

    def __init__(self):
        self.celery_app = celery_app
        self.health_app = FastAPI(title="Celery Worker Health Server")
        self.worker = None
        self.worker_thread = None
        self.stats = {
            "started_at": time.time(),
            "processed_tasks": 0,
            "failed_tasks": 0,
            "status": "starting"
        }

        # ヘルスチェックエンドポイント設定
        self.setup_health_endpoints()

    def setup_health_endpoints(self):
        """ヘルスチェック用エンドポイントを設定"""

        @self.health_app.get("/health")
        @self.health_app.get("/healthz")
        async def health_check():
            """Cloud Run用ヘルスチェック"""
            return JSONResponse(
                status_code=200,
                content={
                    "status": "healthy",
                    "service": "celery-worker",
                    "uptime_seconds": int(time.time() - self.stats["started_at"]),
                    "worker_status": self.stats["status"],
                    "processed_tasks": self.stats["processed_tasks"],
                    "failed_tasks": self.stats["failed_tasks"]
                }
            )

        @self.health_app.get("/worker/stats")
        async def worker_stats():
            """Celeryワーカー統計情報"""
            return JSONResponse(content=self.stats)

        @self.health_app.get("/worker/inspect")
        async def worker_inspect():
            """Celeryワーカー詳細情報"""
            try:
                from celery import inspect
                i = inspect.Inspect(app=self.celery_app)
                active_tasks = i.active()
                reserved_tasks = i.reserved()

                return JSONResponse(content={
                    "active_tasks": active_tasks or {},
                    "reserved_tasks": reserved_tasks or {},
                    "worker_stats": self.stats
                })
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={"error": str(e)}
                )

    def start_celery_worker(self):
        """Celeryワーカーを開始"""
        try:
            logger.info("Starting Celery worker...")
            self.stats["status"] = "starting"

            # Celeryワーカー設定
            worker_args = [
                "--loglevel=info",
                "--queues=ingest,ai_analysis,backtest,market_data,notifications",
                "--concurrency=4",
                "--prefetch-multiplier=1"
            ]

            # カスタムワーカーイベント処理
            from celery import signals

            @signals.task_success.connect
            def task_success_handler(sender=None, result=None, **kwargs):
                self.stats["processed_tasks"] += 1

            @signals.task_failure.connect
            def task_failure_handler(sender=None, task_id=None, exception=None, einfo=None, **kwargs):
                self.stats["failed_tasks"] += 1

            @signals.worker_ready.connect
            def worker_ready_handler(sender=None, **kwargs):
                self.stats["status"] = "running"
                logger.info("Celery worker is ready")

            # Celeryワーカー実行
            self.worker = self.celery_app.Worker(
                loglevel='info',
                queues=['ingest', 'ai_analysis', 'backtest', 'market_data', 'notifications'],
                concurrency=4,
                prefetch_multiplier=1
            )

            self.worker.start()

        except Exception as e:
            logger.exception(f"Celery worker failed to start: {e}")
            self.stats["status"] = "failed"

    def start_health_server(self, port: int = 8080):
        """ヘルスチェックサーバーを開始"""
        try:
            logger.info(f"Starting health server on port {port}...")
            uvicorn.run(
                self.health_app,
                host="0.0.0.0",
                port=port,
                log_level="info",
                access_log=False
            )
        except Exception as e:
            logger.exception(f"Health server failed to start: {e}")

    def run(self):
        """Celeryワーカー + ヘルスサーバーを同時実行"""
        logger.info("Starting Celery Worker with Health Server...")

        # Celeryワーカーを別スレッドで開始
        self.worker_thread = threading.Thread(
            target=self.start_celery_worker,
            daemon=True
        )
        self.worker_thread.start()

        # メインスレッドでヘルスサーバーを実行
        # （Cloud RunはメインプロセスのHTTPサーバーを監視）
        port = int(os.getenv("PORT", 8080))
        self.start_health_server(port)

def main():
    """エントリーポイント"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    server = CeleryWorkerHealthServer()
    server.run()

if __name__ == "__main__":
    main()