"""
取引管理API - データベース統合版
売買注文・取引履歴・市場データ統合

機能:
- 売買注文CRUD（実データベース）
- 取引履歴管理
- 取引統計分析
- リアルタイム市場データ
- 価格アラート機能
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.middleware.auth import get_current_user, get_premium_user, User as AuthUser
from app.services.trading_service import TradingService
from app.services.redis_client import get_redis_client, RedisClient
from app.websocket.manager import websocket_manager
from app.tasks.market_data_tasks import update_stock_price_task
from app.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trades", tags=["Trading"])


# ===================================
# Pydanticモデル定義
# ===================================

class OrderCreate(BaseModel):
    portfolio_id: str = Field(..., description="ポートフォリオID")
    symbol: str = Field(..., description="銘柄コード")
    side: str = Field(..., description="売買区分: buy|sell")
    order_type: str = Field(..., description="注文種別: market|limit|stop|stop_limit")
    quantity: int = Field(..., gt=0, description="数量")
    limit_price: Optional[float] = Field(None, description="指値価格")
    stop_price: Optional[float] = Field(None, description="逆指値価格")
    time_in_force: str = Field("DAY", description="有効期限: DAY|GTC|IOC|FOK")
    notes: Optional[str] = Field(None, description="注文メモ")
    estimated_price: Optional[float] = Field(None, description="予想価格（成行用）")


class OrderUpdate(BaseModel):
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    notes: Optional[str] = None


class TradeExecution(BaseModel):
    quantity: int = Field(..., gt=0, description="約定数量")
    price: float = Field(..., gt=0, description="約定価格")
    commission: float = Field(0, description="手数料")
    fees: float = Field(0, description="その他費用")
    market_price: Optional[float] = Field(None, description="市場価格")
    bid_price: Optional[float] = Field(None, description="買気配")
    ask_price: Optional[float] = Field(None, description="売気配")
    notes: Optional[str] = Field(None, description="約定メモ")


class PriceAlert(BaseModel):
    symbol: str = Field(..., description="銘柄コード")
    condition: str = Field(..., description="条件: above|below|change")
    target_price: float = Field(..., gt=0, description="目標価格")
    percentage_change: Optional[float] = Field(None, description="変動率（%）")
    is_active: bool = Field(True, description="アラート有効")


# ===================================
# APIエンドポイント
# ===================================

@router.get("/orders")
async def get_user_orders(
    portfolio_id: Optional[str] = Query(None, description="ポートフォリオIDでフィルタ"),
    status: Optional[str] = Query(None, description="ステータスでフィルタ"),
    limit: int = Query(50, description="取得件数"),
    offset: int = Query(0, description="オフセット"),
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ユーザーの注文一覧取得"""
    try:
        trading_service = TradingService(db)
        
        portfolio_uuid = UUID(portfolio_id) if portfolio_id else None
        orders = await trading_service.get_user_orders(
            user.id, portfolio_uuid, limit, offset
        )
        
        # Filter by status if provided
        if status:
            orders = [order for order in orders if order.status == status]
        
        orders_data = []
        for order in orders:
            order_dict = order.to_dict()
            # Add trade count for this order
            trades = await trading_service.get_user_trades(user.id)
            order_dict["trade_count"] = len([t for t in trades if str(t.order_id) == str(order.id)])
            orders_data.append(order_dict)
        
        return {
            "orders": orders_data,
            "total_count": len(orders_data),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get user orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文一覧取得に失敗しました"
        )


@router.post("/orders")
async def create_order(
    order_data: OrderCreate,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """新規注文作成"""
    try:
        trading_service = TradingService(db)
        
        # Validate order type and required fields
        if order_data.order_type in ["limit", "stop_limit"] and not order_data.limit_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="指値注文には指値価格が必要です"
            )
        
        if order_data.order_type in ["stop", "stop_limit"] and not order_data.stop_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="逆指値注文には逆指値価格が必要です"
            )
        
        # Create order
        order = await trading_service.create_order(
            user_id=user.id,
            order_data=order_data.dict()
        )
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "order_created",
            "order": order.to_dict()
        })
        
        # For paper trading or simulation, auto-execute market orders
        if order.is_paper_trade and order.order_type == "market":
            # Simulate execution
            current_price = order_data.estimated_price or 1000.0  # Default simulation price
            execution_data = {
                "quantity": order.quantity,
                "price": current_price,
                "commission": 100.0,  # Simulation commission
                "fees": 0.0,
                "market_price": current_price
            }
            
            trade = await trading_service.execute_trade(order.id, execution_data)
            if trade:
                await websocket_manager.send_portfolio_update(user.id, {
                    "action": "trade_executed",
                    "trade": trade.to_dict()
                })
        
        return {
            "message": "注文が作成されました",
            "order": order.to_dict()
        }
        
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文作成に失敗しました"
        )


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """注文詳細取得"""
    try:
        trading_service = TradingService(db)
        
        try:
            order_uuid = UUID(order_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な注文IDです"
            )
        
        order = await trading_service.get_order(order_uuid, user.id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="注文が見つかりません"
            )
        
        # Get trades for this order
        all_trades = await trading_service.get_user_trades(user.id)
        order_trades = [t for t in all_trades if t.order_id == order.id]
        
        order_dict = order.to_dict()
        order_dict["trades"] = [trade.to_dict() for trade in order_trades]
        
        return order_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文取得に失敗しました"
        )


