import jwt
from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client
from app.config.settings import settings

security = HTTPBearer()

# Supabase client for JWT verification (optional)
supabase = None
if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")

async def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    """Verify Supabase JWT token"""
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
        
        return {
            "user_id": response.user.id,
            "email": response.user.email,
            "user_metadata": response.user.user_metadata
        }
        
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = None) -> Optional[dict]:
    """Get current user from token (optional)"""
    if not credentials:
        return None
    return await verify_token(credentials)