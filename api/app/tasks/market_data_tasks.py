"""
市場データ・システム監視タスク

機能:
- 定期的な株価データ取得・更新
- システムメトリクス収集
- 価格アラート監視
- WebSocket経由リアルタイム配信
"""
import asyncio
import json
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
import yfinance as yf

from app.tasks.celery_app import celery_app
from app.services.redis_client import get_redis_client
from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


@celery_app.task(name="market_data.update_all_stock_prices", queue="market_data")
def update_all_stock_prices() -> Dict[str, Any]:
    """全監視銘柄の価格データ更新タスク"""
    try:
        updated_symbols = asyncio.run(_update_stock_prices_async())
        
        return {
            "status": "success",
            "updated_symbols": len(updated_symbols),
            "symbols": updated_symbols,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stock price update task failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@celery_app.task(name="market_data.collect_system_metrics", queue="market_data")
def collect_system_metrics() -> Dict[str, Any]:
    """システムメトリクス収集タスク"""
    try:
        metrics = asyncio.run(_collect_system_metrics_async())
        
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(
    bind=True,
    name="market_data.update_single_stock",
    queue="market_data",
    soft_time_limit=30,
    time_limit=60
)
def update_single_stock_task(self, symbol: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """個別銘柄データ更新タスク"""
    try:
        price_data = asyncio.run(_fetch_single_stock_data_async(symbol))
        
        # Redis保存
        asyncio.run(_save_stock_price_data(symbol, price_data))
        
        # WebSocket配信
        asyncio.run(websocket_manager.send_price_update(symbol, price_data))
        
        # 特定ユーザーへの通知
        if user_id:
            asyncio.run(websocket_manager.send_system_notification({
                "title": f"{symbol} 価格更新",
                "message": f"最新価格: ¥{price_data.get('price', 'N/A')}",
                "level": "info"
            }, [user_id]))
        
        return {
            "status": "success",
            "symbol": symbol,
            "price_data": price_data,
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"Single stock update failed for {symbol}: {e}")
        raise


@celery_app.task(name="market_data.price_alert_monitor", queue="market_data")
def price_alert_monitor_task() -> Dict[str, Any]:
    """価格アラート監視タスク"""
    try:
        alerts_triggered = asyncio.run(_check_price_alerts_async())
        
        return {
            "status": "success",
            "alerts_triggered": len(alerts_triggered),
            "details": alerts_triggered
        }
        
    except Exception as e:
        logger.error(f"Price alert monitoring failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="market_data.market_hours_check", queue="market_data")
def market_hours_check_task() -> Dict[str, Any]:
    """市場営業時間チェックタスク"""
    try:
        market_status = _get_market_status()
        
        # 市場状態をRedisに保存
        asyncio.run(_save_market_status(market_status))
        
        # 状態変化時にWebSocket通知
        if market_status.get("status_changed"):
            asyncio.run(websocket_manager.send_system_notification({
                "title": "市場状況更新",
                "message": f"東京証券取引所: {market_status['status']}",
                "level": "info"
            }))
        
        return {
            "status": "success",
            "market_status": market_status
        }
        
    except Exception as e:
        logger.error(f"Market hours check failed: {e}")
        return {"status": "error", "error": str(e)}


# ===================================
# 内部ヘルパー関数（非同期処理）
# ===================================

async def _update_stock_prices_async() -> List[str]:
    """監視銘柄価格データ一括更新"""
    # デフォルト監視銘柄（設定から取得する想定）
    default_symbols = [
        "7203.T",   # トヨタ自動車
        "9984.T",   # ソフトバンクグループ
        "6098.T",   # リクルートホールディングス
        "4689.T",   # Zホールディングス
        "9983.T"    # ファーストリテイリング
    ]
    
    # Redis から追加監視銘柄を取得
    redis_client = await get_redis_client()
    
    try:
        cached_symbols = await redis_client.get_cache("monitored_symbols")
        if cached_symbols:
            additional_symbols = cached_symbols.get("symbols", [])
            all_symbols = list(set(default_symbols + additional_symbols))
        else:
            all_symbols = default_symbols
    except Exception:
        all_symbols = default_symbols
    
    updated_symbols = []
    
    for symbol in all_symbols:
        try:
            price_data = await _fetch_single_stock_data_async(symbol)
            await _save_stock_price_data(symbol, price_data)
            
            # WebSocket配信
            await websocket_manager.send_price_update(symbol, price_data)
            
            updated_symbols.append(symbol)
            
        except Exception as e:
            logger.warning(f"Failed to update {symbol}: {e}")
    
    return updated_symbols


async def _fetch_single_stock_data_async(symbol: str) -> Dict[str, Any]:
    """単一銘柄データ取得"""
    try:
        # 実際のyfinanceによるデータ取得（非同期ラッパー）
        loop = asyncio.get_event_loop()
        stock_data = await loop.run_in_executor(None, _fetch_stock_data_sync, symbol)
        
        return stock_data
        
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        # モックデータ返却（開発時）
        return _generate_mock_price_data(symbol)


def _fetch_stock_data_sync(symbol: str) -> Dict[str, Any]:
    """yfinanceによる実際の株価取得（同期処理）"""
    try:
        ticker = yf.Ticker(symbol)
        
        # 最新価格取得
        info = ticker.info
        hist = ticker.history(period="2d")
        
        if hist.empty:
            raise ValueError(f"No data found for symbol {symbol}")
        
        latest = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else latest
        
        current_price = float(latest['Close'])
        previous_close = float(previous['Close'])
        
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close != 0 else 0
        
        return {
            "symbol": symbol,
            "price": current_price,
            "change": change,
            "change_percent": change_percent,
            "volume": int(latest['Volume']),
            "high": float(latest['High']),
            "low": float(latest['Low']),
            "open": float(latest['Open']),
            "previous_close": previous_close,
            "timestamp": datetime.utcnow().isoformat(),
            "market": info.get("market", "unknown"),
            "currency": info.get("currency", "JPY")
        }
        
    except Exception as e:
        logger.error(f"yfinance fetch failed for {symbol}: {e}")
        raise


def _generate_mock_price_data(symbol: str) -> Dict[str, Any]:
    """モック価格データ生成（開発・テスト用）"""
    base_price = 1000 + hash(symbol) % 5000  # シンボルベースの基準価格
    
    # ランダムな価格変動
    current_price = base_price * (1 + np.random.normal(0, 0.02))
    change = np.random.normal(0, 20)
    change_percent = change / base_price * 100
    
    return {
        "symbol": symbol,
        "price": round(current_price, 2),
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),
        "volume": np.random.randint(100000, 2000000),
        "high": round(current_price * 1.02, 2),
        "low": round(current_price * 0.98, 2),
        "open": round(current_price * 0.999, 2),
        "previous_close": round(current_price - change, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "market": "TSE",
        "currency": "JPY",
        "is_mock": True
    }


async def _save_stock_price_data(symbol: str, price_data: Dict[str, Any]):
    """価格データをRedisに保存"""
    try:
        redis_client = await get_redis_client()
        await redis_client.set_stock_price(symbol, price_data, expire_seconds=300)  # 5分キャッシュ
        
        # 履歴データも保存（簡易版）
        history_key = f"price_history:{symbol}"
        existing_history = await redis_client.get_cache(history_key) or []
        
        # 最新10件のみ保持
        existing_history.append({
            "price": price_data["price"],
            "timestamp": price_data["timestamp"]
        })
        
        if len(existing_history) > 10:
            existing_history = existing_history[-10:]
        
        await redis_client.set_cache(history_key, existing_history, expire_seconds=3600)
        
    except Exception as e:
        logger.error(f"Failed to save stock price data for {symbol}: {e}")


async def _collect_system_metrics_async() -> Dict[str, Any]:
    """システムメトリクス収集"""
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # メモリ使用量
        memory = psutil.virtual_memory()
        
        # ディスク使用量
        disk = psutil.disk_usage('/')
        
        # Redis接続状況
        redis_client = await get_redis_client()
        redis_health = await redis_client.health_check()
        
        # WebSocket接続数
        ws_stats = websocket_manager.get_connection_stats()
        
        metrics = {
            "system": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available // (1024**3),
                "disk_usage_percent": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free // (1024**3)
            },
            "redis": {
                "status": redis_health["status"],
                "memory_usage": redis_health.get("memory_usage", "unknown")
            },
            "websocket": {
                "active_connections": ws_stats["active_connections"],
                "redis_connected": ws_stats["redis_connected"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # メトリクスをRedisに保存
        await redis_client.set_cache("system_metrics", metrics, expire_seconds=1800)  # 30分
        
        # アラート条件チェック
        alerts = _check_system_alerts(metrics)
        if alerts:
            await websocket_manager.send_system_notification({
                "title": "システムアラート",
                "message": f"{len(alerts)}件のアラートが発生",
                "level": "warning"
            })
        
        return metrics
        
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        raise


def _check_system_alerts(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """システムアラート条件チェック"""
    alerts = []
    
    system_metrics = metrics.get("system", {})
    
    # CPU使用率アラート（90%以上）
    if system_metrics.get("cpu_usage_percent", 0) > 90:
        alerts.append({
            "type": "cpu_high",
            "message": f"CPU使用率が高い: {system_metrics['cpu_usage_percent']:.1f}%",
            "severity": "warning"
        })
    
    # メモリ使用率アラート（85%以上）
    if system_metrics.get("memory_usage_percent", 0) > 85:
        alerts.append({
            "type": "memory_high",
            "message": f"メモリ使用率が高い: {system_metrics['memory_usage_percent']:.1f}%",
            "severity": "warning"
        })
    
    # ディスク使用率アラート（90%以上）
    if system_metrics.get("disk_usage_percent", 0) > 90:
        alerts.append({
            "type": "disk_high",
            "message": f"ディスク使用率が高い: {system_metrics['disk_usage_percent']:.1f}%",
            "severity": "critical"
        })
    
    # Redis接続アラート
    if metrics.get("redis", {}).get("status") != "connected":
        alerts.append({
            "type": "redis_disconnected",
            "message": "Redis接続が切断されています",
            "severity": "critical"
        })
    
    return alerts


async def _check_price_alerts_async() -> List[Dict[str, Any]]:
    """価格アラート条件チェック"""
    try:
        redis_client = await get_redis_client()
        
        # ユーザー設定アラート取得
        user_alerts = await redis_client.get_cache("price_alerts") or {}
        
        triggered_alerts = []
        
        for user_id, alerts in user_alerts.items():
            for alert in alerts:
                symbol = alert.get("symbol")
                condition = alert.get("condition")  # "above", "below"
                target_price = alert.get("target_price")
                
                # 現在価格取得
                current_price_data = await redis_client.get_stock_price(symbol)
                if not current_price_data:
                    continue
                
                current_price = current_price_data.get("price")
                
                # アラート条件チェック
                alert_triggered = False
                if condition == "above" and current_price >= target_price:
                    alert_triggered = True
                elif condition == "below" and current_price <= target_price:
                    alert_triggered = True
                
                if alert_triggered:
                    alert_data = {
                        "user_id": user_id,
                        "symbol": symbol,
                        "condition": condition,
                        "target_price": target_price,
                        "current_price": current_price,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # ユーザーに通知
                    await websocket_manager.send_system_notification({
                        "title": f"価格アラート: {symbol}",
                        "message": f"目標価格({condition} ¥{target_price})に到達しました。現在価格: ¥{current_price}",
                        "level": "info"
                    }, [user_id])
                    
                    triggered_alerts.append(alert_data)
        
        return triggered_alerts
        
    except Exception as e:
        logger.error(f"Price alert check failed: {e}")
        return []


def _get_market_status() -> Dict[str, Any]:
    """東京証券取引所営業時間判定"""
    now = datetime.now()
    
    # 平日判定
    is_weekday = now.weekday() < 5
    
    # 営業時間判定（9:00-11:30, 12:30-15:00）
    morning_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    morning_close = now.replace(hour=11, minute=30, second=0, microsecond=0)
    afternoon_open = now.replace(hour=12, minute=30, second=0, microsecond=0)
    afternoon_close = now.replace(hour=15, minute=0, second=0, microsecond=0)
    
    if not is_weekday:
        status = "closed"
        reason = "休日"
    elif morning_open <= now <= morning_close:
        status = "open"
        reason = "前場"
    elif morning_close < now < afternoon_open:
        status = "break"
        reason = "昼休み"
    elif afternoon_open <= now <= afternoon_close:
        status = "open"
        reason = "後場"
    else:
        status = "closed"
        reason = "時間外"
    
    return {
        "status": status,
        "reason": reason,
        "timestamp": now.isoformat(),
        "next_open": _calculate_next_open_time(now, status).isoformat() if status == "closed" else None
    }


def _calculate_next_open_time(current_time: datetime, current_status: str) -> datetime:
    """次回市場開始時刻計算"""
    if current_status == "break":
        # 昼休み中 -> 後場開始
        return current_time.replace(hour=12, minute=30, second=0, microsecond=0)
    
    # 時間外・休日 -> 翌営業日の前場開始
    next_day = current_time + timedelta(days=1)
    while next_day.weekday() >= 5:  # 土日をスキップ
        next_day += timedelta(days=1)
    
    return next_day.replace(hour=9, minute=0, second=0, microsecond=0)


async def _save_market_status(market_status: Dict[str, Any]):
    """市場状況をRedisに保存"""
    try:
        redis_client = await get_redis_client()
        
        # 前回の状況と比較
        previous_status = await redis_client.get_cache("market_status")
        status_changed = (
            not previous_status or 
            previous_status.get("status") != market_status["status"]
        )
        
        market_status["status_changed"] = status_changed
        
        await redis_client.set_cache("market_status", market_status, expire_seconds=3600)
        
    except Exception as e:
        logger.error(f"Failed to save market status: {e}")