@router.put("/orders/{order_id}")
async def update_order(
    order_id: str,
    update_data: OrderUpdate,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """注文更新"""
    try:
        trading_service = TradingService(db)
        
        try:
            order_uuid = UUID(order_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な注文IDです"
            )
        
        # Filter out None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        order = await trading_service.update_order(order_uuid, user.id, update_dict)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="注文が見つからないか、更新できません"
            )
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "order_updated",
            "order": order.to_dict()
        })
        
        return {
            "message": "注文が更新されました",
            "order": order.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文更新に失敗しました"
        )


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """注文キャンセル"""
    try:
        trading_service = TradingService(db)
        
        try:
            order_uuid = UUID(order_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な注文IDです"
            )
        
        success = await trading_service.cancel_order(order_uuid, user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="注文をキャンセルできません"
            )
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "order_cancelled",
            "order_id": order_id
        })
        
        return {"message": "注文がキャンセルされました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注文キャンセルに失敗しました"
        )


@router.get("/history")
async def get_trade_history(
    portfolio_id: Optional[str] = Query(None, description="ポートフォリオIDでフィルタ"),
    symbol: Optional[str] = Query(None, description="銘柄でフィルタ"),
    limit: int = Query(50, description="取得件数"),
    offset: int = Query(0, description="オフセット"),
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """取引履歴取得"""
    try:
        trading_service = TradingService(db)
        
        portfolio_uuid = UUID(portfolio_id) if portfolio_id else None
        trades = await trading_service.get_user_trades(
            user.id, portfolio_uuid, symbol, limit, offset
        )
        
        trades_data = [trade.to_dict() for trade in trades]
        
        return {
            "trades": trades_data,
            "total_count": len(trades_data),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get trade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取引履歴取得に失敗しました"
        )


@router.get("/statistics")
async def get_trading_statistics(
    portfolio_id: Optional[str] = Query(None, description="ポートフォリオIDでフィルタ"),
    period_days: int = Query(30, description="分析期間（日数）"),
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """取引統計分析"""
    try:
        trading_service = TradingService(db)
        
        portfolio_uuid = UUID(portfolio_id) if portfolio_id else None
        stats = await trading_service.get_trading_statistics(
            user.id, portfolio_uuid, period_days
        )
        
        return {
            "statistics": stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get trading statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取引統計取得に失敗しました"
        )


@router.get("/market-data/{symbol}")
async def get_market_data(
    symbol: str,
    user: AuthUser = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """リアルタイム市場データ取得"""
    try:
        # Get real-time market data using enhanced service
        market_data = await market_data_service.get_stock_price(symbol)
        
        # Get technical indicators
        technical_data = await market_data_service.get_technical_indicators(symbol)
        
        # Get company info
        company_info = await market_data_service.get_company_info(symbol)
        
        # Combine all market data
        combined_data = {
            **market_data,
            "company_info": company_info if "error" not in company_info else {},
            "technical_indicators": technical_data if "error" not in technical_data else {},
            "bid_ask": {
                "bid": market_data.get("current_price", 1000) - 1,
                "ask": market_data.get("current_price", 1000) + 1,
                "bid_size": 1000,
                "ask_size": 1500
            }
        }
        
        return combined_data
        
    except Exception as e:
        logger.error(f"Failed to get market data for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="市場データ取得に失敗しました"
        )


@router.post("/price-alerts")
async def create_price_alert(
    alert_data: PriceAlert,
    user: AuthUser = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """価格アラート作成"""
    try:
        alert_id = f"alert:{user.id}:{alert_data.symbol}:{datetime.utcnow().timestamp()}"
        
        alert_info = {
            "id": alert_id,
            "user_id": str(user.id),
            "symbol": alert_data.symbol,
            "condition": alert_data.condition,
            "target_price": alert_data.target_price,
            "percentage_change": alert_data.percentage_change,
            "is_active": alert_data.is_active,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store alert in Redis
        await redis_client.set_cache(alert_id, alert_info, expire_seconds=86400 * 30)  # 30 days
        
        # Add to user's alert list
        user_alerts_key = f"user_alerts:{user.id}"
        alerts = await redis_client.get_cache(user_alerts_key) or []
        alerts.append(alert_id)
        await redis_client.set_cache(user_alerts_key, alerts, expire_seconds=86400 * 30)
        
        return {
            "message": "価格アラートが作成されました",
            "alert": alert_info
        }
        
    except Exception as e:
        logger.error(f"Failed to create price alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="価格アラート作成に失敗しました"
        )


@router.get("/price-alerts")
async def get_user_price_alerts(
    user: AuthUser = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """ユーザーの価格アラート一覧"""
    try:
        user_alerts_key = f"user_alerts:{user.id}"
        alert_ids = await redis_client.get_cache(user_alerts_key) or []
        
        alerts = []
        for alert_id in alert_ids:
            alert_info = await redis_client.get_cache(alert_id)
            if alert_info and alert_info.get("is_active"):
                alerts.append(alert_info)
        
        return {
            "alerts": alerts,
            "total_count": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"Failed to get price alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="価格アラート取得に失敗しました"
        )


@router.post("/orders/{order_id}/execute")
async def execute_trade_manual(
    order_id: str,
    execution_data: TradeExecution,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """手動取引実行（テスト・シミュレーション用）"""
    try:
        trading_service = TradingService(db)
        
        try:
            order_uuid = UUID(order_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な注文IDです"
            )
        
        # Execute trade
        trade = await trading_service.execute_trade(
            order_uuid, execution_data.dict()
        )
        
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="取引を実行できません"
            )
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "trade_executed",
            "trade": trade.to_dict()
        })
        
        return {
            "message": "取引が実行されました",
            "trade": trade.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute trade for order {order_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取引実行に失敗しました"
        )