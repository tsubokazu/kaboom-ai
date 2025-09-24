"""
ジョブ進捗追跡サービス - Celeryベストプラクティス実装

リアルタイム進捗更新・状態管理・WebSocket通知を提供
"""
from __future__ import annotations

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from app.services.redis_client import RedisClient


class JobStatus(Enum):
    """ジョブ状態定義"""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class JobProgress:
    """ジョブ進捗情報"""
    job_id: str
    status: JobStatus
    progress_percent: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None

    # 詳細進捗情報
    processing_details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


class JobProgressService:
    """ジョブ進捗管理サービス"""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.progress_key_prefix = "job:progress:"
        self.notification_channel = "job:notifications"

    async def create_job(
        self,
        job_id: str,
        total_steps: int = 100,
        job_type: str = "ingest",
        metadata: Optional[Dict[str, Any]] = None
    ) -> JobProgress:
        """新しいジョブ進捗を作成"""

        progress = JobProgress(
            job_id=job_id,
            status=JobStatus.QUEUED,
            total_steps=total_steps,
            started_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
            processing_details={
                "job_type": job_type,
                "metadata": metadata or {}
            }
        )

        await self._store_progress(progress)
        await self._notify_progress_update(progress)

        return progress

    async def update_progress(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress_percent: Optional[float] = None,
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> JobProgress:
        """ジョブ進捗を更新"""

        # 既存の進捗情報を取得
        progress = await self.get_job_progress(job_id)
        if not progress:
            raise ValueError(f"Job {job_id} not found")

        # 更新
        if status:
            progress.status = status
        if progress_percent is not None:
            progress.progress_percent = min(100.0, max(0.0, progress_percent))
        if current_step:
            progress.current_step = current_step
        if completed_steps is not None:
            progress.completed_steps = completed_steps
            # 自動計算: 完了ステップ数から進捗率を計算
            if progress.total_steps > 0:
                progress.progress_percent = (completed_steps / progress.total_steps) * 100

        progress.updated_at = datetime.utcnow().isoformat() + "Z"

        # 詳細情報・メトリクス更新
        if details:
            if not progress.processing_details:
                progress.processing_details = {}
            progress.processing_details.update(details)

        if metrics:
            if not progress.metrics:
                progress.metrics = {}
            progress.metrics.update(metrics)

        # 完了・失敗時の特別処理
        if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            progress.completed_at = progress.updated_at
            if status == JobStatus.COMPLETED:
                progress.progress_percent = 100.0

        await self._store_progress(progress)
        await self._notify_progress_update(progress)

        return progress

    async def set_job_result(
        self,
        job_id: str,
        result_data: Dict[str, Any],
        status: JobStatus = JobStatus.COMPLETED
    ) -> JobProgress:
        """ジョブ結果を設定"""

        progress = await self.get_job_progress(job_id)
        if not progress:
            raise ValueError(f"Job {job_id} not found")

        progress.result_data = result_data
        progress.status = status
        progress.progress_percent = 100.0
        progress.completed_at = datetime.utcnow().isoformat() + "Z"
        progress.updated_at = progress.completed_at

        await self._store_progress(progress)
        await self._notify_progress_update(progress)

        return progress

    async def set_job_error(
        self,
        job_id: str,
        error_message: str,
        status: JobStatus = JobStatus.FAILED
    ) -> JobProgress:
        """ジョブエラーを設定"""

        progress = await self.get_job_progress(job_id)
        if not progress:
            raise ValueError(f"Job {job_id} not found")

        progress.error_message = error_message
        progress.status = status
        progress.completed_at = datetime.utcnow().isoformat() + "Z"
        progress.updated_at = progress.completed_at

        await self._store_progress(progress)
        await self._notify_progress_update(progress)

        return progress

    async def get_job_progress(self, job_id: str) -> Optional[JobProgress]:
        """ジョブ進捗を取得"""

        key = f"{self.progress_key_prefix}{job_id}"
        data = await self.redis.client.get(key)

        if not data:
            return None

        try:
            progress_dict = json.loads(data)
            # EnumをStringから復元
            progress_dict["status"] = JobStatus(progress_dict["status"])
            return JobProgress(**progress_dict)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    async def list_active_jobs(self, limit: int = 50) -> List[JobProgress]:
        """アクティブなジョブ一覧を取得"""

        pattern = f"{self.progress_key_prefix}*"
        keys = await self.redis.client.keys(pattern)

        jobs = []
        for key in keys[:limit]:
            data = await self.redis.client.get(key)
            if data:
                try:
                    progress_dict = json.loads(data)
                    progress_dict["status"] = JobStatus(progress_dict["status"])
                    jobs.append(JobProgress(**progress_dict))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

        # 更新日時でソート（新しい順）
        jobs.sort(key=lambda x: x.updated_at or "", reverse=True)
        return jobs

    async def cleanup_old_jobs(self, retention_hours: int = 168) -> int:
        """古いジョブ情報をクリーンアップ（デフォルト7日）"""

        cutoff_time = time.time() - (retention_hours * 3600)
        pattern = f"{self.progress_key_prefix}*"
        keys = await self.redis.client.keys(pattern)

        deleted_count = 0
        for key in keys:
            data = await self.redis.client.get(key)
            if data:
                try:
                    progress_dict = json.loads(data)
                    updated_at = progress_dict.get("updated_at")
                    if updated_at:
                        job_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00')).timestamp()
                        if job_time < cutoff_time:
                            await self.redis.client.delete(key)
                            deleted_count += 1
                except (json.JSONDecodeError, TypeError, ValueError):
                    # 壊れたデータは削除
                    await self.redis.client.delete(key)
                    deleted_count += 1

        return deleted_count

    async def _store_progress(self, progress: JobProgress) -> None:
        """進捗情報をRedisに保存"""

        key = f"{self.progress_key_prefix}{progress.job_id}"

        # EnumをStringに変換
        progress_dict = asdict(progress)
        progress_dict["status"] = progress.status.value

        data = json.dumps(progress_dict, default=str, ensure_ascii=False)

        # 24時間のTTL設定
        await self.redis.client.setex(key, 86400, data)

    async def _notify_progress_update(self, progress: JobProgress) -> None:
        """進捗更新をWebSocket/Pub/Sub経由で通知"""

        notification = {
            "type": "job_progress_update",
            "job_id": progress.job_id,
            "status": progress.status.value,
            "progress_percent": progress.progress_percent,
            "current_step": progress.current_step,
            "timestamp": progress.updated_at
        }

        # Redis Pub/Subでリアルタイム通知
        await self.redis.client.publish(
            self.notification_channel,
            json.dumps(notification)
        )


# Dependency Injection用のシングルトン
_job_progress_service: Optional[JobProgressService] = None

async def get_job_progress_service() -> JobProgressService:
    """ジョブ進捗サービスのDI取得"""
    global _job_progress_service

    if _job_progress_service is None:
        from app.services.redis_client import redis_client
        _job_progress_service = JobProgressService(redis_client)

    return _job_progress_service