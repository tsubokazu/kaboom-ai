# app/middleware/security.py

import logging
import secrets
import time
from typing import Dict, List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダーとセキュリティ機能を提供するミドルウェア"""
    
    def __init__(self, app):
        super().__init__(app)
        
        # セキュリティヘッダー設定
        self.security_headers = {
            # XSS Protection
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            
            # HTTPS Enforcement (production only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if not settings.DEBUG else None,
            
            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.openrouter.ai https://openrouter.ai; "
                "frame-ancestors 'none';"
            ),
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        # 機密情報パターン
        self.sensitive_patterns = [
            "password",
            "secret", 
            "api_key",
            "token",
            "private_key",
            "OPENROUTER_API_KEY"
        ]
        
        # 攻撃パターン検出
        self.malicious_patterns = [
            "<script",
            "javascript:",
            "onload=",
            "onerror=",
            "eval(",
            "document.cookie",
            "../../../",  # Path traversal
            "union select",  # SQL injection
            "drop table",
            "'or'1'='1",
        ]
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # リクエスト前処理
        security_check_result = await self._security_check(request)
        if security_check_result:
            return security_check_result
        
        # Request ID生成
        request_id = self._generate_request_id()
        
        try:
            # リクエスト実行
            response = await call_next(request)
            
            # レスポンス後処理
            await self._add_security_headers(response, request_id)
            await self._log_request(request, response, start_time, request_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Request processing error: {e}", exc_info=True)
            
            # セキュアなエラーレスポンス
            error_response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "request_id": request_id}
            )
            await self._add_security_headers(error_response, request_id)
            return error_response
    
    async def _security_check(self, request: Request) -> Optional[Response]:
        """セキュリティチェック"""
        
        # 1. Malicious pattern detection
        malicious_content = self._detect_malicious_content(request)
        if malicious_content:
            logger.warning(f"Malicious content detected: {malicious_content}")
            return JSONResponse(
                status_code=400,
                content={"error": "Malicious content detected"}
            )
        
        # 2. Request size limit
        if hasattr(request, 'body'):
            try:
                body = await request.body()
                if len(body) > 10 * 1024 * 1024:  # 10MB limit
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request payload too large"}
                    )
            except Exception:
                pass  # Body already consumed
        
        # 3. Sensitive information exposure check (development mode)
        if settings.DEBUG:
            await self._check_sensitive_data_exposure(request)
        
        return None
    
    def _detect_malicious_content(self, request: Request) -> Optional[str]:
        """悪意のあるコンテンツ検出"""
        
        # URL path check
        path = str(request.url.path).lower()
        for pattern in self.malicious_patterns:
            if pattern in path:
                return f"URL path: {pattern}"
        
        # Query parameters check
        for key, value in request.query_params.items():
            value_lower = str(value).lower()
            for pattern in self.malicious_patterns:
                if pattern in value_lower:
                    return f"Query param {key}: {pattern}"
        
        # Headers check (basic)
        for header_name, header_value in request.headers.items():
            header_value_lower = str(header_value).lower()
            for pattern in self.malicious_patterns:
                if pattern in header_value_lower:
                    return f"Header {header_name}: {pattern}"
        
        return None
    
    async def _check_sensitive_data_exposure(self, request: Request):
        """機密情報露出チェック（開発モード）"""
        
        # Authorization headerの内容をログ記録（開発時のみ）
        auth_header = request.headers.get("authorization")
        if auth_header:
            # トークンの一部のみログ記録（セキュリティ考慮）
            if len(auth_header) > 20:
                masked_token = auth_header[:10] + "*" * (len(auth_header) - 20) + auth_header[-10:]
                logger.debug(f"Auth header (masked): {masked_token}")
    
    async def _add_security_headers(self, response: Response, request_id: str):
        """セキュリティヘッダーの追加"""
        
        # セキュリティヘッダー追加
        for header_name, header_value in self.security_headers.items():
            if header_value is not None:
                response.headers[header_name] = header_value
        
        # Request ID追加
        response.headers["X-Request-ID"] = request_id
        
        # API version
        response.headers["X-API-Version"] = "1.0.0"
        
        # Response time header (for monitoring)
        if hasattr(response, '_processing_time'):
            response.headers["X-Response-Time"] = f"{response._processing_time:.3f}s"
    
    async def _log_request(self, request: Request, response: Response, 
                          start_time: float, request_id: str):
        """リクエストログ記録"""
        
        processing_time = time.time() - start_time
        response._processing_time = processing_time
        
        # ログ記録
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "processing_time": f"{processing_time:.3f}s",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "client_ip": self._get_client_ip(request),
        }
        
        # Error status codes
        if response.status_code >= 400:
            logger.warning(f"HTTP {response.status_code}: {log_data}")
        else:
            logger.info(f"Request processed: {log_data}")
    
    def _get_client_ip(self, request: Request) -> str:
        """クライアントIP取得"""
        # CloudRun/Load Balancer環境
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # 直接接続
        return request.client.host if request.client else "unknown"
    
    def _generate_request_id(self) -> str:
        """リクエストID生成"""
        return secrets.token_urlsafe(16)

class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """信頼できるプロキシからのヘッダーのみを受け入れる"""
    
    def __init__(self, app, trusted_proxies: List[str] = None):
        super().__init__(app)
        self.trusted_proxies = trusted_proxies or [
            "127.0.0.1",
            "::1",
            "10.0.0.0/8",       # Private networks
            "172.16.0.0/12",
            "192.168.0.0/16"
        ]
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else None
        
        # 信頼できるプロキシかチェック（簡易実装）
        if client_ip and self._is_trusted_proxy(client_ip):
            # X-Forwarded-* headersを信頼
            forwarded_for = request.headers.get("x-forwarded-for")
            forwarded_proto = request.headers.get("x-forwarded-proto")
            
            if forwarded_for:
                # 実際のクライアントIPを設定
                real_client_ip = forwarded_for.split(",")[0].strip()
                request.scope["client"] = (real_client_ip, 0)
            
            if forwarded_proto:
                request.scope["scheme"] = forwarded_proto
        
        return await call_next(request)
    
    def _is_trusted_proxy(self, ip: str) -> bool:
        """信頼できるプロキシかチェック"""
        # 簡易実装（実際にはipaddress moduleを使用推奨）
        return ip in ["127.0.0.1", "::1"] or ip.startswith("10.")

# CORS設定（既存のcors.pyを拡張）
def configure_cors(app):
    """CORS設定（セキュリティ強化版）"""
    from fastapi.middleware.cors import CORSMiddleware
    
    # Production環境では厳密に制限
    allowed_origins = settings.ALLOWED_ORIGINS if not settings.DEBUG else ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        max_age=3600,  # Preflight cache time
    )
    
    logger.info(f"CORS configured with origins: {allowed_origins}")