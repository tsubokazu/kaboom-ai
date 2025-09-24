# app/services/monitoring_service.py

import asyncio
import psutil
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

from app.services.redis_client import redis_client
from app.database.connection import check_database_health
from app.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)

class MetricType(str, Enum):
    SYSTEM = "system"
    DATABASE = "database"
    REDIS = "redis"
    API = "api"
    AI = "ai"
    TRADING = "trading"
    WEBSOCKET = "websocket"

class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemMetrics:
    """システムメトリクス"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_connections: int
    api_requests_per_minute: int
    ai_requests_count: int
    websocket_connections: int
    database_connections: int
    redis_memory_usage: float

@dataclass
class Alert:
    """システムアラート"""
    id: str
    level: AlertLevel
    message: str
    metric_type: MetricType
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class MonitoringService:
    """システム監視サービス"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.metrics_history: List[SystemMetrics] = []
        self.is_monitoring = False
        
        # アラート閾値設定
        self.thresholds = {
            "cpu_percent": {"warning": 70.0, "critical": 90.0},
            "memory_percent": {"warning": 80.0, "critical": 95.0},
            "disk_percent": {"warning": 85.0, "critical": 95.0},
            "api_response_time": {"warning": 2.0, "critical": 5.0},
            "websocket_connections": {"warning": 800, "critical": 950},
            "database_connections": {"warning": 80, "critical": 95},
            "ai_cost_per_hour": {"warning": 10.0, "critical": 25.0}
        }
    
    async def start_monitoring(self):
        """監視開始"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        logger.info("System monitoring started")
        
        # メトリクス収集タスク
        asyncio.create_task(self._metrics_collection_loop())
        
        # アラート処理タスク
        asyncio.create_task(self._alert_processing_loop())
    
    async def stop_monitoring(self):
        """監視停止"""
        self.is_monitoring = False
        logger.info("System monitoring stopped")
    
    async def _metrics_collection_loop(self):
        """メトリクス収集ループ"""
        while self.is_monitoring:
            try:
                metrics = await self.collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # 古いメトリクスを削除（24時間分保持）
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m.timestamp > cutoff_time
                ]
                
                # Redis にメトリクス保存
                await self._save_metrics_to_redis(metrics)
                
                # アラートチェック
                await self._check_alerts(metrics)
                
                # WebSocket配信
                await self._broadcast_metrics(metrics)
                
                await asyncio.sleep(30)  # 30秒間隔
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(60)  # エラー時は1分待機
    
    async def collect_system_metrics(self) -> SystemMetrics:
        """システムメトリクス収集"""
        
        # システムリソース
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # データベース接続数
        db_connections = await self._get_database_connections()
        
        # Redis メモリ使用量
        redis_memory = await self._get_redis_memory_usage()
        
        # API リクエスト数
        api_requests = await self._get_api_request_count()
        
        # WebSocket接続数
        ws_connections = await self._get_websocket_connections()
        
        # AI リクエスト数
        ai_requests = await self._get_ai_request_count()
        
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=(disk.used / disk.total) * 100,
            active_connections=len(psutil.net_connections()),
            api_requests_per_minute=api_requests,
            ai_requests_count=ai_requests,
            websocket_connections=ws_connections,
            database_connections=db_connections,
            redis_memory_usage=redis_memory
        )
    
    async def _get_database_connections(self) -> int:
        """データベース接続数取得"""
        try:
            health = await check_database_health()
            return health.get("active_connections", 0)
        except:
            return 0
    
    async def _get_redis_memory_usage(self) -> float:
        """Redis メモリ使用量取得"""
        try:
            info = await redis_client.info("memory")
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 1) or 1
            return (used_memory / max_memory) * 100
        except:
            return 0.0
    
    async def _get_api_request_count(self) -> int:
        """API リクエスト数取得"""
        try:
            # Redis から直近1分間のリクエスト数取得
            key = f"api_requests:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
            count = await redis_client.get(key)
            return int(count) if count else 0
        except:
            return 0
    
    async def _get_websocket_connections(self) -> int:
        """WebSocket接続数取得"""
        try:
            # WebSocketマネージャーから取得
            from app.websocket.manager import websocket_manager
            return len(websocket_manager.active_connections)
        except:
            return 0
    
    async def _get_ai_request_count(self) -> int:
        """AI リクエスト数取得"""
        try:
            # Redis から直近1時間のAIリクエスト数取得
            key = f"ai_requests:{datetime.utcnow().strftime('%Y%m%d%H')}"
            count = await redis_client.get(key)
            return int(count) if count else 0
        except:
            return 0
    
    async def _save_metrics_to_redis(self, metrics: SystemMetrics):
        """メトリクスをRedisに保存"""
        try:
            # Redis接続確認
            if not redis_client.client:
                await redis_client.connect()

            key = f"metrics:{metrics.timestamp.strftime('%Y%m%d%H%M')}"
            data = {
                "timestamp": metrics.timestamp.isoformat(),
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "disk_percent": metrics.disk_percent,
                "active_connections": metrics.active_connections,
                "api_requests_per_minute": metrics.api_requests_per_minute,
                "ai_requests_count": metrics.ai_requests_count,
                "websocket_connections": metrics.websocket_connections,
                "database_connections": metrics.database_connections,
                "redis_memory_usage": metrics.redis_memory_usage
            }

            await redis_client.set(key, json.dumps(data), expire=86400)  # 24時間保持
        except Exception as e:
            logger.error(f"Failed to save metrics to Redis: {e}")
    
    async def _check_alerts(self, metrics: SystemMetrics):
        """アラートチェック"""
        alerts_to_create = []
        
        # CPU使用率チェック
        if metrics.cpu_percent >= self.thresholds["cpu_percent"]["critical"]:
            alerts_to_create.append(self._create_alert(
                "CPU_CRITICAL", AlertLevel.CRITICAL, MetricType.SYSTEM,
                f"CPU使用率が危険水準: {metrics.cpu_percent:.1f}%",
                metrics.cpu_percent, self.thresholds["cpu_percent"]["critical"]
            ))
        elif metrics.cpu_percent >= self.thresholds["cpu_percent"]["warning"]:
            alerts_to_create.append(self._create_alert(
                "CPU_WARNING", AlertLevel.WARNING, MetricType.SYSTEM,
                f"CPU使用率が高い: {metrics.cpu_percent:.1f}%",
                metrics.cpu_percent, self.thresholds["cpu_percent"]["warning"]
            ))
        
        # メモリ使用率チェック
        if metrics.memory_percent >= self.thresholds["memory_percent"]["critical"]:
            alerts_to_create.append(self._create_alert(
                "MEMORY_CRITICAL", AlertLevel.CRITICAL, MetricType.SYSTEM,
                f"メモリ使用率が危険水準: {metrics.memory_percent:.1f}%",
                metrics.memory_percent, self.thresholds["memory_percent"]["critical"]
            ))
        elif metrics.memory_percent >= self.thresholds["memory_percent"]["warning"]:
            alerts_to_create.append(self._create_alert(
                "MEMORY_WARNING", AlertLevel.WARNING, MetricType.SYSTEM,
                f"メモリ使用率が高い: {metrics.memory_percent:.1f}%",
                metrics.memory_percent, self.thresholds["memory_percent"]["warning"]
            ))
        
        # ディスク使用率チェック
        if metrics.disk_percent >= self.thresholds["disk_percent"]["critical"]:
            alerts_to_create.append(self._create_alert(
                "DISK_CRITICAL", AlertLevel.CRITICAL, MetricType.SYSTEM,
                f"ディスク使用率が危険水準: {metrics.disk_percent:.1f}%",
                metrics.disk_percent, self.thresholds["disk_percent"]["critical"]
            ))
        elif metrics.disk_percent >= self.thresholds["disk_percent"]["warning"]:
            alerts_to_create.append(self._create_alert(
                "DISK_WARNING", AlertLevel.WARNING, MetricType.SYSTEM,
                f"ディスク使用率が高い: {metrics.disk_percent:.1f}%",
                metrics.disk_percent, self.thresholds["disk_percent"]["warning"]
            ))
        
        # WebSocket接続数チェック
        if metrics.websocket_connections >= self.thresholds["websocket_connections"]["critical"]:
            alerts_to_create.append(self._create_alert(
                "WS_CONNECTIONS_CRITICAL", AlertLevel.CRITICAL, MetricType.WEBSOCKET,
                f"WebSocket接続数が上限近く: {metrics.websocket_connections}",
                metrics.websocket_connections, self.thresholds["websocket_connections"]["critical"]
            ))
        elif metrics.websocket_connections >= self.thresholds["websocket_connections"]["warning"]:
            alerts_to_create.append(self._create_alert(
                "WS_CONNECTIONS_WARNING", AlertLevel.WARNING, MetricType.WEBSOCKET,
                f"WebSocket接続数が多い: {metrics.websocket_connections}",
                metrics.websocket_connections, self.thresholds["websocket_connections"]["warning"]
            ))
        
        # アラート追加
        for alert in alerts_to_create:
            await self._add_alert(alert)
    
    def _create_alert(self, alert_id: str, level: AlertLevel, metric_type: MetricType,
                     message: str, value: float, threshold: float) -> Alert:
        """アラート作成"""
        return Alert(
            id=f"{alert_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            level=level,
            message=message,
            metric_type=metric_type,
            value=value,
            threshold=threshold,
            timestamp=datetime.utcnow()
        )
    
    async def _add_alert(self, alert: Alert):
        """アラート追加"""
        # 重複チェック
        existing_alert = next(
            (a for a in self.alerts if a.message == alert.message and not a.resolved),
            None
        )
        
        if existing_alert:
            return  # 重複アラートはスキップ
        
        self.alerts.append(alert)
        logger.warning(f"Alert created: {alert.level.value.upper()} - {alert.message}")
        
        # Redis に保存
        await self._save_alert_to_redis(alert)
        
        # WebSocket配信
        await self._broadcast_alert(alert)
    
    async def _save_alert_to_redis(self, alert: Alert):
        """アラートをRedisに保存"""
        try:
            key = f"alert:{alert.id}"
            data = {
                "id": alert.id,
                "level": alert.level.value,
                "message": alert.message,
                "metric_type": alert.metric_type.value,
                "value": alert.value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved
            }
            
            # Redis接続確認
            if not redis_client.client:
                await redis_client.connect()

            await redis_client.set(key, json.dumps(data), expire=604800)  # 7日間保持
        except Exception as e:
            logger.error(f"Failed to save alert to Redis: {e}")
    
    async def _broadcast_metrics(self, metrics: SystemMetrics):
        """メトリクスをWebSocketで配信"""
        try:
            # Redis接続確認
            if not redis_client.client:
                await redis_client.connect()

            await redis_client.publish("system_metrics", json.dumps({
                "type": "metrics",
                "data": {
                    "timestamp": metrics.timestamp.isoformat(),
                    "cpu_percent": metrics.cpu_percent,
                    "memory_percent": metrics.memory_percent,
                    "disk_percent": metrics.disk_percent,
                    "active_connections": metrics.active_connections,
                    "api_requests_per_minute": metrics.api_requests_per_minute,
                    "ai_requests_count": metrics.ai_requests_count,
                    "websocket_connections": metrics.websocket_connections,
                    "database_connections": metrics.database_connections,
                    "redis_memory_usage": metrics.redis_memory_usage
                }
            }))
        except Exception as e:
            logger.error(f"Failed to broadcast metrics: {e}")
    
    async def _broadcast_alert(self, alert: Alert):
        """アラートをWebSocketで配信"""
        try:
            # Redis接続確認
            if not redis_client.client:
                await redis_client.connect()

            await redis_client.publish("system_alerts", json.dumps({
                "type": "alert",
                "data": {
                    "id": alert.id,
                    "level": alert.level.value,
                    "message": alert.message,
                    "metric_type": alert.metric_type.value,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "timestamp": alert.timestamp.isoformat()
                }
            }))
        except Exception as e:
            logger.error(f"Failed to broadcast alert: {e}")
    
    async def _alert_processing_loop(self):
        """アラート処理ループ"""
        while self.is_monitoring:
            try:
                # 自動解決チェック
                await self._check_alert_resolution()
                
                # 重要アラートの通知処理
                await self._process_critical_alerts()
                
                await asyncio.sleep(60)  # 1分間隔
                
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
                await asyncio.sleep(120)  # エラー時は2分待機
    
    async def _check_alert_resolution(self):
        """アラート自動解決チェック"""
        current_metrics = self.metrics_history[-1] if self.metrics_history else None
        if not current_metrics:
            return
        
        for alert in self.alerts:
            if alert.resolved:
                continue
            
            resolved = False
            
            # CPU アラート解決チェック
            if "CPU" in alert.id and current_metrics.cpu_percent < alert.threshold * 0.9:
                resolved = True
            
            # メモリ アラート解決チェック
            elif "MEMORY" in alert.id and current_metrics.memory_percent < alert.threshold * 0.9:
                resolved = True
            
            # ディスク アラート解決チェック
            elif "DISK" in alert.id and current_metrics.disk_percent < alert.threshold * 0.9:
                resolved = True
            
            # WebSocket アラート解決チェック
            elif "WS_CONNECTIONS" in alert.id and current_metrics.websocket_connections < alert.threshold * 0.9:
                resolved = True
            
            if resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                logger.info(f"Alert resolved: {alert.id}")
                
                # Redis 更新
                await self._save_alert_to_redis(alert)
                
                # WebSocket配信
                await self._broadcast_alert_resolution(alert)
    
    async def _broadcast_alert_resolution(self, alert: Alert):
        """アラート解決をWebSocketで配信"""
        try:
            # Redis接続確認
            if not redis_client.client:
                await redis_client.connect()

            await redis_client.publish("system_alerts", json.dumps({
                "type": "alert_resolved",
                "data": {
                    "id": alert.id,
                    "message": alert.message,
                    "resolved_at": alert.resolved_at.isoformat()
                }
            }))
        except Exception as e:
            logger.error(f"Failed to broadcast alert resolution: {e}")
    
    async def _process_critical_alerts(self):
        """重要アラート処理"""
        critical_alerts = [
            a for a in self.alerts 
            if a.level == AlertLevel.CRITICAL and not a.resolved
        ]
        
        if not critical_alerts:
            return
        
        # 重要アラートのログ出力
        for alert in critical_alerts:
            logger.critical(f"CRITICAL ALERT: {alert.message}")
        
        # TODO: メール通知、Slack通知などの実装
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボード表示用データ取得"""
        if not self.metrics_history:
            return {"error": "No metrics data available"}
        
        latest_metrics = self.metrics_history[-1]
        active_alerts = [a for a in self.alerts if not a.resolved]
        
        # 過去1時間のメトリクス
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp > one_hour_ago
        ]
        
        return {
            "current_status": {
                "cpu_percent": latest_metrics.cpu_percent,
                "memory_percent": latest_metrics.memory_percent,
                "disk_percent": latest_metrics.disk_percent,
                "active_connections": latest_metrics.active_connections,
                "websocket_connections": latest_metrics.websocket_connections,
                "database_connections": latest_metrics.database_connections,
                "redis_memory_usage": latest_metrics.redis_memory_usage
            },
            "active_alerts": [
                {
                    "id": a.id,
                    "level": a.level.value,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in active_alerts
            ],
            "metrics_history": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "cpu_percent": m.cpu_percent,
                    "memory_percent": m.memory_percent,
                    "api_requests_per_minute": m.api_requests_per_minute,
                    "websocket_connections": m.websocket_connections
                }
                for m in recent_metrics[-60:]  # 最新60ポイント
            ],
            "system_health": self._calculate_system_health(),
            "uptime": self._get_system_uptime(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _calculate_system_health(self) -> str:
        """システム健康状態計算"""
        if not self.metrics_history:
            return "unknown"
        
        latest = self.metrics_history[-1]
        critical_alerts = len([a for a in self.alerts if a.level == AlertLevel.CRITICAL and not a.resolved])
        warning_alerts = len([a for a in self.alerts if a.level == AlertLevel.WARNING and not a.resolved])
        
        if critical_alerts > 0 or latest.cpu_percent > 90 or latest.memory_percent > 95:
            return "critical"
        elif warning_alerts > 0 or latest.cpu_percent > 70 or latest.memory_percent > 80:
            return "warning"
        else:
            return "healthy"
    
    def _get_system_uptime(self) -> str:
        """システム稼働時間取得"""
        try:
            uptime_seconds = psutil.boot_time()
            uptime_delta = datetime.now() - datetime.fromtimestamp(uptime_seconds)
            
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            return f"{days}日 {hours}時間 {minutes}分"
        except:
            return "不明"

# グローバルインスタンス
monitoring_service = MonitoringService()