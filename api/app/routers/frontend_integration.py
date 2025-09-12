# app/routers/frontend_integration.py

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json
from pathlib import Path

from app.services.redis_client import redis_client
from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/frontend", tags=["Frontend Integration"])

# Pydantic Models
class HealthCheckResponse(BaseModel):
    status: str = "healthy"
    timestamp: str
    version: str = "1.0.0"
    services: Dict[str, str]

class WebSocketInfoResponse(BaseModel):
    websocket_url: str
    available_channels: List[str]
    connection_info: Dict[str, Any]

class ApiInfoResponse(BaseModel):
    total_endpoints: int
    endpoint_groups: Dict[str, int]
    features: List[str]
    rate_limits: Dict[str, str]

# Frontend Support Endpoints
@router.get("/health", response_model=HealthCheckResponse)
async def frontend_health_check():
    """フロントエンド向けヘルスチェック"""
    try:
        # サービス状態確認
        services = {}
        
        # Redis接続確認
        try:
            await redis_client.ping()
            services["redis"] = "healthy"
        except:
            services["redis"] = "unhealthy"
        
        # WebSocket接続確認
        services["websocket"] = "healthy" if websocket_manager else "unhealthy"
        
        # データベース接続確認
        try:
            from app.database.connection import check_database_health
            db_health = await check_database_health()
            services["database"] = "healthy" if db_health.get("status") == "connected" else "unhealthy"
        except:
            services["database"] = "unhealthy"
        
        return HealthCheckResponse(
            status="healthy" if all(s == "healthy" for s in services.values()) else "degraded",
            timestamp=datetime.utcnow().isoformat(),
            services=services
        )
        
    except Exception as e:
        logger.error(f"Frontend health check failed: {e}")
        raise HTTPException(status_code=500, detail="ヘルスチェックでエラーが発生しました")

