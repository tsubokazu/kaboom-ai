"""
通知タスク - システム通知・メール配信・プッシュ通知

機能:
- WebSocket経由リアルタイム通知
- メール通知（重要なアラート）
- プッシュ通知（モバイルアプリ用）
- 通知履歴管理
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.tasks.celery_app import celery_app
from app.services.redis_client import get_redis_client
from app.websocket.manager import websocket_manager
from app.config.settings import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="notifications.send_realtime_notification",
    queue="notifications", 
    soft_time_limit=30,
    time_limit=60
)
def send_realtime_notification_task(
    self, 
    notification_data: Dict[str, Any], 
    target_users: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    リアルタイムWebSocket通知タスク
    
    Args:
        notification_data: {
            "title": "通知タイトル",
            "message": "通知メッセージ", 
            "level": "info|warning|error|success",
            "category": "price_alert|system|trading",
            "data": {...}  # 追加データ
        }
        target_users: 対象ユーザーID列表（Noneの場合は全体配信）
    """
    try:
        # 通知をWebSocket経由で配信
        result = asyncio.run(_send_websocket_notification(notification_data, target_users))
        
        # 通知履歴を保存
        asyncio.run(_save_notification_history(
            notification_data, 
            target_users, 
            self.request.id
        ))
        
        return {
            "status": "success",
            "task_id": self.request.id,
            "recipients": result.get("recipients", 0),
            "notification_type": "websocket",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Realtime notification task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "task_id": self.request.id
        }


@celery_app.task(
    bind=True,
    name="notifications.send_email_notification",
    queue="notifications",
    soft_time_limit=60,
    time_limit=120,
    retry_kwargs={"max_retries": 3, "countdown": 300}
)
def send_email_notification_task(
    self,
    email_data: Dict[str, Any],
    recipient_emails: List[str]
) -> Dict[str, Any]:
    """
    メール通知タスク（重要アラート用）
    
    Args:
        email_data: {
            "subject": "件名",
            "message": "本文",
            "html_content": "<html>...",  # オプション
            "category": "alert|report|system"
        }
        recipient_emails: 送信先メールアドレス列表
    """
    try:
        sent_count = asyncio.run(_send_email_notifications(email_data, recipient_emails))
        
        # 送信履歴保存
        asyncio.run(_save_email_history(
            email_data,
            recipient_emails, 
            sent_count,
            self.request.id
        ))
        
        return {
            "status": "success",
            "task_id": self.request.id,
            "sent_count": sent_count,
            "total_recipients": len(recipient_emails),
            "notification_type": "email"
        }
        
    except Exception as e:
        logger.error(f"Email notification task failed: {e}")
        
        # リトライ実行
        if self.request.retries < self.retry_kwargs['max_retries']:
            raise self.retry(exc=e)
        
        return {
            "status": "error",
            "error": str(e),
            "task_id": self.request.id
        }


