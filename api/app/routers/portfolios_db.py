"""
ポートフォリオ管理API - データベース統合版
投資組み合わせ・リスク管理・パフォーマンス分析

機能:
- ポートフォリオCRUD操作（実データベース）
- リアルタイム評価額・損益計算
- リスク分析・アロケーション管理
- AI推奨ポートフォリオ生成
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.middleware.auth import get_current_user, get_premium_user, User as AuthUser
from app.services.portfolio_service import PortfolioService
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
    portfolio_type: str = Field("trading", description="ポートフォリオタイプ")
    initial_capital: float = Field(1000000.0, description="初期資本")
    currency: str = Field("JPY", description="通貨")
    ai_enabled: bool = Field(False, description="AI有効化")
    risk_limit: float = Field(10.0, description="リスク制限（%）")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ai_enabled: Optional[bool] = None
    risk_limit: Optional[float] = None
    rebalancing_frequency: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HoldingCreate(BaseModel):
    symbol: str = Field(..., description="銘柄コード")
    quantity: int = Field(..., gt=0, description="保有数量")
    average_cost: float = Field(..., gt=0, description="平均取得単価")
    company_name: Optional[str] = Field(None, description="会社名")
    sector: Optional[str] = Field(None, description="セクター")
    market: str = Field("TSE", description="取引所")
    current_price: Optional[float] = Field(None, description="現在価格")


class AnalysisRequest(BaseModel):
    analysis_type: str = Field(..., description="分析タイプ: risk|performance|allocation")
    period: str = Field("1m", description="分析期間: 1d|1w|1m|3m|1y")


# ===================================
# APIエンドポイント
# ===================================

@router.get("/")
async def get_user_portfolios(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ユーザーのポートフォリオ一覧取得"""
    try:
        portfolio_service = PortfolioService(db)
        portfolios = await portfolio_service.get_user_portfolios(user.id)
        
        portfolio_list = []
        for portfolio in portfolios:
            portfolio_dict = portfolio.to_dict()
            # Calculate metrics
            metrics = await portfolio_service.calculate_portfolio_metrics(portfolio.id)
            portfolio_dict.update(metrics)
            portfolio_list.append(portfolio_dict)
        
        return {
            "portfolios": portfolio_list,
            "total_count": len(portfolio_list)
        }
        
    except Exception as e:
        logger.error(f"Failed to get user portfolios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ一覧取得に失敗しました"
        )


