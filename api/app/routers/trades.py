"""
取引API - 売買注文・履歴管理・リアルタイム取引実行

機能:
- 売買注文の作成・キャンセル・実行
- 取引履歴管理・分析
- リアルタイム約定通知
- 外部証券API統合（立花証券等）
"""
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from app.middleware.auth import get_current_user, get_premium_user, User
from app.services.redis_client import get_redis_client, RedisClient
from app.websocket.manager import websocket_manager
from app.tasks.notification_tasks import send_realtime_notification_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trades", tags=["Trading"])


# ===================================
# Enum・Pydanticモデル定義
# ===================================

class OrderType(str, Enum):
    MARKET = "market"      # 成行
    LIMIT = "limit"        # 指値
    STOP = "stop"          # 逆指値
    STOP_LIMIT = "stop_limit"  # 逆指値付指値

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"         # 注文中
    PARTIALLY_FILLED = "partially_filled"  # 一部約定
    FILLED = "filled"          # 全約定
    CANCELLED = "cancelled"    # キャンセル
    REJECTED = "rejected"      # 拒否

class TimeInForce(str, Enum):
    DAY = "day"              # 当日有効
    GTC = "gtc"              # Good Till Cancelled
    IOC = "ioc"              # Immediate or Cancel
    FOK = "fok"              # Fill or Kill


class OrderCreate(BaseModel):
    symbol: str = Field(..., description="銘柄コード")
    side: OrderSide = Field(..., description="売買区分")
    order_type: OrderType = Field(..., description="注文種別")
    quantity: int = Field(..., gt=0, description="注文数量")
    price: Optional[float] = Field(None, gt=0, description="指値価格（指値・逆指値時必須）")
    stop_price: Optional[float] = Field(None, gt=0, description="逆指値価格")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="有効期限")
    portfolio_id: Optional[str] = Field(None, description="対象ポートフォリオID")
    
    @validator('price')
    def validate_price(cls, v, values):
        order_type = values.get('order_type')
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('指値・逆指値付指値では価格が必須です')
        return v
    
    @validator('stop_price')
    def validate_stop_price(cls, v, values):
        order_type = values.get('order_type')
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('逆指値では逆指値価格が必須です')
        return v


class OrderUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)


# ===================================
# 注文管理API
# ===================================

@router.post("/orders")
async def create_order(
    order_data: OrderCreate,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """新規注文作成"""
    try:
        # 銘柄情報検証
        await _validate_trading_symbol(order_data.symbol, redis_client)
        
        # 買付余力・保有株数チェック
        if order_data.side == OrderSide.BUY:
            await _check_buying_power(user.id, order_data, redis_client)
        else:
            await _check_holding_quantity(user.id, order_data)
        
        # 注文作成
        new_order = await _create_order(user.id, order_data)
        
        # 外部証券API経由で注文送信（非同期処理）
        execution_result = await _submit_order_to_broker(new_order)
        
        # 注文状況をRedisに保存
        await redis_client.set_cache(
            f"order:{new_order['id']}", 
            new_order, 
            expire_seconds=86400  # 24時間
        )
        
        # リアルタイム通知
        await websocket_manager.send_system_notification({
            "title": "注文送信完了",
            "message": f"{order_data.symbol} {order_data.side} {order_data.quantity}株の注文を送信しました",
            "level": "success",
            "category": "trading"
        }, [user.id])
        
        return {
            "message": "注文を送信しました",
            "order": new_order,
            "broker_response": execution_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文作成に失敗しました"
        )


@router.get("/orders")
async def get_orders(
    status_filter: Optional[OrderStatus] = Query(None, description="ステータスフィルター"),
    symbol_filter: Optional[str] = Query(None, description="銘柄フィルター"),
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=100, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット"),
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """注文履歴取得"""
    try:
        # フィルター条件構築
        filters = {
            "user_id": user.id,
            "status": status_filter,
            "symbol": symbol_filter,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset
        }
        
        # キャッシュキー生成
        cache_key = f"orders:{user.id}:{hash(str(filters))}"
        cached_orders = await redis_client.get_cache(cache_key)
        
        if cached_orders:
            return cached_orders
        
        # データベースから取得
        orders = await _get_user_orders(filters)
        
        # 各注文のリアルタイム状況を更新
        for order in orders["items"]:
            current_status = await _get_order_current_status(order["id"])
            if current_status and current_status != order["status"]:
                order["status"] = current_status
                order["updated_at"] = datetime.utcnow().isoformat()
        
        # キャッシュ保存（2分）
        await redis_client.set_cache(cache_key, orders, expire_seconds=120)
        
        return orders
        
    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文履歴取得に失敗しました"
        )


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """個別注文詳細取得"""
    try:
        # Redis から最新状況取得
        cached_order = await redis_client.get_cache(f"order:{order_id}")
        
        # データベースから取得
        order = await _get_order_by_id(order_id, user.id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="注文が見つかりません"
            )
        
        # 約定履歴取得
        executions = await _get_order_executions(order_id)
        
        # リアルタイム価格情報
        current_price = await redis_client.get_stock_price(order["symbol"])
        
        return {
            "order": order,
            "executions": executions,
            "current_market_price": current_price.get("price") if current_price else None,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文詳細取得に失敗しました"
        )


@router.put("/orders/{order_id}")
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """注文変更"""
    try:
        # 注文存在・権限チェック
        order = await _get_order_by_id(order_id, user.id)
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")
        
        # 変更可能状態チェック
        if order["status"] not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この注文は変更できません"
            )
        
        # 証券会社API経由で注文変更
        updated_order = await _update_order_at_broker(order_id, order_update)
        
        # キャッシュ更新
        await redis_client.set_cache(f"order:{order_id}", updated_order, expire_seconds=86400)
        
        # 通知
        await websocket_manager.send_system_notification({
            "title": "注文変更完了",
            "message": f"注文ID: {order_id}の変更が完了しました",
            "level": "info",
            "category": "trading"
        }, [user.id])
        
        return {
            "message": "注文を変更しました",
            "order": updated_order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="注文変更に失敗しました")


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """注文キャンセル"""
    try:
        # 注文チェック
        order = await _get_order_by_id(order_id, user.id)
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")
        
        # キャンセル可能チェック
        if order["status"] not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="この注文はキャンセルできません"
            )
        
        # 証券会社APIでキャンセル実行
        cancellation_result = await _cancel_order_at_broker(order_id)
        
        # 状況更新
        order["status"] = OrderStatus.CANCELLED
        order["cancelled_at"] = datetime.utcnow().isoformat()
        
        await redis_client.set_cache(f"order:{order_id}", order, expire_seconds=86400)
        
        # 通知
        await websocket_manager.send_system_notification({
            "title": "注文キャンセル完了",
            "message": f"{order['symbol']} {order['side']}注文をキャンセルしました",
            "level": "info",
            "category": "trading"
        }, [user.id])
        
        return {
            "message": "注文をキャンセルしました",
            "order": order,
            "cancellation_result": cancellation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="注文キャンセルに失敗しました")