@celery_app.task(
    bind=True,
    name="notifications.send_batch_notifications",
    queue="notifications",
    soft_time_limit=180,
    time_limit=300
)
def send_batch_notifications_task(
    self,
    notification_batch: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    バッチ通知タスク（大量通知の効率的処理）
    
    Args:
        notification_batch: [
            {
                "type": "websocket|email|push",
                "data": {...},
                "targets": [...]
            }, ...
        ]
    """
    try:
        results = asyncio.run(_process_batch_notifications(notification_batch))
        
        # バッチ処理結果をまとめる
        total_sent = sum(r.get("sent_count", 0) for r in results)
        failed_count = len([r for r in results if r.get("status") == "error"])
        
        return {
            "status": "success",
            "task_id": self.request.id,
            "batch_size": len(notification_batch),
            "total_sent": total_sent,
            "failed_count": failed_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch notifications task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "task_id": self.request.id
        }


@celery_app.task(name="notifications.cleanup_notification_history", queue="notifications")
def cleanup_notification_history_task() -> Dict[str, Any]:
    """通知履歴クリーンアップタスク（古い履歴削除）"""
    try:
        cleanup_result = asyncio.run(_cleanup_old_notifications())
        
        return {
            "status": "success",
            "cleaned_notifications": cleanup_result.get("cleaned_count", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Notification cleanup task failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(
    name="notifications.daily_summary_report",
    queue="notifications",
    soft_time_limit=300,
    time_limit=600
)
def daily_summary_report_task() -> Dict[str, Any]:
    """日次サマリーレポート通知タスク"""
    try:
        report_data = asyncio.run(_generate_daily_summary())
        
        # 管理者ユーザーに配信
        admin_users = asyncio.run(_get_admin_users())
        
        for admin_user in admin_users:
            asyncio.run(_send_websocket_notification({
                "title": "日次システムサマリー",
                "message": "システム運用状況の日次レポートが生成されました",
                "level": "info",
                "category": "system",
                "data": report_data
            }, [admin_user["user_id"]]))
        
        return {
            "status": "success",
            "report_generated": True,
            "admin_recipients": len(admin_users),
            "report_data": report_data
        }
        
    except Exception as e:
        logger.error(f"Daily summary report task failed: {e}")
        return {"status": "error", "error": str(e)}


# ===================================
# 内部ヘルパー関数（非同期処理）
# ===================================

async def _send_websocket_notification(
    notification_data: Dict[str, Any], 
    target_users: Optional[List[str]]
) -> Dict[str, Any]:
    """WebSocket通知配信"""
    try:
        # 通知データの標準化
        standardized_notification = {
            "title": notification_data.get("title", "システム通知"),
            "message": notification_data.get("message", ""),
            "level": notification_data.get("level", "info"),
            "category": notification_data.get("category", "system"),
            "timestamp": datetime.utcnow().isoformat(),
            "data": notification_data.get("data", {})
        }
        
        # WebSocketマネージャー経由で配信
        if target_users:
            # 個別ユーザー配信
            for user_id in target_users:
                await websocket_manager.send_system_notification(
                    standardized_notification, 
                    [user_id]
                )
            recipients = len(target_users)
        else:
            # 全体配信
            await websocket_manager.send_system_notification(standardized_notification)
            ws_stats = websocket_manager.get_connection_stats()
            recipients = ws_stats.get("active_connections", 0)
        
        return {
            "status": "success",
            "recipients": recipients,
            "notification_id": f"ws_{datetime.utcnow().timestamp()}"
        }
        
    except Exception as e:
        logger.error(f"WebSocket notification failed: {e}")
        raise


async def _send_email_notifications(
    email_data: Dict[str, Any], 
    recipient_emails: List[str]
) -> int:
    """メール通知配信"""
    # メール設定（環境変数から取得）
    smtp_server = settings.get("SMTP_SERVER", "localhost")
    smtp_port = settings.get("SMTP_PORT", 587)
    smtp_username = settings.get("SMTP_USERNAME", "")
    smtp_password = settings.get("SMTP_PASSWORD", "")
    from_email = settings.get("FROM_EMAIL", "noreply@kaboom-trading.com")
    
    if not smtp_username or not smtp_password:
        logger.warning("SMTP credentials not configured, skipping email notifications")
        return 0
    
    sent_count = 0
    
    try:
        # SMTP接続
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        
        for recipient_email in recipient_emails:
            try:
                # メール作成
                msg = MIMEMultipart('alternative')
                msg['Subject'] = email_data.get("subject", "Kaboom Trading Notification")
                msg['From'] = from_email
                msg['To'] = recipient_email
                
                # テキスト部分
                text_content = email_data.get("message", "")
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
                
                # HTML部分（オプション）
                if email_data.get("html_content"):
                    html_part = MIMEText(email_data["html_content"], 'html', 'utf-8')
                    msg.attach(html_part)
                
                # 送信
                server.sendmail(from_email, recipient_email, msg.as_string())
                sent_count += 1
                
                logger.info(f"Email sent to {recipient_email}")
                
            except Exception as e:
                logger.error(f"Failed to send email to {recipient_email}: {e}")
        
        server.quit()
        
    except Exception as e:
        logger.error(f"SMTP connection failed: {e}")
        raise
    
    return sent_count


async def _process_batch_notifications(notification_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """バッチ通知処理"""
    results = []
    
    for notification in notification_batch:
        notification_type = notification.get("type", "websocket")
        data = notification.get("data", {})
        targets = notification.get("targets", [])
        
        try:
            if notification_type == "websocket":
                result = await _send_websocket_notification(data, targets)
            elif notification_type == "email":
                sent_count = await _send_email_notifications(data, targets)
                result = {
                    "status": "success",
                    "sent_count": sent_count,
                    "notification_type": "email"
                }
            else:
                result = {
                    "status": "error", 
                    "error": f"Unknown notification type: {notification_type}"
                }
                
            results.append(result)
            
        except Exception as e:
            results.append({
                "status": "error",
                "error": str(e),
                "notification_type": notification_type
            })
    
    return results


async def _save_notification_history(
    notification_data: Dict[str, Any],
    target_users: Optional[List[str]],
    task_id: str
):
    """通知履歴保存"""
    try:
        redis_client = await get_redis_client()
        
        history_entry = {
            "task_id": task_id,
            "notification": notification_data,
            "targets": target_users,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "websocket"
        }
        
        # 履歴をRedisリストに追加
        history_key = "notification_history"
        existing_history = await redis_client.get_cache(history_key) or []
        existing_history.append(history_entry)
        
        # 最新1000件のみ保持
        if len(existing_history) > 1000:
            existing_history = existing_history[-1000:]
        
        await redis_client.set_cache(history_key, existing_history, expire_seconds=86400 * 7)  # 1週間
        
    except Exception as e:
        logger.error(f"Failed to save notification history: {e}")


async def _save_email_history(
    email_data: Dict[str, Any],
    recipient_emails: List[str],
    sent_count: int,
    task_id: str
):
    """メール履歴保存"""
    try:
        redis_client = await get_redis_client()
        
        history_entry = {
            "task_id": task_id,
            "email_data": email_data,
            "recipients": recipient_emails,
            "sent_count": sent_count,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "email"
        }
        
        # メール履歴専用キー
        history_key = "email_history"
        existing_history = await redis_client.get_cache(history_key) or []
        existing_history.append(history_entry)
        
        # 最新500件のみ保持
        if len(existing_history) > 500:
            existing_history = existing_history[-500:]
        
        await redis_client.set_cache(history_key, existing_history, expire_seconds=86400 * 30)  # 30日
        
    except Exception as e:
        logger.error(f"Failed to save email history: {e}")


async def _cleanup_old_notifications() -> Dict[str, Any]:
    """古い通知履歴クリーンアップ"""
    try:
        redis_client = await get_redis_client()
        
        cutoff_date = datetime.utcnow() - timedelta(days=7)  # 7日より古いものを削除
        
        # WebSocket通知履歴クリーンアップ
        ws_history = await redis_client.get_cache("notification_history") or []
        original_count = len(ws_history)
        
        cleaned_ws_history = [
            entry for entry in ws_history 
            if datetime.fromisoformat(entry.get("timestamp", "1970-01-01")) > cutoff_date
        ]
        
        await redis_client.set_cache("notification_history", cleaned_ws_history, expire_seconds=86400 * 7)
        
        # メール履歴クリーンアップ
        email_history = await redis_client.get_cache("email_history") or []
        cleaned_email_history = [
            entry for entry in email_history
            if datetime.fromisoformat(entry.get("timestamp", "1970-01-01")) > cutoff_date
        ]
        
        await redis_client.set_cache("email_history", cleaned_email_history, expire_seconds=86400 * 30)
        
        cleaned_count = (original_count - len(cleaned_ws_history)) + (len(email_history) - len(cleaned_email_history))
        
        return {"cleaned_count": cleaned_count}
        
    except Exception as e:
        logger.error(f"Notification cleanup failed: {e}")
        return {"cleaned_count": 0}


async def _generate_daily_summary() -> Dict[str, Any]:
    """日次サマリーレポート生成"""
    try:
        redis_client = await get_redis_client()
        
        # システムメトリクス取得
        system_metrics = await redis_client.get_cache("system_metrics") or {}
        
        # WebSocket統計
        ws_stats = websocket_manager.get_connection_stats()
        
        # 通知履歴統計
        notification_history = await redis_client.get_cache("notification_history") or []
        today_notifications = [
            entry for entry in notification_history
            if entry.get("timestamp", "").startswith(datetime.utcnow().strftime("%Y-%m-%d"))
        ]
        
        # AI分析タスク統計（簡易版）
        ai_analysis_stats = {
            "completed_today": 0,  # 実際はCeleryタスク履歴から取得
            "average_response_time": "unknown"
        }
        
        summary_report = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "system": {
                "cpu_avg": system_metrics.get("system", {}).get("cpu_usage_percent", "unknown"),
                "memory_avg": system_metrics.get("system", {}).get("memory_usage_percent", "unknown"),
                "redis_status": system_metrics.get("redis", {}).get("status", "unknown")
            },
            "websocket": {
                "current_connections": ws_stats.get("active_connections", 0),
                "redis_connected": ws_stats.get("redis_connected", False)
            },
            "notifications": {
                "sent_today": len(today_notifications),
                "categories": {}  # カテゴリ別統計
            },
            "ai_analysis": ai_analysis_stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return summary_report
        
    except Exception as e:
        logger.error(f"Daily summary generation failed: {e}")
        return {"error": str(e), "generated_at": datetime.utcnow().isoformat()}


async def _get_admin_users() -> List[Dict[str, Any]]:
    """管理者ユーザー取得（モック実装）"""
    # 実際にはデータベースから取得
    return [
        {"user_id": "admin_1", "email": "admin@kaboom-trading.com"},
        {"user_id": "admin_2", "email": "tech@kaboom-trading.com"}
    ]