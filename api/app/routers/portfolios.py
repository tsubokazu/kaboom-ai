"""
ポートフォリオ管理API - 投資組み合わせ・リスク管理・パフォーマンス分析

機能:
- ポートフォリオCRUD操作
- リアルタイム評価額・損益計算
- リスク分析・アロケーション管理
- AI推奨ポートフォリオ生成
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user, get_premium_user, User
from app.services.redis_client import get_redis_client, RedisClient
from app.websocket.manager import websocket_manager
from app.tasks.ai_analysis_tasks import multi_model_analysis_task
from app.tasks.backtest_tasks import portfolio_optimization_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/portfolios", tags=["Portfolios"])


# ===================================
# Pydanticモデル定義
# ===================================

class PortfolioCreate(BaseModel):
    name: str = Field(..., description="ポートフォリオ名")
    description: Optional[str] = Field(None, description="説明")
    target_allocation: Dict[str, float] = Field(..., description="目標アロケーション")
    risk_tolerance: str = Field("moderate", description="リスク許容度: conservative|moderate|aggressive")


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_allocation: Optional[Dict[str, float]] = None
    risk_tolerance: Optional[str] = None


class HoldingCreate(BaseModel):
    symbol: str = Field(..., description="銘柄コード")
    quantity: int = Field(..., gt=0, description="保有数量")
    average_cost: float = Field(..., gt=0, description="平均取得単価")


class HoldingUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    average_cost: Optional[float] = Field(None, gt=0)


# ===================================
# ポートフォリオCRUD操作
# ===================================

@router.get("/")
async def get_portfolios(
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> List[Dict[str, Any]]:
    """ユーザーのポートフォリオ一覧取得"""
    try:
        # Redisから取得（キャッシュ戦略）
        cache_key = f"user_portfolios:{user.id}"
        cached_portfolios = await redis_client.get_cache(cache_key)
        
        if cached_portfolios:
            return cached_portfolios
        
        # 実際のデータベースから取得（モック実装）
        portfolios = await _get_user_portfolios(user.id)
        
        # リアルタイム評価額計算
        for portfolio in portfolios:
            current_value = await _calculate_portfolio_value(portfolio, redis_client)
            portfolio["current_value"] = current_value
            
        # キャッシュに保存（5分）
        await redis_client.set_cache(cache_key, portfolios, expire_seconds=300)
        
        return portfolios
        
    except Exception as e:
        logger.error(f"Failed to get portfolios for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ取得に失敗しました"
        )


@router.post("/")
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """新しいポートフォリオ作成"""
    try:
        # アロケーション合計の検証
        if sum(portfolio_data.target_allocation.values()) != 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="アロケーションの合計は1.0である必要があります"
            )
        
        # ポートフォリオ作成
        new_portfolio = await _create_portfolio(user.id, portfolio_data)
        
        # キャッシュクリア
        await redis_client.delete_cache(f"user_portfolios:{user.id}")
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "created",
            "portfolio": new_portfolio
        })
        
        return {
            "message": "ポートフォリオが作成されました",
            "portfolio": new_portfolio
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ作成に失敗しました"
        )


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """ポートフォリオ詳細取得"""
    try:
        portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # 詳細データ取得
        holdings = await _get_portfolio_holdings(portfolio_id)
        performance = await _calculate_portfolio_performance(portfolio, holdings, redis_client)
        risk_metrics = await _calculate_risk_metrics(portfolio, holdings, redis_client)
        
        return {
            "portfolio": portfolio,
            "holdings": holdings,
            "performance": performance,
            "risk_metrics": risk_metrics,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ取得に失敗しました"
        )


@router.put("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: str,
    portfolio_data: PortfolioUpdate,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """ポートフォリオ更新"""
    try:
        # 存在チェック
        existing_portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        if not existing_portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # 更新実行
        updated_portfolio = await _update_portfolio(portfolio_id, portfolio_data)
        
        # キャッシュクリア
        await redis_client.delete_cache(f"user_portfolios:{user.id}")
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "updated", 
            "portfolio": updated_portfolio
        })
        
        return {
            "message": "ポートフォリオが更新されました",
            "portfolio": updated_portfolio
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ更新に失敗しました"
        )


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """ポートフォリオ削除"""
    try:
        # 存在・権限チェック
        portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # 削除実行
        await _delete_portfolio(portfolio_id)
        
        # キャッシュクリア
        await redis_client.delete_cache(f"user_portfolios:{user.id}")
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "deleted",
            "portfolio_id": portfolio_id
        })
        
        return {"message": "ポートフォリオが削除されました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ削除に失敗しました"
        )


# ===================================
# 銘柄保有情報操作
# ===================================

@router.post("/{portfolio_id}/holdings")
async def add_holding(
    portfolio_id: str,
    holding_data: HoldingCreate,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """ポートフォリオに銘柄追加"""
    try:
        # ポートフォリオ存在確認
        portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="ポートフォリオが見つかりません")
        
        # 銘柄情報検証
        await _validate_symbol(holding_data.symbol, redis_client)
        
        # 銘柄追加
        new_holding = await _add_holding(portfolio_id, holding_data)
        
        # ポートフォリオキャッシュクリア
        await redis_client.delete_cache(f"user_portfolios:{user.id}")
        
        # リアルタイム通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "holding_added",
            "portfolio_id": portfolio_id,
            "holding": new_holding
        })
        
        return {"message": "銘柄を追加しました", "holding": new_holding}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add holding: {e}")
        raise HTTPException(status_code=500, detail="銘柄追加に失敗しました")


@router.put("/{portfolio_id}/holdings/{symbol}")
async def update_holding(
    portfolio_id: str,
    symbol: str,
    holding_data: HoldingUpdate,
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """保有銘柄更新"""
    try:
        # 権限チェック
        portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="ポートフォリオが見つかりません")
        
        # 銘柄更新
        updated_holding = await _update_holding(portfolio_id, symbol, holding_data)
        
        if not updated_holding:
            raise HTTPException(status_code=404, detail="保有銘柄が見つかりません")
        
        # キャッシュクリア
        await redis_client.delete_cache(f"user_portfolios:{user.id}")
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "holding_updated",
            "portfolio_id": portfolio_id,
            "holding": updated_holding
        })
        
        return {"message": "保有銘柄を更新しました", "holding": updated_holding}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update holding: {e}")
        raise HTTPException(status_code=500, detail="保有銘柄更新に失敗しました")


# ===================================
# AI分析・最適化機能
# ===================================

@router.post("/{portfolio_id}/ai-analysis")
async def analyze_portfolio_with_ai(
    portfolio_id: str,
    analysis_options: Dict[str, Any] = {},
    user: User = Depends(get_premium_user),  # プレミアム機能
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """AI によるポートフォリオ分析"""
    try:
        portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="ポートフォリオが見つかりません")
        
        holdings = await _get_portfolio_holdings(portfolio_id)
        symbols = [holding["symbol"] for holding in holdings]
        
        # AIタスク実行（非同期）
        task_result = multi_model_analysis_task.delay({
            "symbols": symbols,
            "portfolio_data": portfolio,
            "analysis_type": "portfolio_analysis",
            "user_id": user.id
        })
        
        # タスク状況をRedisに保存
        await redis_client.set_job_status(task_result.id, "pending", {
            "message": "AI分析開始",
            "portfolio_id": portfolio_id
        })
        
        # ユーザーにタスク開始通知
        await websocket_manager.send_system_notification({
            "title": "AI分析開始",
            "message": f"ポートフォリオ「{portfolio['name']}」のAI分析を開始しました",
            "level": "info"
        }, [user.id])
        
        return {
            "message": "AI分析を開始しました",
            "task_id": task_result.id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start portfolio AI analysis: {e}")
        raise HTTPException(status_code=500, detail="AI分析開始に失敗しました")


@router.post("/{portfolio_id}/optimize")
async def optimize_portfolio(
    portfolio_id: str,
    optimization_config: Dict[str, Any] = {},
    user: User = Depends(get_premium_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """ポートフォリオ最適化"""
    try:
        portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="ポートフォリオが見つかりません")
        
        holdings = await _get_portfolio_holdings(portfolio_id)
        symbols = [holding["symbol"] for holding in holdings]
        
        # 最適化タスク実行
        task_result = portfolio_optimization_task.delay({
            "symbols": symbols,
            "portfolio_data": portfolio,
            "optimization_config": optimization_config,
            "user_id": user.id,
            "start_date": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d")
        })
        
        await redis_client.set_job_status(task_result.id, "pending", {
            "message": "ポートフォリオ最適化開始",
            "portfolio_id": portfolio_id
        })
        
        return {
            "message": "ポートフォリオ最適化を開始しました",
            "task_id": task_result.id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start portfolio optimization: {e}")
        raise HTTPException(status_code=500, detail="最適化開始に失敗しました")


# ===================================
# パフォーマンス・リスク分析
# ===================================

@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: str,
    period: str = Query("1m", regex="^(1w|1m|3m|6m|1y|all)$"),
    user: User = Depends(get_current_user),
    redis_client: RedisClient = Depends(get_redis_client)
) -> Dict[str, Any]:
    """ポートフォリオパフォーマンス取得"""
    try:
        portfolio = await _get_portfolio_by_id(portfolio_id, user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="ポートフォリオが見つかりません")
        
        # キャッシュチェック
        cache_key = f"portfolio_performance:{portfolio_id}:{period}"
        cached_performance = await redis_client.get_cache(cache_key)
        
        if cached_performance:
            return cached_performance
        
        # パフォーマンス計算
        holdings = await _get_portfolio_holdings(portfolio_id)
        performance_data = await _calculate_detailed_performance(
            portfolio, holdings, period, redis_client
        )
        
        # キャッシュ保存（10分）
        await redis_client.set_cache(cache_key, performance_data, expire_seconds=600)
        
        return performance_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance for {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail="パフォーマンス取得に失敗しました")


# ===================================
# ヘルパー関数（データベース・ビジネスロジック）
# ===================================

async def _get_user_portfolios(user_id: str) -> List[Dict[str, Any]]:
    """ユーザーポートフォリオ取得（モック実装）"""
    # 実際にはデータベースから取得
    return [
        {
            "id": "portfolio_1",
            "name": "バランス型ポートフォリオ",
            "description": "リスクとリターンのバランスを重視",
            "created_at": "2024-01-01T00:00:00Z",
            "risk_tolerance": "moderate",
            "target_allocation": {"stocks": 0.6, "bonds": 0.3, "cash": 0.1}
        }
    ]


async def _create_portfolio(user_id: str, portfolio_data: PortfolioCreate) -> Dict[str, Any]:
    """ポートフォリオ作成"""
    new_portfolio = {
        "id": f"portfolio_{datetime.utcnow().timestamp()}",
        "user_id": user_id,
        "name": portfolio_data.name,
        "description": portfolio_data.description,
        "target_allocation": portfolio_data.target_allocation,
        "risk_tolerance": portfolio_data.risk_tolerance,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # データベース保存処理（モック）
    return new_portfolio


async def _get_portfolio_by_id(portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """ポートフォリオ取得"""
    # 実際にはデータベースから取得
    if portfolio_id == "portfolio_1":
        return {
            "id": portfolio_id,
            "user_id": user_id,
            "name": "バランス型ポートフォリオ",
            "description": "リスクとリターンのバランスを重視",
            "risk_tolerance": "moderate"
        }
    return None


async def _calculate_portfolio_value(portfolio: Dict, redis_client: RedisClient) -> Dict[str, Any]:
    """ポートフォリオ現在価値計算"""
    # モック実装
    return {
        "total_value": 1500000,
        "day_change": 15000,
        "day_change_percent": 1.0
    }


async def _validate_symbol(symbol: str, redis_client: RedisClient):
    """銘柄コード検証"""
    # 実際には市場データAPIで検証
    if not symbol or len(symbol) < 4:
        raise HTTPException(status_code=400, detail="無効な銘柄コードです")


async def _add_holding(portfolio_id: str, holding_data: HoldingCreate) -> Dict[str, Any]:
    """銘柄保有情報追加"""
    return {
        "symbol": holding_data.symbol,
        "quantity": holding_data.quantity,
        "average_cost": holding_data.average_cost,
        "added_at": datetime.utcnow().isoformat()
    }


# その他のヘルパー関数（簡略化）
async def _update_portfolio(portfolio_id: str, data: PortfolioUpdate) -> Dict: return {}
async def _delete_portfolio(portfolio_id: str): pass
async def _get_portfolio_holdings(portfolio_id: str) -> List[Dict]: return []
async def _update_holding(portfolio_id: str, symbol: str, data: HoldingUpdate) -> Dict: return {}
async def _calculate_portfolio_performance(portfolio: Dict, holdings: List, redis_client: RedisClient) -> Dict: return {}
async def _calculate_risk_metrics(portfolio: Dict, holdings: List, redis_client: RedisClient) -> Dict: return {}
async def _calculate_detailed_performance(portfolio: Dict, holdings: List, period: str, redis_client: RedisClient) -> Dict: return {}