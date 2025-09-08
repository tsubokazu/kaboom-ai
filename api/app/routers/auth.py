# app/routers/auth.py

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.middleware.auth import security, verify_token, get_current_user_optional, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Request/Response Models
class TokenVerificationRequest(BaseModel):
    token: str = Field(..., description="Supabase JWT token to verify")

class UserInfoResponse(BaseModel):
    user_id: str
    email: str
    role: str
    verified: bool = True
    authenticated_at: str
    metadata: Optional[dict] = None

class TokenVerificationResponse(BaseModel):
    user_id: str
    email: str
    role: str
    verified: bool = True

@router.post("/verify", response_model=TokenVerificationResponse)
async def verify_jwt_token(request: TokenVerificationRequest):
    """JWT トークン検証"""
    
    try:
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Create credentials object from the token
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=request.token
        )
        
        # Verify token
        user = await verify_token(credentials)
        
        return TokenVerificationResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            verified=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Token verification failed"
        )

@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user_optional)):
    """現在のユーザー情報取得"""
    
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    return UserInfoResponse(
        user_id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        verified=True,
        authenticated_at=current_user.authenticated_at.isoformat(),
        metadata=current_user.metadata
    )

@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_user_optional)):
    """トークンリフレッシュ（Supabaseクライアント側で処理）"""
    
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    # Supabaseのトークンリフレッシュはクライアント側で処理
    # ここではユーザー情報の再検証のみ
    return {
        "message": "Token refresh should be handled by Supabase client",
        "user_id": current_user.id,
        "current_role": current_user.role,
        "refresh_endpoint": "https://your-supabase-url/auth/v1/token?grant_type=refresh_token"
    }

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user_optional)):
    """ログアウト（クライアント側でトークン削除）"""
    
    if current_user:
        logger.info(f"User {current_user.id} logged out")
    
    # サーバーサイドではセッション管理していないため、
    # クライアント側でのトークン削除を指示
    return {
        "message": "Logout successful. Please remove the token from client storage.",
        "logged_out_at": datetime.utcnow().isoformat()
    }

@router.get("/session")
async def get_session_info(
    request: Request, 
    current_user: User = Depends(get_current_user_optional)
):
    """セッション情報取得"""
    
    # クライアント情報
    user_agent = request.headers.get("user-agent", "unknown")
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    
    session_info = {
        "authenticated": current_user is not None,
        "session_id": None,  # JWTベースなのでセッションIDなし
        "client_info": {
            "ip_address": client_ip,
            "user_agent": user_agent
        },
        "server_time": datetime.utcnow().isoformat()
    }
    
    if current_user:
        session_info.update({
            "user_id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "authenticated_at": current_user.authenticated_at.isoformat()
        })
    
    return session_info

# ヘルスチェック用エンドポイント（認証不要）
@router.get("/health")
async def auth_health_check():
    """認証サービスヘルスチェック"""
    
    from app.config.settings import settings
    
    return {
        "status": "healthy",
        "service": "authentication",
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        "timestamp": datetime.utcnow().isoformat()
    }