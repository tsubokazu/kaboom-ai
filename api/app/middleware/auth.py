import jwt
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from app.config.settings import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Supabase client for JWT verification (optional)
supabase = None
if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")

class UserRole:
    """ユーザー権限レベル"""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    ADMIN = "admin"

class User:
    """認証済みユーザー情報"""
    def __init__(self, user_id: str, email: str, role: str = UserRole.BASIC, 
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = user_id
        self.email = email
        self.role = role
        self.metadata = metadata or {}
        self.authenticated_at = datetime.utcnow()
    
    def has_role(self, required_role: str) -> bool:
        """権限レベルチェック"""
        role_hierarchy = {
            UserRole.BASIC: 1,
            UserRole.PREMIUM: 2,
            UserRole.ENTERPRISE: 3,
            UserRole.ADMIN: 4
        }
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        return user_level >= required_level

async def verify_token(credentials: HTTPAuthorizationCredentials) -> User:
    """Supabase JWT トークン検証"""
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Authentication service not configured",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token = credentials.credentials
        
        # Verify JWT token with Supabase
        response = supabase.auth.get_user(token)
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # ユーザーロール判定（メタデータまたは外部設定から）
        user_role = UserRole.BASIC
        if response.user.user_metadata:
            user_role = response.user.user_metadata.get("role", UserRole.BASIC)
        
        return User(
            user_id=response.user.id,
            email=response.user.email,
            role=user_role,
            metadata=response.user.user_metadata
        )
        
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dependency functions for FastAPI
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """現在認証済みユーザーの取得 (必須)"""
    return await verify_token(credentials)

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """現在認証済みユーザーの取得 (オプション)"""
    if not credentials:
        return None
    return await verify_token(credentials)

def require_role(required_role: str):
    """特定の権限を要求するデコレータ"""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}, user role: {user.role}"
            )
        return user
    return role_checker

# 権限レベル別の依存関数
get_premium_user = require_role(UserRole.PREMIUM)
get_enterprise_user = require_role(UserRole.ENTERPRISE) 
get_admin_user = require_role(UserRole.ADMIN)