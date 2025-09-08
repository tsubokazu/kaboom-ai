# app/routers/ai_analysis.py

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, validator

from app.middleware.auth import get_current_user, get_premium_user, User
from app.services.openrouter_client import (
    AIRequest, 
    AIResponse, 
    AIAnalysisType, 
    AIAnalysisService,
    generate_idempotency_key
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI Analysis"])

# Request/Response Models
class AIAnalysisRequest(BaseModel):
    symbol: str = Field(..., pattern=r'^[0-9]{4}$', description="4-digit Japanese stock code")
    symbol_name: Optional[str] = Field(None, max_length=200, description="Optional symbol name")
    analysis_types: List[str] = Field(..., min_items=1, max_items=3)
    models: Optional[List[str]] = Field(None, description="Specific OpenRouter models to use")
    timeframes: List[str] = Field(["1h", "4h", "1d"], min_items=1, max_items=6)
    include_chart: bool = Field(True, description="Generate chart images for analysis")
    priority: str = Field("normal", pattern=r'^(low|normal|high|urgent)$')
    
    @validator('analysis_types')
    def validate_analysis_types(cls, v):
        valid_types = ['technical', 'sentiment', 'risk']
        for analysis_type in v:
            if analysis_type not in valid_types:
                raise ValueError(f'Invalid analysis type: {analysis_type}')
        return v
    
    @validator('timeframes')
    def validate_timeframes(cls, v):
        valid_frames = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']
        for frame in v:
            if frame not in valid_frames:
                raise ValueError(f'Invalid timeframe: {frame}')
        return v

class AIModelResultResponse(BaseModel):
    model: str
    analysis_type: str
    decision: str
    confidence: float
    reasoning: str
    cost_usd: float
    processing_time: float

class AIAnalysisResponse(BaseModel):
    job_id: str
    status: str
    symbol: str
    estimated_completion: Optional[str] = None
    model_results: Optional[List[AIModelResultResponse]] = None
    final_decision: Optional[str] = None
    consensus_confidence: Optional[float] = None
    total_cost: Optional[float] = None
    created_at: str
    completed_at: Optional[str] = None

# 分析ジョブストレージ（実際にはRedis/DBを使用）
analysis_jobs: Dict[str, Dict[str, Any]] = {}

@router.post("/analyze", response_model=AIAnalysisResponse)
async def submit_ai_analysis(
    request: AIAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """AI分析ジョブ投入"""
    
    # クォータチェック (簡易実装)
    daily_usage = await _check_user_daily_ai_usage(current_user.id)
    max_daily_analyses = _get_user_ai_quota(current_user.role)
    
    if daily_usage >= max_daily_analyses:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI analysis quota exceeded. Limit: {max_daily_analyses}, Used: {daily_usage}"
        )
    
    # 冪等性チェック
    idempotency_key = generate_idempotency_key(
        request.symbol,
        {"types": request.analysis_types, "models": request.models or []}
    )
    
    existing_job = await _check_existing_analysis(idempotency_key)
    if existing_job:
        return AIAnalysisResponse(**existing_job)
    
    # ジョブID生成
    job_id = str(uuid4())
    
    # ジョブ初期状態作成
    job_data = {
        "job_id": job_id,
        "status": "queued",
        "symbol": request.symbol,
        "user_id": current_user.id,
        "request_data": request.dict(),
        "created_at": datetime.utcnow().isoformat(),
        "estimated_completion": (datetime.utcnow() + timedelta(minutes=2)).isoformat(),
        "idempotency_key": idempotency_key
    }
    
    # ジョブストレージに保存
    analysis_jobs[job_id] = job_data
    
    # バックグラウンドタスクで分析実行
    background_tasks.add_task(
        _execute_ai_analysis_task,
        job_id,
        request,
        current_user.id
    )
    
    return AIAnalysisResponse(
        job_id=job_id,
        status="queued",
        symbol=request.symbol,
        estimated_completion=job_data["estimated_completion"],
        created_at=job_data["created_at"]
    )

@router.get("/analysis/{job_id}", response_model=AIAnalysisResponse)
async def get_ai_analysis_result(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """AI分析結果取得"""
    
    if job_id not in analysis_jobs:
        raise HTTPException(
            status_code=404,
            detail="AI analysis job not found"
        )
    
    job_data = analysis_jobs[job_id]
    
    # 認可チェック
    if job_data["user_id"] != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this analysis job"
        )
    
    return AIAnalysisResponse(**job_data)

@router.get("/decisions")
async def get_ai_analysis_history(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """AI分析履歴取得"""
    
    # ユーザーの分析ジョブを検索
    user_jobs = [
        job for job in analysis_jobs.values() 
        if job["user_id"] == current_user.id and job["status"] == "completed"
    ]
    
    # フィルタリング
    if symbol:
        user_jobs = [job for job in user_jobs if job["symbol"] == symbol]
    
    # TODO: date filtering implementation
    
    # ページネーション
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_jobs = user_jobs[start_idx:end_idx]
    
    return {
        "items": paginated_jobs,
        "total": len(user_jobs),
        "page": page,
        "limit": limit
    }

@router.delete("/analysis/{job_id}")
async def cancel_ai_analysis(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """AI分析ジョブキャンセル"""
    
    if job_id not in analysis_jobs:
        raise HTTPException(
            status_code=404,
            detail="AI analysis job not found"
        )
    
    job_data = analysis_jobs[job_id]
    
    # 認可チェック
    if job_data["user_id"] != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied to this analysis job"
        )
    
    # 実行中のジョブのみキャンセル可能
    if job_data["status"] in ["queued", "processing"]:
        job_data["status"] = "cancelled"
        job_data["cancelled_at"] = datetime.utcnow().isoformat()
        
        return {"message": "AI analysis job cancelled successfully"}
    else:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel job in status: {job_data['status']}"
        )

@router.get("/quota")
async def get_user_ai_quota(current_user: User = Depends(get_current_user)):
    """ユーザーAIクォータ状況取得"""
    
    daily_usage = await _check_user_daily_ai_usage(current_user.id)
    monthly_usage = await _check_user_monthly_ai_usage(current_user.id)
    
    max_daily = _get_user_ai_quota(current_user.role)
    max_monthly = max_daily * 30  # 簡易計算
    
    return {
        "user_role": current_user.role,
        "daily_quota": {
            "used": daily_usage,
            "limit": max_daily,
            "remaining": max(0, max_daily - daily_usage)
        },
        "monthly_quota": {
            "used": monthly_usage,
            "limit": max_monthly,
            "remaining": max(0, max_monthly - monthly_usage)
        }
    }

# バックグラウンドタスク
async def _execute_ai_analysis_task(job_id: str, request: AIAnalysisRequest, user_id: str):
    """AI分析実行タスク"""
    
    try:
        # ジョブ状況更新
        analysis_jobs[job_id]["status"] = "processing"
        analysis_jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Starting AI analysis job {job_id} for user {user_id}, symbol {request.symbol}")
        
        # AI分析実行
        results = []
        total_cost = 0.0
        
        async with AIAnalysisService() as ai_service:
            for analysis_type in request.analysis_types:
                ai_request = AIRequest(
                    analysis_type=AIAnalysisType(analysis_type),
                    symbol=request.symbol,
                    prompt=f"銘柄{request.symbol}の{analysis_type}分析を実行してください。現在価格情報に基づく投資判断をお願いします。"
                )
                
                try:
                    response = await ai_service.analyze_with_fallback(ai_request)
                    
                    results.append(AIModelResultResponse(
                        model=response.model,
                        analysis_type=analysis_type,
                        decision=response.decision,
                        confidence=response.confidence,
                        reasoning=response.reasoning,
                        cost_usd=response.cost_usd,
                        processing_time=response.processing_time
                    ))
                    
                    total_cost += response.cost_usd
                    
                except Exception as e:
                    logger.error(f"AI analysis failed for {analysis_type}: {e}")
                    # 部分的な失敗は続行
        
        # 合意形成
        if results:
            decisions = [r.decision for r in results]
            final_decision = max(set(decisions), key=decisions.count)  # 多数決
            consensus_confidence = sum(r.confidence for r in results) / len(results)
        else:
            final_decision = "hold"
            consensus_confidence = 0.5
        
        # ジョブ完了更新
        analysis_jobs[job_id].update({
            "status": "completed",
            "model_results": [result.dict() for result in results],
            "final_decision": final_decision,
            "consensus_confidence": consensus_confidence,
            "total_cost": total_cost,
            "completed_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"AI analysis job {job_id} completed successfully. Decision: {final_decision}")
        
    except Exception as e:
        logger.error(f"AI analysis job {job_id} failed: {e}", exc_info=True)
        
        analysis_jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat()
        })

# ヘルパー関数
async def _check_user_daily_ai_usage(user_id: str) -> int:
    """ユーザーの日次AI使用量チェック（簡易実装）"""
    # 実際にはRedis/DBから取得
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_jobs = [
        job for job in analysis_jobs.values()
        if job["user_id"] == user_id and job["created_at"].startswith(today)
    ]
    return len(daily_jobs)

async def _check_user_monthly_ai_usage(user_id: str) -> int:
    """ユーザーの月次AI使用量チェック（簡易実装）"""
    # 実際にはRedis/DBから取得
    current_month = datetime.utcnow().strftime("%Y-%m")
    monthly_jobs = [
        job for job in analysis_jobs.values()
        if job["user_id"] == user_id and job["created_at"].startswith(current_month)
    ]
    return len(monthly_jobs)

def _get_user_ai_quota(user_role: str) -> int:
    """ユーザー役割別AI分析クォータ取得"""
    quotas = {
        "basic": 10,
        "premium": 100,
        "enterprise": 1000,
        "admin": 10000
    }
    return quotas.get(user_role, 10)

async def _check_existing_analysis(idempotency_key: str) -> Optional[Dict[str, Any]]:
    """既存分析の冪等性チェック"""
    # 1時間以内の同じ分析を検索
    cutoff_time = datetime.utcnow() - timedelta(hours=1)
    
    for job in analysis_jobs.values():
        job_created = datetime.fromisoformat(job["created_at"])
        if (job.get("idempotency_key") == idempotency_key and 
            job_created > cutoff_time and 
            job["status"] == "completed"):
            return job
    
    return None