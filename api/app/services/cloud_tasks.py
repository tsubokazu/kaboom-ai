"""Cloud Tasks 統合サービス - Celery からの移行用"""
import json
import os
import uuid
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from google.cloud import tasks_v2
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

class CloudTasksClient:
    """Cloud Tasks 統合クライアント"""

    def __init__(self):
        from app.config.settings import settings
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.CLOUD_TASKS_LOCATION
        self.service_url = settings.CLOUD_RUN_SERVICE_URL
        self.client = None

    def _get_client(self) -> tasks_v2.CloudTasksClient:
        """Cloud Tasks クライアント取得（遅延初期化）"""
        if self.client is None:
            self.client = tasks_v2.CloudTasksClient()
        return self.client

    def _get_queue_path(self, queue_name: str) -> str:
        """キューパスを構築"""
        return self._get_client().queue_path(
            self.project_id,
            self.location,
            queue_name
        )

    async def create_task(
        self,
        queue: str,
        url: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
        schedule_time: Optional[datetime] = None,
        timeout_seconds: int = 1800
    ) -> str:
        """
        Cloud Task を作成

        Args:
            queue: キュー名 (例: "ingest-jobs")
            url: ターゲットURL (例: "/internal/ingest/run-daily")
            payload: タスクペイロード
            task_id: カスタムタスクID（未指定時は自動生成）
            schedule_time: スケジュール時刻（未指定時は即座に実行）
            timeout_seconds: タイムアウト（デフォルト1時間）

        Returns:
            タスクID（ジョブIDとして使用）
        """
        try:
            client = self._get_client()
            queue_path = self._get_queue_path(queue)

            # タスクID生成
            if task_id is None:
                task_id = f"{queue}-{uuid.uuid4().hex}"

            # タスクペイロード準備
            task_payload = {
                "job_id": task_id,
                "created_at": datetime.utcnow().isoformat(),
                "payload": payload
            }

            # フルURL構築
            full_url = f"{self.service_url.rstrip('/')}{url}"

            # Cloud Task構築
            task = {
                "name": f"{queue_path}/tasks/{task_id}",
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": full_url,
                    "headers": {
                        "Content-Type": "application/json",
                    },
                    "body": json.dumps(task_payload, default=str).encode(),
                },
                "dispatch_deadline": timedelta(seconds=timeout_seconds)
            }

            # スケジュール時刻設定
            if schedule_time:
                task["schedule_time"] = schedule_time

            # タスク作成
            response = client.create_task(
                parent=queue_path,
                task=task
            )

            logger.info(
                f"Cloud Task created: {task_id} in queue {queue}, "
                f"target: {full_url}"
            )

            return task_id

        except google_exceptions.GoogleAPICallError as e:
            logger.error(f"Cloud Tasks API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Task creation failed: {e}")
            raise

    async def create_ingest_task(
        self,
        interval_days: Dict[str, int],
        market: str = "TSE_PRIME",
        symbols: Optional[list[str]] = None,
        chunk_size: int = 5000
    ) -> str:
        """
        データインジェストタスクを作成

        Returns:
            ジョブID
        """
        payload = {
            "interval_days": interval_days,
            "market": market,
            "symbols": symbols,
            "chunk_size": chunk_size
        }

        return await self.create_task(
            queue="ingest-jobs",
            url="/internal/ingest/run-daily",
            payload=payload,
            timeout_seconds=1800
        )

    async def get_task_status(self, queue: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスクステータス取得

        Note: Cloud Tasks API は実行中のタスクのステータス詳細を提供しません。
        実際のジョブステータスは Redis から取得する必要があります。
        """
        try:
            client = self._get_client()
            queue_path = self._get_queue_path(queue)
            task_path = f"{queue_path}/tasks/{task_id}"

            try:
                task = client.get_task(name=task_path)
                return {
                    "name": task.name,
                    "schedule_time": task.schedule_time,
                    "dispatch_deadline": task.dispatch_deadline,
                    "status": "queued"  # Cloud Tasks では詳細ステータス不明
                }
            except google_exceptions.NotFound:
                # タスクが見つからない = 実行済みまたは削除済み
                return None

        except Exception as e:
            logger.error(f"Task status retrieval failed: {e}")
            return None


# グローバル Cloud Tasks クライアントインスタンス
cloud_tasks_client = CloudTasksClient()


# FastAPI 依存性注入用
async def get_cloud_tasks_client() -> CloudTasksClient:
    """Cloud Tasks クライアント依存性注入"""
    return cloud_tasks_client