@router.post("/")
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """新しいポートフォリオ作成"""
    try:
        portfolio_service = PortfolioService(db)
        
        # Create portfolio
        portfolio = await portfolio_service.create_portfolio(
            user_id=user.id,
            portfolio_data=portfolio_data.dict()
        )
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "created",
            "portfolio": portfolio.to_dict()
        })
        
        return {
            "message": "ポートフォリオが作成されました",
            "portfolio": portfolio.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to create portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ作成に失敗しました"
        )


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ポートフォリオ詳細取得"""
    try:
        portfolio_service = PortfolioService(db)
        
        # Convert string to UUID
        try:
            portfolio_uuid = UUID(portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なポートフォリオIDです"
            )
        
        portfolio = await portfolio_service.get_portfolio(portfolio_uuid, user.id)
        
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # Calculate current metrics
        metrics = await portfolio_service.calculate_portfolio_metrics(portfolio.id)
        
        portfolio_data = portfolio.to_dict()
        portfolio_data.update(metrics)
        
        # Include holdings
        holdings_data = []
        for holding in portfolio.holdings:
            if holding.is_active:
                holdings_data.append(holding.to_dict())
        
        portfolio_data["holdings"] = holdings_data
        
        return portfolio_data
        
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
    update_data: PortfolioUpdate,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ポートフォリオ更新"""
    try:
        portfolio_service = PortfolioService(db)
        
        try:
            portfolio_uuid = UUID(portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なポートフォリオIDです"
            )
        
        # Filter out None values
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        portfolio = await portfolio_service.update_portfolio(
            portfolio_uuid, user.id, update_dict
        )
        
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "updated",
            "portfolio": portfolio.to_dict()
        })
        
        return {
            "message": "ポートフォリオが更新されました",
            "portfolio": portfolio.to_dict()
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
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ポートフォリオ削除"""
    try:
        portfolio_service = PortfolioService(db)
        
        try:
            portfolio_uuid = UUID(portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なポートフォリオIDです"
            )
        
        success = await portfolio_service.delete_portfolio(portfolio_uuid, user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
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


@router.post("/{portfolio_id}/holdings")
async def add_holding(
    portfolio_id: str,
    holding_data: HoldingCreate,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ポートフォリオに銘柄追加"""
    try:
        portfolio_service = PortfolioService(db)
        
        try:
            portfolio_uuid = UUID(portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なポートフォリオIDです"
            )
        
        holding = await portfolio_service.add_holding(
            portfolio_uuid, user.id, holding_data.dict()
        )
        
        if not holding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # Recalculate portfolio metrics
        await portfolio_service.calculate_portfolio_metrics(portfolio_uuid)
        
        # WebSocket通知
        await websocket_manager.send_portfolio_update(user.id, {
            "action": "holding_added",
            "portfolio_id": portfolio_id,
            "holding": holding.to_dict()
        })
        
        return {
            "message": "銘柄が追加されました",
            "holding": holding.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add holding to portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="銘柄追加に失敗しました"
        )


@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: str,
    period: str = Query("1m", description="分析期間: 1d|1w|1m|3m|1y"),
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ポートフォリオパフォーマンス分析"""
    try:
        portfolio_service = PortfolioService(db)
        
        try:
            portfolio_uuid = UUID(portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なポートフォリオIDです"
            )
        
        portfolio = await portfolio_service.get_portfolio(portfolio_uuid, user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # Calculate detailed metrics
        metrics = await portfolio_service.calculate_portfolio_metrics(portfolio_uuid)
        
        # Add performance analysis
        performance_data = {
            "period": period,
            "metrics": metrics,
            "allocation": [],
            "top_performers": [],
            "risk_analysis": {
                "risk_score": "Medium",  # Placeholder - implement actual risk calculation
                "volatility": metrics.get("volatility", 0),
                "beta": portfolio.beta or 0,
                "var_95": portfolio.var_95 or 0
            }
        }
        
        # Calculate allocation
        total_value = metrics.get("total_market_value", 0)
        if total_value > 0:
            for holding in portfolio.holdings:
                if holding.is_active and holding.market_value > 0:
                    allocation_percent = float(holding.market_value / total_value * 100)
                    performance_data["allocation"].append({
                        "symbol": holding.symbol,
                        "company_name": holding.company_name,
                        "percentage": allocation_percent,
                        "value": float(holding.market_value),
                        "pnl": float(holding.unrealized_pnl),
                        "pnl_percent": float(holding.unrealized_pnl_percent)
                    })
            
            # Sort by percentage
            performance_data["allocation"].sort(key=lambda x: x["percentage"], reverse=True)
            performance_data["top_performers"] = performance_data["allocation"][:5]
        
        return performance_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get portfolio performance {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パフォーマンス分析に失敗しました"
        )


@router.post("/{portfolio_id}/ai-analysis")
async def request_ai_analysis(
    portfolio_id: str,
    analysis_request: AnalysisRequest,
    user: AuthUser = Depends(get_premium_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """AI分析リクエスト（プレミアム機能）"""
    try:
        portfolio_service = PortfolioService(db)
        
        try:
            portfolio_uuid = UUID(portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なポートフォリオIDです"
            )
        
        portfolio = await portfolio_service.get_portfolio(portfolio_uuid, user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # Prepare portfolio data for analysis
        portfolio_data = portfolio.to_dict()
        holdings_data = [holding.to_dict() for holding in portfolio.holdings if holding.is_active]
        
        analysis_data = {
            "portfolio": portfolio_data,
            "holdings": holdings_data,
            "analysis_type": analysis_request.analysis_type,
            "period": analysis_request.period,
            "user_id": str(user.id)
        }
        
        # Launch async AI analysis task
        task_result = multi_model_analysis_task.delay(analysis_data)
        
        # Store task info in cache for tracking
        redis_client = await get_redis_client()
        await redis_client.set_cache(
            f"ai_analysis:{task_result.id}",
            {
                "user_id": str(user.id),
                "portfolio_id": portfolio_id,
                "analysis_type": analysis_request.analysis_type,
                "status": "processing",
                "created_at": datetime.utcnow().isoformat()
            },
            expire_seconds=3600
        )
        
        return {
            "message": "AI分析を開始しました",
            "task_id": task_result.id,
            "estimated_completion": "2-3分後",
            "analysis_type": analysis_request.analysis_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to request AI analysis for portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI分析リクエストに失敗しました"
        )


@router.post("/{portfolio_id}/optimize")
async def optimize_portfolio(
    portfolio_id: str,
    user: AuthUser = Depends(get_premium_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """ポートフォリオ最適化（プレミアム機能）"""
    try:
        portfolio_service = PortfolioService(db)
        
        try:
            portfolio_uuid = UUID(portfolio_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なポートフォリオIDです"
            )
        
        portfolio = await portfolio_service.get_portfolio(portfolio_uuid, user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ポートフォリオが見つかりません"
            )
        
        # Prepare data for optimization
        optimization_data = {
            "portfolio_id": str(portfolio.id),
            "user_id": str(user.id),
            "current_holdings": [holding.to_dict() for holding in portfolio.holdings if holding.is_active],
            "risk_tolerance": portfolio.risk_limit,
            "target_return": 10.0,  # Default target return
            "constraints": {
                "max_single_position": 20.0,  # Max 20% in single position
                "min_positions": 5,
                "max_positions": 15
            }
        }
        
        # Launch async optimization task
        task_result = portfolio_optimization_task.delay(optimization_data)
        
        # Store task info in cache
        redis_client = await get_redis_client()
        await redis_client.set_cache(
            f"portfolio_optimization:{task_result.id}",
            {
                "user_id": str(user.id),
                "portfolio_id": portfolio_id,
                "status": "processing",
                "created_at": datetime.utcnow().isoformat()
            },
            expire_seconds=3600
        )
        
        return {
            "message": "ポートフォリオ最適化を開始しました",
            "task_id": task_result.id,
            "estimated_completion": "3-5分後"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to optimize portfolio {portfolio_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ポートフォリオ最適化に失敗しました"
        )