@router.get("/websocket/info", response_model=WebSocketInfoResponse)
async def get_websocket_info(request: Request):
    """WebSocket接続情報取得"""
    try:
        # WebSocket URL構築
        host = request.headers.get("host", "localhost:8000")
        protocol = "wss" if request.url.scheme == "https" else "ws"
        websocket_url = f"{protocol}://{host}/ws"
        
        # 利用可能チャンネル
        available_channels = [
            "price_updates",
            "portfolio_updates", 
            "order_updates",
            "ai_analysis",
            "system_alerts",
            "market_news"
        ]
        
        # 接続情報
        connection_info = {
            "max_connections": 1000,
            "heartbeat_interval": 30,
            "reconnect_strategy": "exponential_backoff",
            "message_format": "json",
            "compression": "deflate"
        }
        
        return WebSocketInfoResponse(
            websocket_url=websocket_url,
            available_channels=available_channels,
            connection_info=connection_info
        )
        
    except Exception as e:
        logger.error(f"WebSocket info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="WebSocket情報取得でエラーが発生しました")

@router.get("/api/info", response_model=ApiInfoResponse)
async def get_api_info():
    """API情報取得"""
    try:
        from app.main import app
        
        # エンドポイント集計
        total_endpoints = 0
        endpoint_groups = {
            "authentication": 0,
            "portfolios": 0,
            "trading": 0,
            "ai_analysis": 0,
            "admin": 0,
            "health": 0,
            "other": 0
        }
        
        for route in app.routes:
            if hasattr(route, 'path'):
                total_endpoints += 1
                path = route.path
                
                if '/auth' in path:
                    endpoint_groups["authentication"] += 1
                elif '/portfolios' in path:
                    endpoint_groups["portfolios"] += 1
                elif '/trading' in path or '/trades' in path:
                    endpoint_groups["trading"] += 1
                elif '/ai' in path:
                    endpoint_groups["ai_analysis"] += 1
                elif '/admin' in path:
                    endpoint_groups["admin"] += 1
                elif '/health' in path:
                    endpoint_groups["health"] += 1
                else:
                    endpoint_groups["other"] += 1
        
        # 機能リスト
        features = [
            "Real-time price updates",
            "AI-powered analysis",
            "Multi-model consensus",
            "Portfolio management", 
            "Order execution",
            "Risk management",
            "Performance reporting",
            "Admin dashboard",
            "WebSocket streaming",
            "RESTful APIs"
        ]
        
        # レート制限
        rate_limits = {
            "authenticated": "1000 requests/hour",
            "unauthenticated": "100 requests/hour",
            "websocket": "100 connections/user",
            "ai_analysis": "50 requests/hour (premium: 500)"
        }
        
        return ApiInfoResponse(
            total_endpoints=total_endpoints,
            endpoint_groups=endpoint_groups,
            features=features,
            rate_limits=rate_limits
        )
        
    except Exception as e:
        logger.error(f"API info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="API情報取得でエラーが発生しました")

@router.get("/types/download")
async def download_typescript_types():
    """TypeScript型定義ダウンロード"""
    try:
        # 型定義ファイルパス
        types_file = Path(__file__).parent.parent.parent / "generated" / "types" / "api-types.ts"
        
        if not types_file.exists():
            # 型定義が存在しない場合は生成
            import subprocess
            import sys
            
            script_path = Path(__file__).parent.parent.parent / "scripts" / "generate_types.py"
            result = subprocess.run([sys.executable, str(script_path)], capture_output=True)
            
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500, 
                    detail="型定義生成でエラーが発生しました"
                )
        
        if types_file.exists():
            return FileResponse(
                types_file,
                media_type="text/plain",
                filename="api-types.ts"
            )
        else:
            raise HTTPException(status_code=404, detail="型定義ファイルが見つかりません")
            
    except Exception as e:
        logger.error(f"TypeScript types download failed: {e}")
        raise HTTPException(status_code=500, detail="型定義ダウンロードでエラーが発生しました")

@router.get("/openapi/download")
async def download_openapi_spec():
    """OpenAPI仕様書ダウンロード"""
    try:
        # OpenAPI仕様書ファイルパス
        openapi_file = Path(__file__).parent.parent.parent / "generated" / "openapi.json"
        
        if not openapi_file.exists():
            # 仕様書が存在しない場合は生成
            import subprocess
            import sys
            
            script_path = Path(__file__).parent.parent.parent / "scripts" / "generate_types.py"
            result = subprocess.run([sys.executable, str(script_path)], capture_output=True)
            
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail="OpenAPI仕様書生成でエラーが発生しました"
                )
        
        if openapi_file.exists():
            return FileResponse(
                openapi_file,
                media_type="application/json",
                filename="openapi.json"
            )
        else:
            raise HTTPException(status_code=404, detail="OpenAPI仕様書が見つかりません")
            
    except Exception as e:
        logger.error(f"OpenAPI spec download failed: {e}")
        raise HTTPException(status_code=500, detail="OpenAPI仕様書ダウンロードでエラーが発生しました")

