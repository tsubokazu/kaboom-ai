# app/routers/ai_analysis.py

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.services.advanced_ai_service import (
    AdvancedAIService, ConsensusResult, ConsensusStrategy, ModelWeight,
    ModelOptimizer
)
from app.services.market_data_service import market_data_service
from app.middleware.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI Analysis"])

# Pydantic Models
class ConsensusAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="銘柄コード")
    strategy: ConsensusStrategy = Field(ConsensusStrategy.WEIGHTED_AVERAGE, description="合意戦略")
    cache_minutes: int = Field(30, ge=1, le=1440, description="キャッシュ時間（分）")
    include_chart_analysis: bool = Field(False, description="チャート画像分析を含める")

class ModelWeightRequest(BaseModel):
    technical_weight: float = Field(1.0, ge=0.1, le=2.0)
    sentiment_weight: float = Field(1.0, ge=0.1, le=2.0) 
    risk_weight: float = Field(1.0, ge=0.1, le=2.0)
    general_weight: float = Field(0.5, ge=0.1, le=2.0)

class BatchAnalysisRequest(BaseModel):
    symbols: List[str] = Field(..., max_items=10, description="分析する銘柄リスト（最大10）")
    strategy: ConsensusStrategy = Field(ConsensusStrategy.WEIGHTED_AVERAGE)
    cache_minutes: int = Field(30, ge=1, le=1440)

