from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.config.settings import settings
from app.middleware.cors import setup_cors
from app.websocket.routes import router as websocket_router
from app.websocket.manager import websocket_manager
from app.services.routes import router as services_router
from app.services.realtime_service import realtime_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    print(f"🚀 Starting Kaboom Stock Trading API")
    print(f"   - Host: {settings.API_HOST}:{settings.API_PORT}")
    print(f"   - Debug: {settings.DEBUG}")
    print(f"   - CloudRun: {settings.is_cloud_run}")
    
    # WebSocketマネージャー起動
    await websocket_manager.startup()
    print("   - WebSocket Manager initialized")
    
    # リアルタイムデータサービス起動
    await realtime_service.start()
    print("   - Realtime Service started")
    
    yield
    
    # サービス終了処理
    await realtime_service.stop()
    print("   - Realtime Service stopped")
    
    await websocket_manager.shutdown()
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

# Setup middleware
setup_cors(app)

# Include routers
app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(services_router)

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check for CloudRun and load balancers"""
    return {"status": "healthy", "service": "kaboom-api"}

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