@router.get("/sample-data/{data_type}")
async def get_sample_data(data_type: str):
    """フロントエンド開発用サンプルデータ"""
    try:
        sample_data = {}
        
        if data_type == "portfolio":
            sample_data = {
                "id": "sample_portfolio_001",
                "name": "サンプルポートフォリオ",
                "total_value": 1500000.0,
                "total_return": 75000.0,
                "total_return_percent": 5.26,
                "daily_change": 12500.0,
                "daily_change_percent": 0.84,
                "holdings": [
                    {
                        "symbol": "7203",
                        "company_name": "トヨタ自動車",
                        "quantity": 100,
                        "average_cost": 2600.0,
                        "current_price": 2650.0,
                        "market_value": 265000.0,
                        "unrealized_pnl": 5000.0,
                        "weight": 17.67
                    },
                    {
                        "symbol": "6758",
                        "company_name": "ソニーグループ",
                        "quantity": 50,
                        "average_cost": 8400.0,
                        "current_price": 8500.0,
                        "market_value": 425000.0,
                        "unrealized_pnl": 5000.0,
                        "weight": 28.33
                    }
                ]
            }
        
        elif data_type == "trades":
            sample_data = {
                "trades": [
                    {
                        "id": "trade_001",
                        "symbol": "7203",
                        "side": "buy",
                        "quantity": 100,
                        "price": 2600.0,
                        "total_amount": 260000.0,
                        "commission": 275.0,
                        "executed_at": "2024-01-15T09:30:00Z",
                        "status": "filled"
                    },
                    {
                        "id": "trade_002",
                        "symbol": "6758", 
                        "side": "buy",
                        "quantity": 50,
                        "price": 8400.0,
                        "total_amount": 420000.0,
                        "commission": 420.0,
                        "executed_at": "2024-01-16T10:15:00Z",
                        "status": "filled"
                    }
                ]
            }
        
        elif data_type == "ai-analysis":
            sample_data = {
                "symbol": "7203",
                "analysis_result": {
                    "final_decision": "buy",
                    "consensus_confidence": 0.78,
                    "reasoning": "テクニカル指標とセンチメント分析が共に買いシグナルを示している",
                    "agreement_level": 0.85
                },
                "detailed_analysis": {
                    "technical": {
                        "decision": "buy",
                        "confidence": 0.82,
                        "reasoning": "RSI過売り圏からの反発・MACD転換シグナル"
                    },
                    "sentiment": {
                        "decision": "buy", 
                        "confidence": 0.75,
                        "reasoning": "決算好調・業績上方修正期待"
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif data_type == "price-updates":
            sample_data = {
                "symbol": "7203",
                "price": 2650.0,
                "change": 25.0,
                "change_percent": 0.95,
                "volume": 1250000,
                "bid": 2648.0,
                "ask": 2652.0,
                "high": 2665.0,
                "low": 2635.0,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            raise HTTPException(status_code=404, detail=f"サンプルデータタイプ '{data_type}' は存在しません")
        
        return JSONResponse(content=sample_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sample data retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="サンプルデータ取得でエラーが発生しました")

@router.get("/config/frontend")
async def get_frontend_config():
    """フロントエンド設定取得"""
    try:
        config = {
            "api": {
                "base_url": "/api/v1",
                "websocket_url": "/ws",
                "timeout": 30000,
                "retry_attempts": 3
            },
            "features": {
                "real_time_updates": True,
                "ai_analysis": True,
                "multi_portfolio": True,
                "advanced_charts": True,
                "export_reports": True
            },
            "ui": {
                "theme": "system",  # light, dark, system
                "language": "ja",
                "currency": "JPY",
                "number_format": "ja-JP",
                "chart_refresh_interval": 5000
            },
            "limits": {
                "max_portfolios": 10,
                "max_holdings_per_portfolio": 50,
                "max_ai_requests_per_hour": 50,
                "websocket_reconnect_delay": 1000
            },
            "development": {
                "mock_mode": False,
                "debug_websocket": False,
                "log_api_calls": False
            }
        }
        
        return JSONResponse(content=config)
        
    except Exception as e:
        logger.error(f"Frontend config retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="フロントエンド設定取得でエラーが発生しました")

@router.post("/test/websocket")
async def test_websocket_connection():
    """WebSocket接続テスト"""
    try:
        # テスト用WebSocket接続数取得
        active_connections = len(websocket_manager.active_connections)
        
        # テストメッセージ送信
        test_message = {
            "type": "test",
            "data": {
                "message": "WebSocket connection test",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # 全接続にテストメッセージ送信
        await websocket_manager.broadcast(json.dumps(test_message))
        
        return {
            "status": "success",
            "active_connections": active_connections,
            "test_message": test_message,
            "message": "WebSocketテストメッセージを送信しました"
        }
        
    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")
        raise HTTPException(status_code=500, detail="WebSocketテストでエラーが発生しました")

@router.get("/development/reset-cache")
async def reset_development_cache():
    """開発用キャッシュリセット（開発環境のみ）"""
    try:
        from app.config.settings import settings
        
        if not settings.DEBUG:
            raise HTTPException(status_code=403, detail="開発環境でのみ利用可能です")
        
        # Redis キャッシュクリア
        keys_to_clear = [
            "portfolio:*",
            "price:*", 
            "ai_analysis:*",
            "market_data:*"
        ]
        
        cleared_count = 0
        for pattern in keys_to_clear:
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)
                cleared_count += len(keys)
        
        return {
            "status": "success",
            "cleared_keys": cleared_count,
            "message": "開発用キャッシュをクリアしました",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Development cache reset failed: {e}")
        raise HTTPException(status_code=500, detail="キャッシュリセットでエラーが発生しました")