# API Endpoints
@router.post("/consensus-analysis", response_model=Dict[str, Any])
async def multi_model_consensus_analysis(
    request: ConsensusAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """マルチモデル合意分析"""
    try:
        # 市場データ取得
        market_data = await market_data_service.get_comprehensive_data(request.symbol)
        
        # AI分析実行
        async with AdvancedAIService() as ai_service:
            result = await ai_service.multi_model_consensus_analysis(
                symbol=request.symbol,
                market_data=market_data,
                strategy=request.strategy,
                cache_minutes=request.cache_minutes
            )
        
        # 分析ログ記録（バックグラウンド）
        background_tasks.add_task(
            _log_analysis_result,
            current_user.id,
            request.symbol,
            result
        )
        
        return {
            "symbol": request.symbol,
            "analysis_result": {
                "final_decision": result.final_decision,
                "consensus_confidence": result.consensus_confidence,
                "reasoning": result.reasoning,
                "agreement_level": result.agreement_level,
                "processing_time": result.processing_time,
                "total_cost": result.total_cost,
                "timestamp": result.timestamp.isoformat()
            },
            "detailed_analysis": {
                "technical": {
                    "decision": result.technical_analysis.decision if result.technical_analysis else None,
                    "confidence": result.technical_analysis.confidence if result.technical_analysis else None,
                    "reasoning": result.technical_analysis.reasoning if result.technical_analysis else None
                } if result.technical_analysis else None,
                "sentiment": {
                    "decision": result.sentiment_analysis.decision if result.sentiment_analysis else None,
                    "confidence": result.sentiment_analysis.confidence if result.sentiment_analysis else None,
                    "reasoning": result.sentiment_analysis.reasoning if result.sentiment_analysis else None
                } if result.sentiment_analysis else None,
                "risk": {
                    "decision": result.risk_analysis.decision if result.risk_analysis else None,
                    "confidence": result.risk_analysis.confidence if result.risk_analysis else None,
                    "reasoning": result.risk_analysis.reasoning if result.risk_analysis else None
                } if result.risk_analysis else None
            },
            "statistics": {
                "confidence_distribution": result.confidence_distribution,
                "decision_breakdown": result.decision_breakdown,
                "model_count": len(result.individual_results)
            },
            "market_context": market_data
        }
        
    except Exception as e:
        logger.error(f"Consensus analysis failed for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"AI分析でエラーが発生しました: {str(e)}")

@router.post("/batch-analysis", response_model=Dict[str, Any])
async def batch_consensus_analysis(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """複数銘柄の一括AI分析"""
    if not current_user.is_premium:
        raise HTTPException(status_code=403, detail="プレミアムユーザーのみ利用可能です")
    
    try:
        results = {}
        total_cost = 0.0
        processing_start = datetime.utcnow()
        
        async with AdvancedAIService() as ai_service:
            for symbol in request.symbols:
                try:
                    market_data = await market_data_service.get_comprehensive_data(symbol)
                    
                    result = await ai_service.multi_model_consensus_analysis(
                        symbol=symbol,
                        market_data=market_data,
                        strategy=request.strategy,
                        cache_minutes=request.cache_minutes
                    )
                    
                    results[symbol] = {
                        "decision": result.final_decision,
                        "confidence": result.consensus_confidence,
                        "reasoning": result.reasoning,
                        "agreement_level": result.agreement_level,
                        "cost": result.total_cost
                    }
                    
                    total_cost += result.total_cost
                    
                except Exception as e:
                    logger.error(f"Analysis failed for {symbol}: {e}")
                    results[symbol] = {
                        "error": str(e),
                        "decision": "hold",
                        "confidence": 0.0
                    }
        
        processing_time = (datetime.utcnow() - processing_start).total_seconds()
        
        # 分析ログ記録
        background_tasks.add_task(
            _log_batch_analysis,
            current_user.id,
            request.symbols,
            results,
            total_cost
        )
        
        return {
            "symbols": request.symbols,
            "results": results,
            "summary": {
                "total_cost": total_cost,
                "processing_time": processing_time,
                "success_count": len([r for r in results.values() if "error" not in r]),
                "error_count": len([r for r in results.values() if "error" in r])
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"一括分析でエラーが発生しました: {str(e)}")

@router.get("/model-performance", response_model=Dict[str, Any])
async def get_model_performance_stats(
    days: int = Query(30, ge=1, le=365, description="統計期間（日数）"),
    current_user: User = Depends(get_current_user)
):
    """AIモデルパフォーマンス統計"""
    try:
        async with AdvancedAIService() as ai_service:
            stats = await ai_service.get_model_performance_stats(days)
        
        return {
            "performance_stats": stats,
            "period_days": days,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get model performance stats: {e}")
        raise HTTPException(status_code=500, detail="統計取得でエラーが発生しました")

@router.post("/optimize-weights", response_model=Dict[str, Any])
async def optimize_model_weights(
    days: int = Query(90, ge=30, le=365),
    current_user: User = Depends(get_current_user)
):
    """モデル重み自動最適化"""
    if not current_user.is_premium:
        raise HTTPException(status_code=403, detail="プレミアムユーザーのみ利用可能です")
    
    try:
        optimizer = ModelOptimizer()
        
        # 過去のデータを取得（実装要）
        historical_data = []  # TODO: 実際の履歴データ取得
        
        optimized_weights = await optimizer.optimize_weights(historical_data)
        
        return {
            "optimized_weights": {
                "technical_weight": optimized_weights.technical_weight,
                "sentiment_weight": optimized_weights.sentiment_weight,
                "risk_weight": optimized_weights.risk_weight,
                "general_weight": optimized_weights.general_weight
            },
            "optimization_period": days,
            "timestamp": datetime.utcnow().isoformat(),
            "recommendation": "最適化された重みを使用することで分析精度の向上が期待されます"
        }
        
    except Exception as e:
        logger.error(f"Weight optimization failed: {e}")
        raise HTTPException(status_code=500, detail="重み最適化でエラーが発生しました")

@router.get("/analysis-history", response_model=Dict[str, Any])
async def get_analysis_history(
    symbol: Optional[str] = Query(None, description="銘柄コード（指定時は該当銘柄のみ）"),
    days: int = Query(7, ge=1, le=30, description="取得期間（日数）"),
    limit: int = Query(50, ge=1, le=100, description="最大取得件数"),
    current_user: User = Depends(get_current_user)
):
    """AI分析履歴取得"""
    try:
        # Redis から分析履歴を取得（実装要）
        # ここでは概要のみ
        
        history = {
            "analyses": [],  # 実際の履歴データ
            "summary": {
                "total_count": 0,
                "success_rate": 0.0,
                "avg_processing_time": 0.0,
                "total_cost": 0.0
            },
            "filter": {
                "symbol": symbol,
                "days": days,
                "limit": limit
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return history
        
    except Exception as e:
        logger.error(f"Failed to get analysis history: {e}")
        raise HTTPException(status_code=500, detail="履歴取得でエラーが発生しました")

class CustomAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="銘柄コード")
    custom_prompt: str = Field(..., min_length=10, max_length=1000, description="カスタムプロンプト")
    model_weights: ModelWeightRequest = Field(default_factory=ModelWeightRequest)

@router.post("/custom-analysis", response_model=Dict[str, Any])
async def custom_ai_analysis(
    request: CustomAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """カスタムAI分析（プレミアム機能）"""
    if not current_user.is_premium:
        raise HTTPException(status_code=403, detail="プレミアムユーザーのみ利用可能です")
    
    try:
        # カスタム重みでAI分析実行
        weights = ModelWeight(
            technical_weight=request.model_weights.technical_weight,
            sentiment_weight=request.model_weights.sentiment_weight,
            risk_weight=request.model_weights.risk_weight,
            general_weight=request.model_weights.general_weight
        )
        
        market_data = await market_data_service.get_comprehensive_data(request.symbol)
        market_data["custom_prompt"] = request.custom_prompt
        
        async with AdvancedAIService(weights) as ai_service:
            result = await ai_service.multi_model_consensus_analysis(
                symbol=request.symbol,
                market_data=market_data,
                strategy=ConsensusStrategy.WEIGHTED_AVERAGE
            )
        
        return {
            "symbol": request.symbol,
            "custom_prompt": request.custom_prompt,
            "model_weights": request.model_weights.dict(),
            "result": {
                "decision": result.final_decision,
                "confidence": result.consensus_confidence,
                "reasoning": result.reasoning,
                "processing_time": result.processing_time,
                "cost": result.total_cost
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Custom analysis failed for {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail="カスタム分析でエラーが発生しました")

# Helper Functions
async def _log_analysis_result(user_id: str, symbol: str, result: ConsensusResult):
    """分析結果ログ記録"""
    try:
        # データベースまたはRedisに記録
        logger.info(f"Analysis logged: user={user_id}, symbol={symbol}, decision={result.final_decision}")
    except Exception as e:
        logger.error(f"Failed to log analysis result: {e}")

async def _log_batch_analysis(user_id: str, symbols: List[str], results: Dict, total_cost: float):
    """一括分析ログ記録"""
    try:
        logger.info(f"Batch analysis logged: user={user_id}, symbols={len(symbols)}, cost=${total_cost:.4f}")
    except Exception as e:
        logger.error(f"Failed to log batch analysis: {e}")

# WebSocket Events (for real-time updates)
@router.websocket("/ws/ai-updates/{symbol}")
async def ai_analysis_websocket(websocket, symbol: str):
    """AI分析リアルタイム更新WebSocket"""
    # WebSocket実装は別途 websocket/manager.py で統合
    pass