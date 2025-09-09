"""
Celery アプリケーション設定 - AI分析・バックテスト・市場データ処理

Phase 2A: Celery統合とタスクワーカー
- AI分析の非同期処理（OpenRouter統合）
- バックテストジョブ実行
- 市場データ定期更新
- Redis結果配信・WebSocket通知
"""
import os
from datetime import timedelta
from celery import Celery
from kombu import Exchange, Queue

from app.config.settings import settings

# Celery アプリケーション初期化
celery_app = Celery(
    "kaboom_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.ai_analysis_tasks",
        "app.tasks.backtest_tasks", 
        "app.tasks.market_data_tasks",
        "app.tasks.notification_tasks"
    ]
)

# Celery設定
celery_app.conf.update(
    # タスク設定
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    
    # Worker設定
    worker_prefetch_multiplier=1,  # 1タスクずつ処理（AI分析の重い処理対応）
    worker_concurrency=4,          # 並行処理数（CPUコア数に応じて調整）
    task_acks_late=True,           # タスク完了後にACK送信
    
    # 結果設定
    result_expires=3600,           # 結果保持時間（1時間）
    result_persistent=True,        # 永続化
    
    # タスクタイムアウト設定
    task_soft_time_limit=300,      # ソフト制限（5分）
    task_time_limit=600,           # ハード制限（10分）
    
    # ルーティング設定（優先度別キュー）
    task_routes={
        "app.tasks.ai_analysis_tasks.*": {"queue": "ai_analysis"},
        "app.tasks.backtest_tasks.*": {"queue": "backtest"},
        "app.tasks.market_data_tasks.*": {"queue": "market_data"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"}
    },
    
    # キュー設定（優先度付き）
    task_default_queue="default",
    task_queues=(
        # 最高優先度: リアルタイム通知
        Queue(
            "notifications",
            Exchange("notifications"),
            routing_key="notifications",
            queue_arguments={"x-max-priority": 10}
        ),
        
        # 高優先度: 市場データ更新
        Queue(
            "market_data",
            Exchange("market_data"),
            routing_key="market_data", 
            queue_arguments={"x-max-priority": 8}
        ),
        
        # 中優先度: AI分析（リアルタイム要求）
        Queue(
            "ai_analysis",
            Exchange("ai_analysis"),
            routing_key="ai_analysis",
            queue_arguments={"x-max-priority": 6}
        ),
        
        # 低優先度: バックテスト（時間のかかる処理）
        Queue(
            "backtest",
            Exchange("backtest"),
            routing_key="backtest",
            queue_arguments={"x-max-priority": 4}
        ),
        
        # デフォルト
        Queue("default"),
    ),
    
    # 定期実行設定（Celery Beat）
    beat_schedule={
        # 市場データ定期更新（5分間隔）
        "update_market_data": {
            "task": "app.tasks.market_data_tasks.update_all_stock_prices",
            "schedule": timedelta(minutes=settings.MARKET_DATA_UPDATE_INTERVAL),
            "options": {"queue": "market_data"}
        },
        
        # システムメトリクス更新（30分間隔）  
        "collect_system_metrics": {
            "task": "app.tasks.market_data_tasks.collect_system_metrics",
            "schedule": timedelta(minutes=settings.SYSTEM_METRICS_UPDATE_INTERVAL),
            "options": {"queue": "market_data"}
        },
        
        # AI分析結果クリーンアップ（日次）
        "cleanup_ai_results": {
            "task": "app.tasks.ai_analysis_tasks.cleanup_expired_analysis",
            "schedule": timedelta(hours=24),
            "options": {"queue": "ai_analysis"}
        }
    }
)

# Redis接続健全性チェック
@celery_app.task(bind=True, name="health_check")
def health_check_task(self):
    """Celery Health Check タスク"""
    try:
        return {
            "status": "healthy",
            "task_id": self.request.id,
            "worker_id": self.request.hostname,
            "timestamp": "now"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "task_id": self.request.id
        }

# タスク実行前後のフック
@celery_app.task(bind=True)
def debug_task(self):
    """デバッグ用タスク"""
    print(f"Request: {self.request!r}")
    return {"message": "Debug task completed", "request_info": str(self.request)}


# Celeryアプリケーションの起動設定
if __name__ == "__main__":
    celery_app.start()