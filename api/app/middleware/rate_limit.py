# app/middleware/rate_limit.py

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple, Any
from fastapi import HTTPException, status, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings

logger = logging.getLogger(__name__)

class InMemoryRateLimiter:
    """インメモリレート制限（開発・テスト用）"""
    
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, Any]]:
        """
        レート制限チェック
        
        Args:
            key: 制限キー (user_id, IP等)
            limit: 制限回数
            window: 時間窓（秒）
            
        Returns:
            (allowed, info) タプル
        """
        async with self.lock:
            now = time.time()
            
            # キーが存在しない場合は初期化
            if key not in self.requests:
                self.requests[key] = []
            
            # 時間窓外のリクエストを削除
            self.requests[key] = [
                req_time for req_time in self.requests[key] 
                if now - req_time < window
            ]
            
            current_count = len(self.requests[key])
            
            if current_count >= limit:
                # 制限超過
                oldest_request = min(self.requests[key]) if self.requests[key] else now
                reset_time = int(oldest_request + window)
                
                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset": reset_time,
                    "retry_after": reset_time - int(now)
                }
            else:
                # リクエスト記録
                self.requests[key].append(now)
                remaining = limit - current_count - 1
                
                return True, {
                    "limit": limit,
                    "remaining": remaining,
                    "reset": int(now + window),
                    "retry_after": 0
                }

class RateLimitMiddleware(BaseHTTPMiddleware):
    """レート制限ミドルウェア"""
    
    def __init__(self, app, limiter: Optional[InMemoryRateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter()
        
        # レート制限設定 (ユーザー役割別)
        self.rate_limits = {
            "basic": {"limit": 100, "window": 3600},      # 100 req/hour
            "premium": {"limit": 1000, "window": 3600},   # 1000 req/hour
            "enterprise": {"limit": 10000, "window": 3600}, # 10000 req/hour
            "admin": {"limit": 50000, "window": 3600},    # 50000 req/hour
            "anonymous": {"limit": 10, "window": 3600}    # 10 req/hour (未認証)
        }
        
        # AI分析専用制限
        self.ai_limits = {
            "basic": {"limit": 10, "window": 86400},      # 10 AI analyses/day
            "premium": {"limit": 100, "window": 86400},   # 100 AI analyses/day  
            "enterprise": {"limit": 1000, "window": 86400}, # 1000 AI analyses/day
            "admin": {"limit": 10000, "window": 86400}    # 10000 AI analyses/day
        }
    
    async def dispatch(self, request: Request, call_next):
        # ヘルスチェックはスキップ
        if request.url.path in ["/health", "/healthz", "/"]:
            return await call_next(request)
        
        try:
            # ユーザー識別
            user_key, user_role = await self._get_user_identity(request)
            
            # 基本レート制限チェック
            allowed, limit_info = await self._check_basic_rate_limit(user_key, user_role)
            
            if not allowed:
                return self._create_rate_limit_response(limit_info)
            
            # AI分析エンドポイントの場合、追加制限チェック
            if request.url.path.startswith("/api/v1/ai/"):
                ai_allowed, ai_limit_info = await self._check_ai_rate_limit(user_key, user_role)
                if not ai_allowed:
                    return self._create_rate_limit_response(ai_limit_info, "AI analysis quota exceeded")
            
            # リクエスト実行
            response = await call_next(request)
            
            # レスポンスヘッダーに制限情報を追加
            response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # エラー時はリクエストを通す（フェイルオープン）
            return await call_next(request)
    
    async def _get_user_identity(self, request: Request) -> Tuple[str, str]:
        """ユーザー識別情報の取得"""

        # Ingest API専用トークンをチェック（admin権限付与）
        ingest_token = request.headers.get("x-ingest-token")
        if ingest_token and request.url.path.startswith("/api/v1/ingest/"):
            # settings をインポートして比較
            from app.config.settings import settings
            if ingest_token == settings.INGEST_API_TOKEN and settings.INGEST_API_TOKEN:
                return "ingest_service", "admin"

        # Authorization header from request
        auth_header = request.headers.get("authorization")

        if auth_header and auth_header.startswith("Bearer "):
            try:
                # JWT tokenからユーザーIDを抽出（簡易実装）
                # 実際には auth.py の verify_token を使用すべき
                token = auth_header.split(" ")[1]
                # この例では簡略化してトークンをキーとして使用
                user_key = f"user:{token[:16]}"  # トークンの一部をキーに
                user_role = "basic"  # デフォルト、実際にはJWTから取得

                return user_key, user_role
            except Exception as e:
                logger.warning(f"Failed to extract user from token: {e}")

        # 認証されていない場合はIPアドレスを使用
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}", "anonymous"
    
    def _get_client_ip(self, request: Request) -> str:
        """クライアントIPアドレスの取得"""
        # CloudRun/Load Balancer からの場合
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # 直接接続の場合
        return request.client.host if request.client else "unknown"
    
    async def _check_basic_rate_limit(self, user_key: str, user_role: str) -> Tuple[bool, Dict]:
        """基本レート制限チェック"""
        limit_config = self.rate_limits.get(user_role, self.rate_limits["anonymous"])
        
        return await self.limiter.is_allowed(
            key=f"basic:{user_key}",
            limit=limit_config["limit"],
            window=limit_config["window"]
        )
    
    async def _check_ai_rate_limit(self, user_key: str, user_role: str) -> Tuple[bool, Dict]:
        """AI分析レート制限チェック"""
        if user_role not in self.ai_limits:
            user_role = "basic"
            
        limit_config = self.ai_limits[user_role]
        
        return await self.limiter.is_allowed(
            key=f"ai:{user_key}",
            limit=limit_config["limit"],
            window=limit_config["window"]
        )
    
    def _create_rate_limit_response(self, limit_info: Dict, message: str = "Rate limit exceeded") -> Response:
        """レート制限エラーレスポンス作成"""
        
        response = Response(
            content=f'{{"error": "{message}", "retry_after": {limit_info["retry_after"]}}}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="application/json"
        )
        
        response.headers["Retry-After"] = str(limit_info["retry_after"])
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])
        
        return response

# 使用量追跡用ユーティリティ
class UsageTracker:
    """API使用量追跡"""
    
    def __init__(self, limiter: InMemoryRateLimiter):
        self.limiter = limiter
    
    async def track_ai_usage(self, user_id: str, model: str, cost: float, tokens: int):
        """AI使用量の記録"""
        # 実際にはRedis/DatabaseにデータしURLIH
        logger.info(f"AI usage - User: {user_id}, Model: {model}, Cost: ${cost}, Tokens: {tokens}")
    
    async def get_user_quota_status(self, user_id: str, user_role: str) -> Dict:
        """ユーザークォータ状況の取得"""
        # 簡易実装
        return {
            "daily_ai_requests": {"used": 5, "limit": 100},
            "hourly_requests": {"used": 25, "limit": 1000}
        }