# app/routers/trading_integration.py

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from app.services.tachibana_client import (
    TachibanaClient, OrderExecutionService, TachibanaOrder,
    TachibanaOrderType, TachibanaOrderSide, TachibanaTimeInForce
)
from app.middleware.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trading", tags=["Trading Integration"])

# Pydantic Models
class OrderRequest(BaseModel):
    portfolio_id: str = Field(..., description="ポートフォリオID")
    symbol: str = Field(..., description="銘柄コード")
    side: str = Field(..., description="売買区分 (buy/sell)")
    order_type: str = Field(..., description="注文種別 (market/limit/stop)")
    quantity: int = Field(..., gt=0, description="注文数量")
    price: Optional[float] = Field(None, gt=0, description="指値価格")
    stop_price: Optional[float] = Field(None, gt=0, description="逆指値価格")
    time_in_force: str = Field("day", description="執行条件 (day/gtc/ioc/fok)")

class OrderCancellationRequest(BaseModel):
    order_id: str = Field(..., description="注文ID")
    reason: Optional[str] = Field(None, description="キャンセル理由")

class PositionSyncRequest(BaseModel):
    portfolio_id: str = Field(..., description="同期対象ポートフォリオID")
    force_sync: bool = Field(False, description="強制同期フラグ")

# Trading Integration Endpoints
@router.post("/orders/place", response_model=Dict[str, Any])
async def place_trading_order(
    request: OrderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """取引注文実行"""
    try:
        # プレミアムユーザーまたは実取引権限チェック
        if not current_user.is_premium and not current_user.is_verified:
            raise HTTPException(
                status_code=403, 
                detail="実取引にはプレミアムアカウントまたは認証が必要です"
            )
        
        # 注文データ検証
        if request.order_type in ["limit", "stop_limit"] and not request.price:
            raise HTTPException(status_code=400, detail="指値注文には価格の指定が必要です")
        
        if request.order_type in ["stop", "stop_limit"] and not request.stop_price:
            raise HTTPException(status_code=400, detail="逆指値注文には逆指値価格の指定が必要です")
        
        # 注文執行
        async with OrderExecutionService() as execution_service:
            result = await execution_service.execute_order(
                user_id=str(current_user.id),
                portfolio_id=request.portfolio_id,
                symbol=request.symbol,
                side=request.side,
                order_type=request.order_type,
                quantity=request.quantity,
                price=request.price,
                stop_price=request.stop_price
            )
        
        # データベース注文記録を非同期で更新
        background_tasks.add_task(
            _update_order_in_database,
            str(current_user.id),
            request.portfolio_id,
            result
        )
        
        return {
            "order_result": result,
            "message": "注文が正常に送信されました",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Order placement failed for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"注文実行でエラーが発生しました: {str(e)}")

@router.get("/orders/{order_id}/status", response_model=Dict[str, Any])
async def get_order_status(
    order_id: str,
    current_user: User = Depends(get_current_user)
):
    """注文ステータス確認"""
    try:
        async with TachibanaClient() as tachibana_client:
            order_status = await tachibana_client.get_order_status(order_id)
        
        return {
            "order_id": order_status.order_id,
            "client_order_id": order_status.client_order_id,
            "symbol": order_status.symbol,
            "side": order_status.side,
            "order_type": order_status.order_type,
            "quantity": order_status.quantity,
            "filled_quantity": order_status.filled_quantity,
            "remaining_quantity": order_status.remaining_quantity,
            "price": order_status.price,
            "average_price": order_status.average_price,
            "status": order_status.status,
            "commission": order_status.commission,
            "timestamp": order_status.timestamp.isoformat(),
            "error_message": order_status.error_message
        }
        
    except Exception as e:
        logger.error(f"Order status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="注文ステータス取得でエラーが発生しました")

@router.delete("/orders/{order_id}/cancel", response_model=Dict[str, Any])
async def cancel_trading_order(
    order_id: str,
    request: OrderCancellationRequest,
    current_user: User = Depends(get_current_user)
):
    """取引注文キャンセル"""
    try:
        async with TachibanaClient() as tachibana_client:
            success = await tachibana_client.cancel_order(order_id)
        
        if success:
            return {
                "order_id": order_id,
                "status": "cancelled",
                "reason": request.reason,
                "cancelled_by": str(current_user.id),
                "cancelled_at": datetime.utcnow().isoformat(),
                "message": "注文が正常にキャンセルされました"
            }
        else:
            raise HTTPException(status_code=400, detail="注文のキャンセルに失敗しました")
            
    except Exception as e:
        logger.error(f"Order cancellation failed: {e}")
        raise HTTPException(status_code=500, detail="注文キャンセルでエラーが発生しました")

@router.get("/account/balance", response_model=Dict[str, Any])
async def get_trading_account_balance(
    current_user: User = Depends(get_current_user)
):
    """取引口座残高取得"""
    try:
        if not current_user.is_premium and not current_user.is_verified:
            raise HTTPException(
                status_code=403,
                detail="口座情報の取得にはプレミアムアカウントまたは認証が必要です"
            )
        
        async with TachibanaClient() as tachibana_client:
            balance = await tachibana_client.get_balance()
        
        # ポジション情報を整理
        positions_data = []
        for position in balance.positions:
            positions_data.append({
                "symbol": position.symbol,
                "quantity": position.quantity,
                "average_cost": position.average_cost,
                "current_price": position.current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "market_value": position.market_value,
                "pnl_percent": (position.unrealized_pnl / (position.average_cost * position.quantity) * 100) if position.average_cost > 0 else 0
            })
        
        return {
            "account_balance": {
                "cash_balance": balance.cash_balance,
                "buying_power": balance.buying_power,
                "total_equity": balance.total_equity,
                "margin_used": balance.margin_used,
                "margin_available": balance.margin_available
            },
            "positions": positions_data,
            "summary": {
                "total_positions": len(positions_data),
                "total_unrealized_pnl": sum(p.unrealized_pnl for p in balance.positions),
                "total_market_value": sum(p.market_value for p in balance.positions)
            },
            "last_updated": balance.last_updated.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Balance retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="残高取得でエラーが発生しました")

@router.get("/orders/history", response_model=Dict[str, Any])
async def get_trading_order_history(
    start_date: Optional[datetime] = Query(None, description="開始日時"),
    end_date: Optional[datetime] = Query(None, description="終了日時"),
    limit: int = Query(50, ge=1, le=200, description="最大取得件数"),
    status: Optional[str] = Query(None, description="ステータスフィルター"),
    symbol: Optional[str] = Query(None, description="銘柄フィルター"),
    current_user: User = Depends(get_current_user)
):
    """取引注文履歴取得"""
    try:
        # デフォルト期間設定（過去30日）
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        async with TachibanaClient() as tachibana_client:
            orders = await tachibana_client.get_order_history(start_date, end_date, limit)
        
        # フィルタリング
        filtered_orders = orders
        if status:
            filtered_orders = [o for o in filtered_orders if o.status == status]
        if symbol:
            filtered_orders = [o for o in filtered_orders if o.symbol == symbol]
        
        # レスポンス構築
        orders_data = []
        for order in filtered_orders:
            orders_data.append({
                "order_id": order.order_id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "quantity": order.quantity,
                "filled_quantity": order.filled_quantity,
                "remaining_quantity": order.remaining_quantity,
                "price": order.price,
                "average_price": order.average_price,
                "status": order.status,
                "commission": order.commission,
                "timestamp": order.timestamp.isoformat()
            })
        
        return {
            "orders": orders_data,
            "summary": {
                "total_orders": len(orders_data),
                "filled_orders": len([o for o in orders_data if o["status"] == "filled"]),
                "cancelled_orders": len([o for o in orders_data if o["status"] == "cancelled"]),
                "total_commission": sum(o["commission"] for o in orders_data),
                "total_volume": sum(o["quantity"] * (o["average_price"] or o["price"] or 0) for o in orders_data if o["average_price"] or o["price"])
            },
            "filter": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "status": status,
                "symbol": symbol,
                "limit": limit
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Order history retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="注文履歴取得でエラーが発生しました")

@router.post("/positions/sync", response_model=Dict[str, Any])
async def sync_portfolio_positions(
    request: PositionSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """ポートフォリオ・ポジション同期"""
    try:
        if not current_user.is_premium and not current_user.is_verified:
            raise HTTPException(
                status_code=403,
                detail="ポジション同期にはプレミアムアカウントまたは認証が必要です"
            )
        
        # バックグラウンドで同期処理
        background_tasks.add_task(
            _sync_portfolio_positions,
            str(current_user.id),
            request.portfolio_id,
            request.force_sync
        )
        
        return {
            "portfolio_id": request.portfolio_id,
            "sync_status": "started",
            "force_sync": request.force_sync,
            "message": "ポートフォリオ同期を開始しました",
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=2)).isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Position sync failed: {e}")
        raise HTTPException(status_code=500, detail="ポジション同期でエラーが発生しました")

@router.get("/market/quote/{symbol}", response_model=Dict[str, Any])
async def get_market_quote(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """リアルタイム市場価格取得"""
    try:
        async with TachibanaClient() as tachibana_client:
            quote = await tachibana_client.get_market_quote(symbol)
        
        return {
            "symbol": quote["symbol"],
            "bid": quote["bid"],
            "ask": quote["ask"],
            "last": quote["last"],
            "volume": quote["volume"],
            "spread": quote["ask"] - quote["bid"],
            "spread_percent": ((quote["ask"] - quote["bid"]) / quote["last"] * 100) if quote["last"] > 0 else 0,
            "timestamp": quote["timestamp"]
        }
        
    except Exception as e:
        logger.error(f"Market quote retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="市場価格取得でエラーが発生しました")

@router.get("/connection/status", response_model=Dict[str, Any])
async def get_trading_connection_status(
    current_user: User = Depends(get_current_user)
):
    """取引接続ステータス確認"""
    try:
        # 立花証券APIの接続テスト
        async with TachibanaClient() as tachibana_client:
            # 簡単な API 呼び出しで接続確認
            test_quote = await tachibana_client.get_market_quote("7203")  # トヨタで接続テスト
            
        return {
            "status": "connected",
            "broker": "Tachibana Securities",
            "api_version": "v1",
            "last_ping": datetime.utcnow().isoformat(),
            "connection_quality": "excellent",
            "features": {
                "real_time_quotes": True,
                "order_execution": True,
                "position_sync": True,
                "account_balance": True,
                "order_history": True
            },
            "limits": {
                "max_orders_per_day": 1000,
                "max_order_size": 10000,
                "api_rate_limit": "100 requests/minute"
            }
        }
        
    except Exception as e:
        logger.error(f"Connection status check failed: {e}")
        return {
            "status": "disconnected",
            "broker": "Tachibana Securities",
            "error": str(e),
            "last_attempt": datetime.utcnow().isoformat(),
            "retry_in_seconds": 60
        }

# Helper Functions
async def _update_order_in_database(user_id: str, portfolio_id: str, order_result: Dict[str, Any]):
    """データベース注文記録更新"""
    try:
        # 実際の実装では Order モデルを更新
        logger.info(f"Updating order in database: {order_result['external_order_id']}")
        
        # データベース更新処理
        # order = Order(
        #     user_id=user_id,
        #     portfolio_id=portfolio_id,
        #     external_order_id=order_result['external_order_id'],
        #     ...
        # )
        
    except Exception as e:
        logger.error(f"Database order update failed: {e}")

async def _sync_portfolio_positions(user_id: str, portfolio_id: str, force_sync: bool):
    """ポートフォリオポジション同期処理"""
    try:
        async with OrderExecutionService() as execution_service:
            await execution_service.sync_positions_with_portfolio(user_id, portfolio_id)
        
        logger.info(f"Portfolio {portfolio_id} positions synced for user {user_id}")
        
    except Exception as e:
        logger.error(f"Portfolio sync failed: {e}")

# WebSocket Integration (for real-time updates)
@router.websocket("/ws/orders/{user_id}")
async def order_updates_websocket(websocket, user_id: str):
    """注文更新リアルタイム配信WebSocket"""
    # WebSocket実装は別途 websocket/manager.py で統合
    pass