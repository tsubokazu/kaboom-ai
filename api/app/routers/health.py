# app/routers/health.py

import asyncio
import time
import psutil
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.services.openrouter_client import OpenRouterClient, AIRequest, AIAnalysisType
from app.middleware.auth import get_admin_user, User

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """基本ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "kaboom-api",
        "version": "1.0.0"
    }

@router.get("/healthz")
async def kubernetes_health_check():
    """Kubernetes/CloudRun用ヘルスチェック"""
    return {"status": "ok"}

@router.get("/health/detailed")
async def detailed_health_check(admin_user: User = Depends(get_admin_user)):
    """詳細ヘルスチェック（管理者のみ）"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service_info": {
            "name": "kaboom-api",
            "version": "1.0.0",
            "environment": "development" if settings.DEBUG else "production",
            "uptime": _get_uptime(),
        },
        "system_metrics": await _get_system_metrics(),
        "dependencies": await _check_dependencies(),
        "configuration": _get_configuration_status()
    }
    
    # 全体的な健全性判定
    overall_healthy = all([
        health_status["system_metrics"]["memory_usage_percent"] < 90,
        health_status["system_metrics"]["cpu_usage_percent"] < 90,
        all(dep["status"] == "healthy" for dep in health_status["dependencies"].values())
    ])
    
    health_status["status"] = "healthy" if overall_healthy else "degraded"
    status_code = 200 if overall_healthy else 503
    
    return JSONResponse(content=health_status, status_code=status_code)

@router.get("/health/openrouter")
async def openrouter_health_check(admin_user: User = Depends(get_admin_user)):
    """OpenRouter接続ヘルスチェック"""
    
    if not settings.OPENROUTER_API_KEY:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "OpenRouter API key not configured",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    start_time = time.time()
    
    try:
        # 簡易テスト分析実行
        async with OpenRouterClient() as client:
            test_request = AIRequest(
                analysis_type=AIAnalysisType.GENERAL,
                symbol="TEST",
                prompt="Health check test. Respond with 'OK'.",
                model="openai/gpt-3.5-turbo",  # 低コストモデル使用
                max_tokens=10
            )
            
            response = await client.analyze_stock(test_request)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": f"{response_time:.3f}s",
                "model_used": response.model,
                "cost_usd": response.cost_usd,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        response_time = time.time() - start_time
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "response_time": f"{response_time:.3f}s",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Readiness probe for Kubernetes
@router.get("/ready")
async def readiness_check():
    """アプリケーション準備状況チェック"""
    
    try:
        # 重要な依存関係の確認
        checks = {
            "openrouter_config": bool(settings.OPENROUTER_API_KEY),
            "supabase_config": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        }
        
        all_ready = all(checks.values())
        
        return JSONResponse(
            status_code=200 if all_ready else 503,
            content={
                "status": "ready" if all_ready else "not_ready",
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Liveness probe for Kubernetes
@router.get("/live")
async def liveness_check():
    """アプリケーション生存状況チェック"""
    
    try:
        # 基本的なアプリケーション機能テスト
        test_data = {"test": datetime.utcnow().isoformat()}
        
        return {
            "status": "alive",
            "test_data": test_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "dead",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# ユーティリティ関数
def _get_uptime() -> str:
    """アプリケーション稼働時間取得"""
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    except Exception:
        return "unknown"

async def _get_system_metrics() -> Dict[str, Any]:
    """システムメトリクス取得"""
    try:
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        
        # ディスク使用率
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "memory_available_mb": memory.available // (1024 * 1024),
            "memory_total_mb": memory.total // (1024 * 1024),
            "disk_usage_percent": (disk.used / disk.total) * 100,
            "disk_free_gb": disk.free // (1024 * 1024 * 1024)
        }
    except Exception as e:
        return {
            "error": f"Failed to get system metrics: {e}",
            "cpu_usage_percent": 0,
            "memory_usage_percent": 0,
            "memory_available_mb": 0,
            "memory_total_mb": 0,
            "disk_usage_percent": 0,
            "disk_free_gb": 0
        }

async def _check_dependencies() -> Dict[str, Dict[str, Any]]:
    """依存関係ヘルスチェック"""
    dependencies = {}
    
    # OpenRouter check
    dependencies["openrouter"] = {
        "status": "healthy" if settings.OPENROUTER_API_KEY else "unhealthy",
        "configured": bool(settings.OPENROUTER_API_KEY),
        "endpoint": settings.OPENROUTER_BASE_URL
    }
    
    # Supabase check
    dependencies["supabase"] = {
        "status": "healthy" if (settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY) else "unhealthy",
        "configured": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        "url": settings.SUPABASE_URL if settings.SUPABASE_URL else "not_configured"
    }
    
    # Redis check (if available)
    dependencies["redis"] = {
        "status": "unknown",  # TODO: 実際のRedis接続チェック
        "configured": bool(settings.REDIS_URL),
        "url": settings.REDIS_URL
    }
    
    return dependencies

def _get_configuration_status() -> Dict[str, Any]:
    """設定状況取得"""
    return {
        "debug_mode": settings.DEBUG,
        "openrouter": {
            "api_configured": bool(settings.OPENROUTER_API_KEY),
            "base_url": settings.OPENROUTER_BASE_URL,
            "concurrent_requests": settings.OPENROUTER_CONCURRENT_REQUESTS
        },
        "ai_settings": {
            "max_concurrent_requests": settings.MAX_CONCURRENT_AI_REQUESTS,
            "analysis_timeout": settings.AI_ANALYSIS_TIMEOUT
        },
        "rate_limiting": {
            "per_minute": settings.RATE_LIMIT_PER_MINUTE
        }
    }