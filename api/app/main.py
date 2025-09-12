from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.config.settings import settings
from app.middleware.security import SecurityMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.ai_analysis import router as ai_analysis_router
from app.routers.admin import router as admin_router
from app.routers.trading_integration import router as trading_router
from app.routers.frontend_integration import router as frontend_router
from app.routers.portfolios_db import router as portfolios_router
from app.routers.trades_db import router as trades_router
from app.websocket.routes import router as websocket_router
from app.websocket.manager import websocket_manager
from app.services.routes import router as services_router
from app.services.realtime_service import realtime_service
from app.services.redis_client import redis_client
from app.database.connection import init_database, close_database

# ログ設定
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    print(f"🚀 Starting Kaboom Stock Trading API")
    print(f"   - Host: {settings.API_HOST}:{settings.API_PORT}")
    print(f"   - Debug: {settings.DEBUG}")
    print(f"   - CloudRun: {settings.is_cloud_run}")
    
    # データベース初期化
    await init_database()
    print("   - Database initialized")
    
    # Redis接続初期化
    await redis_client.connect()
    print("   - Redis Client connected")
    
    # WebSocketマネージャー起動
    await websocket_manager.startup()
    print("   - WebSocket Manager initialized")
    
    # リアルタイムデータサービス起動
    await realtime_service.start()
    print("   - Realtime Service started")
    
    # 監視サービス起動
    from app.services.monitoring_service import monitoring_service
    await monitoring_service.start_monitoring()
    print("   - Monitoring Service started")
    
    yield
    
    # サービス終了処理
    await realtime_service.stop()
    print("   - Realtime Service stopped")
    
    # 監視サービス停止
    from app.services.monitoring_service import monitoring_service
    await monitoring_service.stop_monitoring()
    print("   - Monitoring Service stopped")
    
    await websocket_manager.shutdown()
    print("   - WebSocket Manager shutdown")
    
    await redis_client.disconnect()
    print("   - Redis Client disconnected")
    
    await close_database()
    print("   - Database connections closed")
    
    print("🔽 Shutting down Kaboom Stock Trading API")

# Create FastAPI app
app = FastAPI(
    title="Kaboom Stock Trading API",
    description="Real-time stock trading management system with AI analysis",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Setup middleware (順序重要)
from fastapi.middleware.cors import CORSMiddleware

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

app.add_middleware(SecurityMiddleware)  # セキュリティヘッダー
app.add_middleware(RateLimitMiddleware)  # レート制限

# Include routers
app.include_router(health_router)  # ヘルスチェック
app.include_router(auth_router)    # 認証
app.include_router(ai_analysis_router)  # AI分析
app.include_router(admin_router)   # 管理ダッシュボード
app.include_router(trading_router) # 外部取引所統合
app.include_router(frontend_router) # フロントエンド統合
app.include_router(portfolios_router)  # ポートフォリオ管理
app.include_router(trades_router)      # 取引管理
app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(services_router)

# Root endpoint only (health endpoints are in routers/health.py)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Kaboom Stock Trading API",
        "version": "1.0.0",
        "status": "running",
        "websocket_url": f"ws://{settings.API_HOST}:{settings.API_PORT}/ws" if not settings.is_cloud_run else "/ws"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": "2024-01-01T00:00:00Z"  # TODO: Use actual timestamp
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """General exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "detail": str(exc) if settings.DEBUG else "Something went wrong"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        access_log=settings.DEBUG
    )