# ===================================
# 取引履歴・統計API
# ===================================

@router.get("/history")
async def get_trade_history(
    symbol: Optional[str] = Query(None, description="銘柄フィルター"),
    start_date: Optional[str] = Query(None, description="開始日"),
    end_date: Optional[str] = Query(None, description="終了日"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """取引履歴取得"""
    try:
        filters = {
            "user_id": user.id,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "offset": offset
        }
        
        # キャッシュチェック
        cache_key = f"trade_history:{user.id}:{hash(str(filters))}"
        cached_history = await redis_client.get_cache(cache_key)
        
        if cached_history:
            return cached_history
        
        # 実約定データ取得
        trade_history = await _get_user_trade_history(filters)
        
        # 統計情報計算
        stats = await _calculate_trading_stats(trade_history["items"])
        
        result = {
            **trade_history,
            "statistics": stats
        }
        
        # キャッシュ保存（5分）
        await redis_client.set_cache(cache_key, result, expire_seconds=300)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get trade history: {e}")
        raise HTTPException(status_code=500, detail="取引履歴取得に失敗しました")


@router.get("/statistics")
async def get_trading_statistics(
    period: str = Query("1m", regex="^(1w|1m|3m|6m|1y|all)$"),
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """取引統計分析"""
    try:
        cache_key = f"trading_stats:{user.id}:{period}"
        cached_stats = await redis_client.get_cache(cache_key)
        
        if cached_stats:
            return cached_stats
        
        # 期間データ取得
        trades = await _get_trades_by_period(user.id, period)
        
        # 詳細統計計算
        detailed_stats = await _calculate_detailed_trading_stats(trades)
        
        # パフォーマンス分析
        performance_metrics = await _calculate_trading_performance(trades)
        
        result = {
            "period": period,
            "summary": detailed_stats,
            "performance": performance_metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # キャッシュ保存（30分）
        await redis_client.set_cache(cache_key, result, expire_seconds=1800)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get trading statistics: {e}")
        raise HTTPException(status_code=500, detail="取引統計取得に失敗しました")


# ===================================
# リアルタイム市場データ・価格アラート
# ===================================

@router.get("/market-data/{symbol}")
async def get_market_data(
    symbol: str,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """リアルタイム市場データ取得"""
    try:
        # Redis から最新価格取得
        price_data = await redis_client.get_stock_price(symbol)
        
        if not price_data:
            # 価格データが無い場合は更新要求
            from app.tasks.market_data_tasks import update_single_stock_task
            task_result = update_single_stock_task.delay(symbol, user.id)
            
            return {
                "symbol": symbol,
                "status": "updating",
                "task_id": task_result.id,
                "message": "価格データを更新中です"
            }
        
        # 板情報取得（モック）
        orderbook = await _get_orderbook(symbol)
        
        # 取引履歴（直近）
        recent_trades = await _get_recent_trades(symbol)
        
        return {
            "symbol": symbol,
            "price_data": price_data,
            "orderbook": orderbook,
            "recent_trades": recent_trades,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="市場データ取得に失敗しました")


@router.post("/price-alerts")
async def create_price_alert(
    alert_config: Dict[str, Any],
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """価格アラート設定"""
    try:
        symbol = alert_config.get("symbol")
        condition = alert_config.get("condition")  # "above" or "below"
        target_price = float(alert_config.get("target_price"))
        
        # アラート情報構築
        alert = {
            "id": f"alert_{datetime.utcnow().timestamp()}",
            "user_id": user.id,
            "symbol": symbol,
            "condition": condition,
            "target_price": target_price,
            "created_at": datetime.utcnow().isoformat(),
            "active": True
        }
        
        # Redis に保存
        user_alerts_key = "price_alerts"
        existing_alerts = await redis_client.get_cache(user_alerts_key) or {}
        
        if user.id not in existing_alerts:
            existing_alerts[user.id] = []
        
        existing_alerts[user.id].append(alert)
        
        await redis_client.set_cache(user_alerts_key, existing_alerts, expire_seconds=86400 * 30)
        
        return {
            "message": "価格アラートを設定しました",
            "alert": alert
        }
        
    except Exception as e:
        logger.error(f"Failed to create price alert: {e}")
        raise HTTPException(status_code=500, detail="価格アラート設定に失敗しました")


# ===================================
# ヘルパー関数（外部API・ビジネスロジック）
# ===================================

async def _validate_trading_symbol(symbol: str, redis_client: RedisClient):
    """取引可能銘柄検証"""
    if not symbol or len(symbol) < 4:
        raise HTTPException(status_code=400, detail="無効な銘柄コードです")
    
    # 実際には取引所API等で検証


async def _check_buying_power(user_id: str, order: OrderCreate, redis_client: RedisClient):
    """買付余力チェック"""
    # モック実装：十分な余力があると仮定
    required_amount = order.quantity * (order.price or 1000)  # 概算
    
    # 実際にはユーザーの証券口座残高をチェック
    if required_amount > 10000000:  # 1000万円制限（例）
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="買付余力が不足しています"
        )


async def _check_holding_quantity(user_id: str, order: OrderCreate):
    """保有株数チェック（売り注文時）"""
    # 実際にはポートフォリオから保有数確認
    pass


async def _create_order(user_id: str, order_data: OrderCreate) -> Dict[str, Any]:
    """注文オブジェクト作成"""
    return {
        "id": f"order_{datetime.utcnow().timestamp()}",
        "user_id": user_id,
        "symbol": order_data.symbol,
        "side": order_data.side,
        "order_type": order_data.order_type,
        "quantity": order_data.quantity,
        "price": order_data.price,
        "stop_price": order_data.stop_price,
        "time_in_force": order_data.time_in_force,
        "status": OrderStatus.PENDING,
        "created_at": datetime.utcnow().isoformat(),
        "portfolio_id": order_data.portfolio_id
    }


async def _submit_order_to_broker(order: Dict[str, Any]) -> Dict[str, Any]:
    """外部証券API経由注文送信（立花証券等）"""
    # モック実装
    return {
        "broker_order_id": f"broker_{order['id']}",
        "status": "accepted",
        "message": "注文を受け付けました"
    }


async def _get_user_orders(filters: Dict[str, Any]) -> Dict[str, Any]:
    """ユーザー注文履歴取得"""
    # モック実装
    return {
        "items": [
            {
                "id": "order_123",
                "symbol": "7203.T",
                "side": "buy",
                "quantity": 100,
                "price": 2500.0,
                "status": "filled",
                "created_at": "2024-01-01T09:00:00Z"
            }
        ],
        "total": 1,
        "limit": filters["limit"],
        "offset": filters["offset"]
    }


# その他ヘルパー関数（簡略化）
async def _get_order_current_status(order_id: str) -> Optional[str]: return None
async def _get_order_by_id(order_id: str, user_id: str) -> Optional[Dict]: return None
async def _get_order_executions(order_id: str) -> List[Dict]: return []
async def _update_order_at_broker(order_id: str, update_data: OrderUpdate) -> Dict: return {}
async def _cancel_order_at_broker(order_id: str) -> Dict: return {}
async def _get_user_trade_history(filters: Dict) -> Dict: return {"items": [], "total": 0}
async def _calculate_trading_stats(trades: List[Dict]) -> Dict: return {}
async def _get_trades_by_period(user_id: str, period: str) -> List[Dict]: return []
async def _calculate_detailed_trading_stats(trades: List) -> Dict: return {}
async def _calculate_trading_performance(trades: List) -> Dict: return {}
async def _get_orderbook(symbol: str) -> Dict: return {}
async def _get_recent_trades(symbol: str) -> List[Dict]: return []